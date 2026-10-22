"""
CamAI - detector nhanh (CUDA Graph + preprocess toi uu).

Muc dich
--------
Do that tren may nay (RTX 3090, torch 2.14+cu126, ultralytics 8.4.177):
moi 1 LAN GOI `YOLO(frame)` ton ~16-24 ms, nhung phan GPU thuc su chi lam
~1.4 ms. Phan con lai la CHI PHI HOST-SIDE (torch dispatcher + cuDNN launch),
khong phai GPU ban. Do do:
  - goi 1 khung (eager)                 : ~16.8 ms
  - goi 1 khung (CUDA Graph replay)    : ~1.3 ms   -> nhanh ~12.8 lan
Batch 8 khung/lan thi nhanh hon nua (2.2 ms/khung) NHUNG cho ket qua khac
bit (sai lech toi da 0.497559) => KHONG dung batch (se lam sai so dem).
CUDA Graph thi BIT-EXACT (torch.equal == True) => CSV/SO DEM KHONG DOI.

Cach hoat dong
--------------
1. `DetectorNhanh` boc `YOLO` cua ultralytics, goi `detector(frame)` 1 lan
   de ultralytics tao `predictor` + warm-up CUDA (khung dau dung ket qua cua
   ultralytics, dung nguyen).
2. Tu lan sau:
     a. `predictor.preprocess([frame])` -> tensor (1,3,H,W) float32 (Y nguyen)
     b. copy tensor vao buffer tinh cua CUDA Graph
     c. `graph.replay()` -> ket qua raw (1,84,5040) - BIT-EXACT voi eager
     d. `non_max_suppression` + `scale_boxes` (CUNG HAM cua ultralytics)
     e. tra ve `sv.Detections` (CUNG CACH `sv.Detections.from_ultralytics`)
3. Khong bat duoc CUDA Graph (CPU, loi capture,...) -> tu dung ve duong cu
   cua ultralytics, ket qua y het.

KHONG sua hanh vi ket qua: khung hinh, so dem, CSV deu giong het.
"""

from __future__ import annotations

import os
import time

import numpy as np
import supervision as sv
import torch
from ultralytics.utils import ops as uops
from ultralytics.utils.nms import non_max_suppression

# Chi do khi CAMAI_PROFILE=1 (khong ton them gi khi tat).
_PROFILE = os.environ.get("CAMAI_PROFILE", "").strip() == "1"

# Ten truong du lieu ten lop trong supervision (doi theo phien ban).
try:                                        # supervision >= 0.22
    from supervision.detection.utils import CLASS_NAME_DATA_FIELD
except Exception:                           # noqa: BLE001 - phien ban cu
    CLASS_NAME_DATA_FIELD = getattr(
        sv.Detections.from_ultralytics.__globals__,
        "CLASS_NAME_DATA_FIELD",
        "class_name",
    )


class DetectorNhanh:
    """Boc `YOLO` cua ultralytics, chay nhanh hon nhieu lan bang CUDA Graph.

    API:
        det = DetectorNhanh(yolo, conf=0.25)
        detections = det.detect(frame)      # -> sv.Detections
    """

    def __init__(self, detector, conf: float = 0.25, log=print,
                 bat_cuda_graph: bool = True) -> None:
        self.detector = detector
        self.conf = float(conf)
        self.log = log
        self.bat_cuda_graph = bool(bat_cuda_graph)

        self.predictor = None          # ultralytics predictor (tao o lan goi dau)
        self.net = None                # torch module (DetectionModel)
        self._graph = None             # torch.cuda.CUDAGraph
        self._buffer = None            # tensor input tinh cho graph
        self._ra = None                # ket qua raw cua graph
        self._hinh = None              # (H, W) cua khung hinh gui vao model
        self._dung_cuda_graph = False
        self._loi = ""
        self._lb = None                 # LetterBox (cache, cho preprocess nhanh)
        self._thu_bien = False          # True = da thu khoi dong va that bai
        self.tong = {}                 # ho so thoi gian (chi khi CAMAI_PROFILE=1)
        self.so = {}

    # ------------------------------------------------------------------ chay

    def detect(self, frame) -> sv.Detections:
        """Nhan dien 1 khung hinh, tra ve `sv.Detections` (nhu duong cu cu).

        Ket qua BIT-EXACT voi `sv.Detections.from_ultralytics(detector(frame)[0])`.
        """
        if self.predictor is None:
            if self._thu_bien:
                # Da thu khoi dong 1 lan va that bai -> dung duong cu cu.
                result = self.detector(frame, verbose=False, conf=self.conf)[0]
                return sv.Detections.from_ultralytics(result)
            return self._khoi_dong(frame)
        if not self._dung_cuda_graph:
            # Duong fallback: dung nguyen duong cu cua ultralytics.
            result = self.detector(frame, verbose=False, conf=self.conf)[0]
            return sv.Detections.from_ultralytics(result)
        return self._do_bang_graph(frame)

    # -------------------------------------------------------------- khoi dong

    def _khoi_dong(self, frame) -> sv.Detections:
        """Lan goi dau: tao predictor, warm-up CUDA, (neu duoc) capture graph."""
        # 1) goi ultralytics 1 lan: tao predictor + warm-up CUDA. Ket qua cua
        #    khung nay dung nguyen duong cu cu (bit-exact, khong so).
        result = self.detector(frame, verbose=False, conf=self.conf)[0]
        self.predictor = getattr(self.detector, "predictor", None)
        if self.predictor is None:
            self._thu_bien = True
            self.log("[nhanh] khong lay duoc predictor -> dung duong cu cu")
            return sv.Detections.from_ultralytics(result)

        self.net = self.predictor.model.model      # DetectionModel (torch)
        if not self.bat_cuda_graph:
            self.log("[nhanh] CUDA Graph TAT theo yeu cau -> dung duong cu cu")
            return sv.Detections.from_ultralytics(result)
        if not torch.cuda.is_available():
            self.log("[nhanh] khong co CUDA -> dung duong cu cu")
            return sv.Detections.from_ultralytics(result)

        try:
            self._capture(frame)
            self._dung_cuda_graph = True
            self.log(
                "[nhanh] CUDA Graph: BAT (replay ~1-2 ms/khung thay vi "
                "~16-24 ms) | ket qua BIT-EXACT, so dem/CSV khong doi"
            )
        except Exception as exc:                    # noqa: BLE001 - fail-safe
            self._dung_cuda_graph = False
            self._loi = f"{type(exc).__name__}: {exc}"
            self.log(
                f"[nhanh] khong bat duoc CUDA Graph ({self._loi}) -> "
                "dung duong cu cu (ket qua y het)"
            )
        return sv.Detections.from_ultralytics(result)

    def _capture(self, frame) -> None:
        """Chup CUDA Graph cho 1 kich thuoc khung hinh (va giu buffer tinh)."""
        im = self._preprocess(frame)
        if im.device.type != "cuda":
            raise RuntimeError("input khong o tren CUDA")
        shape = tuple(im.shape)
        self._hinh = shape[2:]

        # Warm-up tren stream rieng (bat buoc cho CUDA Graph).
        stream = torch.cuda.Stream()
        stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(stream):
            for _ in range(3):
                self.net(im)
        torch.cuda.current_stream().wait_stream(stream)
        torch.cuda.synchronize()

        self._buffer = torch.zeros(shape, device=im.device, dtype=im.dtype)
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            self._ra = self.net(self._buffer)[0]
        torch.cuda.synchronize()
        self._graph = graph

        # --- tu kiem tra: duong preprocess nhanh phai BIT-EXACT ---
        # Neu lech 1 bit -> bo duong nhanh, dung duong goc cua ultralytics.
        self._chuan_hoa_letterbox()
        if self._nap_vao_buffer(frame):
            if not torch.equal(im, self._buffer):
                self._lb = None
                self._buffer.copy_(im)
                self.log(
                    "[nhanh] preprocess nhanh lech 1 bit -> dung duong goc "
                    "cua ultralytics (ket qua y het)"
                )
        else:
            self._lb = None

    # ------------------------------------------------------------------ hot

    def _preprocess(self, frame):
        """Preprocess y hien `ultralytics` (LetterBox + tensor)."""
        return self.predictor.preprocess([frame])

    def _chuan_hoa_letterbox(self) -> None:
        """Tao LetterBox y het tham so cua ultralytics (de ket qua giong)."""
        if self._lb is not None:
            return
        from ultralytics.data.augment import LetterBox

        p = self.predictor
        scale_fill = bool(getattr(p, "scale_fill", False))
        # ultralytics: auto = same_shapes and args.rect and not scale_fill
        #               and (format == "pt" or ...)
        auto = bool(getattr(p.args, "rect", False)) and not scale_fill
        self._lb = LetterBox(
            p.imgsz, auto=auto, scale_fill=scale_fill, stride=p.model.stride,
        )

    def _nap_vao_buffer(self, frame) -> bool:
        """LetterBox + dua thang vao buffer tinh cua CUDA Graph.

        Ket qua BIT-EXACT voi `predictor.preprocess` (da kiem chung bang
        `torch.equal` luc chup graph). Tra ve False neu khong lam duoc ->
        dung duong preprocess goc cua ultralytics.
        """
        if self._lb is None or self._buffer is None:
            return False
        arr = self._lb(image=frame)
        if tuple(arr.shape[:2]) != tuple(self._buffer.shape[2:]):
            return False
        t = torch.from_numpy(arr).unsqueeze(0).to(
            self._buffer.device, non_blocking=True,
        )
        self._buffer.copy_(t.permute(0, 3, 1, 2).flip(1))
        self._buffer.div_(255)
        return True

    def _do_bang_graph(self, frame) -> sv.Detections:
        """Chay 1 khung qua CUDA Graph + NMS (cung ham cu ultralytics)."""
        _t0 = time.perf_counter()
        self._chuan_hoa_letterbox()
        if not self._nap_vao_buffer(frame):
            im = self._preprocess(frame)
            if tuple(im.shape) != tuple(self._buffer.shape):
                # Khung hinh doi kich thuoc -> chup lai graph (hiem gap).
                self._capture(frame)
                im = self._preprocess(frame)
            self._buffer.copy_(im)
        else:
            im = self._buffer
        if _PROFILE:
            self._them("a_preprocess", time.perf_counter() - _t0)
            _t0 = time.perf_counter()

        self._buffer.copy_(im)
        self._graph.replay()
        if _PROFILE:
            self._them("b_replay", time.perf_counter() - _t0)
            _t0 = time.perf_counter()

        args = self.predictor.args
        raw = self._ra
        preds = non_max_suppression(
            raw,
            args.conf,
            args.iou,
            args.classes,
            args.agnostic_nms,
            max_det=args.max_det,
            nc=0 if args.task == "detect" else len(self.predictor.model.names),
            end2end=getattr(self.predictor.model, "end2end", False),
            rotated=args.task == "obb",
        )
        if len(preds) and len(preds[0]):
            # Scale nguoc ve khung hinh goc - CUNG HAM voi ultralytics.
            preds[0][:, :4] = uops.scale_boxes(
                im.shape[2:], preds[0][:, :4], frame.shape
            )
            du_lieu = preds[0].cpu().numpy()
            xyxy = du_lieu[:, :4]
            confidence = du_lieu[:, 4]
            class_id = du_lieu[:, 5].astype(int)
            ten_lop = np.array(
                [self.predictor.model.names[int(c)] for c in class_id]
            )
        else:
            xyxy = np.empty((0, 4), dtype=np.float32)
            confidence = np.empty((0,), dtype=np.float32)
            class_id = np.empty((0,), dtype=int)
            ten_lop = np.empty((0,), dtype=str)
        if _PROFILE:
            self._them("c_nms", time.perf_counter() - _t0)
            _t0 = time.perf_counter()

        ket_qua = sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
            data={CLASS_NAME_DATA_FIELD: ten_lop},
        )
        if _PROFILE:
            self._them("d_chuyen_doi", time.perf_counter() - _t0)
        return ket_qua

    def _them(self, ten: str, giay: float) -> None:
        self.tong[ten] = self.tong.get(ten, 0.0) + giay
        self.so[ten] = self.so.get(ten, 0) + 1

    def bao_cao(self, log) -> None:
        """In bang thoi gian chi tiet ben trong detector nhanh."""
        if not _PROFILE or not self.so:
            return
        tong = sum(self.tong.values())
        n = max(self.so.values())
        log("  -- chi tiet trong detector nhanh --")
        for ten, giay in sorted(self.tong.items()):
            log(f"     {ten:<14}{giay * 1000.0 / n:>8.3f} ms/khung")
        log(f"     {'TONG':<14}{tong * 1000.0 / n:>8.3f} ms/khung")

    # ------------------------------------------------------------------ info

    def thong_tin(self) -> str:
        """Dong mo ta nganh de ghi log/bao cao."""
        if self._dung_cuda_graph:
            h, w = self._hinh
            return f"CUDA Graph ON ({w}x{h})"
        if self._loi:
            return f"DUONG CU (loi CUDA Graph: {self._loi})"
        return "DUONG CU (khong bat CUDA Graph)"
