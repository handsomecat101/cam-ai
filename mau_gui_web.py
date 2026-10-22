# -*- coding: utf-8 -*-
r"""Mau giao dien CamAI theo huong WEBVIEW: HTML/CSS trong QWebEngineView.

Y tuong: bo cuc + mau sac viet bang HTML/CSS (1 file index.html tu chua),
hien thi trong cua so native PySide6. Python <-> JS giao tiep qua QWebChannel.

Chay:
    .venv\Scripts\python.exe mau_gui_web.py
Chay kem topmost (cho chup anh):
    .venv\Scripts\python.exe mau_gui_web.py --topmost
Chup o kich thuoc dien thoai:
    .venv\Scripts\python.exe mau_gui_web.py --topmost --size 390x844 --min-size 360x600

KHONG noi vao pipeline CV, KHONG detect, KHONG chay model. Chi la mau giao dien.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from ctypes import wintypes

from PySide6.QtCore import QObject, QPoint, QSize, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

# --------------------------------------------------------------------------
# Import WebEngine - BAT BUOC. Khong co thi bao loi ro roi va thoat (khong crash).
# --------------------------------------------------------------------------
try:
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView

    CO_WEBENGINE = True
    LOI_WEBENGINE = ""
except Exception as exc:  # noqa: BLE001
    CO_WEBENGINE = False
    LOI_WEBENGINE = "%s: %s" % (type(exc).__name__, exc)


# --------------------------------------------------------------------------
# qwebchannel.js (ban chinh thuc cua Qt, LGPL) - noi dung ben trong file nay
# de app khong can file ngoai va chay 100% offline.
# --------------------------------------------------------------------------
QWEBCHANNEL_JS = r"""// Copyright (C) 2016 The Qt Company Ltd.
// Copyright (C) 2016 Klarälvdalens Datakonsult AB, a KDAB Group company, info@kdab.com, author Milian Wolff <milian.wolff@kdab.com>
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:critical reason:data-parser

"use strict";

var QWebChannelMessageTypes = {
    signal: 1,
    propertyUpdate: 2,
    init: 3,
    idle: 4,
    debug: 5,
    invokeMethod: 6,
    connectToSignal: 7,
    disconnectFromSignal: 8,
    setProperty: 9,
    response: 10,
};

var QWebChannel = function(transport, initCallback, converters)
{
    if (typeof transport !== "object" || typeof transport.send !== "function") {
        console.error("The QWebChannel expects a transport object with a send function and onmessage callback property." +
                      " Given is: transport: " + typeof(transport) + ", transport.send: " + typeof(transport.send));
        return;
    }

    var channel = this;
    this.transport = transport;

    var converterRegistry =
    {
        Date : function(response) {
            if (typeof response === "string"
                && response.match(
                        /^-?\d+-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d*)?([-+\u2212](\d{2}):(\d{2})|Z)?$/)) {
                var date = new Date(response);
                if (!isNaN(date))
                    return date;
            }
            return undefined; // Return undefined if current converter is not applicable
        }
    };

    this.usedConverters = [];

    this.addConverter = function(converter)
    {
        if (typeof converter === "string") {
            if (converterRegistry.hasOwnProperty(converter))
                this.usedConverters.push(converterRegistry[converter]);
            else
                console.error("Converter '" + converter + "' not found");
        } else if (typeof converter === "function") {
            this.usedConverters.push(converter);
        } else {
            console.error("Invalid converter object type " + typeof converter);
        }
    }

    if (Array.isArray(converters)) {
        for (const converter of converters)
            this.addConverter(converter);
    } else if (converters !== undefined) {
        this.addConverter(converters);
    }

    this.send = function(data)
    {
        if (typeof(data) !== "string") {
            data = JSON.stringify(data);
        }
        channel.transport.send(data);
    }

    this.transport.onmessage = function(message)
    {
        var data = message.data;
        if (typeof data === "string") {
            data = JSON.parse(data);
        }
        switch (data.type) {
            case QWebChannelMessageTypes.signal:
                channel.handleSignal(data);
                break;
            case QWebChannelMessageTypes.response:
                channel.handleResponse(data);
                break;
            case QWebChannelMessageTypes.propertyUpdate:
                channel.handlePropertyUpdate(data);
                break;
            default:
                console.error("invalid message received:", message.data);
                break;
        }
    }

    this.execCallbacks = {};
    this.execId = 0;
    this.exec = function(data, callback)
    {
        if (!callback) {
            // if no callback is given, send directly
            channel.send(data);
            return;
        }
        if (channel.execId === Number.MAX_VALUE) {
            // wrap
            channel.execId = Number.MIN_VALUE;
        }
        if (data.hasOwnProperty("id")) {
            console.error("Cannot exec message with property id: " + JSON.stringify(data));
            return;
        }
        data.id = channel.execId++;
        channel.execCallbacks[data.id] = callback;
        channel.send(data);
    };

    this.objects = {};

    this.handleSignal = function(message)
    {
        var object = channel.objects[message.object];
        if (object) {
            object.signalEmitted(message.signal, message.args);
        } else {
            console.warn("Unhandled signal: " + message.object + "::" + message.signal);
        }
    }

    this.handleResponse = function(message)
    {
        if (!message.hasOwnProperty("id")) {
            console.error("Invalid response message received: ", JSON.stringify(message));
            return;
        }
        channel.execCallbacks[message.id](message.data);
        delete channel.execCallbacks[message.id];
    }

    this.handlePropertyUpdate = function(message)
    {
        message.data.forEach(data => {
            var object = channel.objects[data.object];
            if (object) {
                object.propertyUpdate(data.signals, data.properties);
            } else {
                console.warn("Unhandled property update: " + data.object + "::" + data.signal);
            }
        });
        channel.exec({type: QWebChannelMessageTypes.idle});
    }

    this.debug = function(message)
    {
        channel.send({type: QWebChannelMessageTypes.debug, data: message});
    };

    channel.exec({type: QWebChannelMessageTypes.init}, function(data) {
        for (const objectName of Object.keys(data)) {
            new QObject(objectName, data[objectName], channel);
        }

        // now unwrap properties, which might reference other registered objects
        for (const objectName of Object.keys(channel.objects)) {
            channel.objects[objectName].unwrapProperties();
        }

        if (initCallback) {
            initCallback(channel);
        }
        channel.exec({type: QWebChannelMessageTypes.idle});
    });
};

function QObject(name, data, webChannel)
{
    this.__id__ = name;
    webChannel.objects[name] = this;

    // List of callbacks that get invoked upon signal emission
    this.__objectSignals__ = {};

    // Cache of all properties, updated when a notify signal is emitted
    this.__propertyCache__ = {};

    var object = this;

    // ----------------------------------------------------------------------

    this.unwrapQObject = function(response)
    {
        for (const converter of webChannel.usedConverters) {
            var result = converter(response);
            if (result !== undefined)
                return result;
        }

        if (response instanceof Array) {
            // support list of objects
            return response.map(qobj => object.unwrapQObject(qobj))
        }
        if (!(response instanceof Object))
            return response;

        if (!response["__QObject*__"] || response.id === undefined) {
            var jObj = {};
            for (const propName of Object.keys(response)) {
                jObj[propName] = object.unwrapQObject(response[propName]);
            }
            return jObj;
        }

        var objectId = response.id;
        if (webChannel.objects[objectId])
            return webChannel.objects[objectId];

        if (!response.data) {
            console.error("Cannot unwrap unknown QObject " + objectId + " without data.");
            return;
        }

        var qObject = new QObject( objectId, response.data, webChannel );
        qObject.destroyed.connect(function() {
            if (webChannel.objects[objectId] === qObject) {
                delete webChannel.objects[objectId];
                // reset the now deleted QObject to an empty {} object
                // just assigning {} though would not have the desired effect, but the
                // below also ensures all external references will see the empty map
                // NOTE: this detour is necessary to workaround QTBUG-40021
                Object.keys(qObject).forEach(name => delete qObject[name]);
            }
        });
        // here we are already initialized, and thus must directly unwrap the properties
        qObject.unwrapProperties();
        return qObject;
    }

    this.unwrapProperties = function()
    {
        for (const propertyIdx of Object.keys(object.__propertyCache__)) {
            object.__propertyCache__[propertyIdx] = object.unwrapQObject(object.__propertyCache__[propertyIdx]);
        }
    }

    function addSignal(signalData, isPropertyNotifySignal)
    {
        var signalName = signalData[0];
        var signalIndex = signalData[1];
        object[signalName] = {
            connect: function(callback) {
                if (typeof(callback) !== "function") {
                    console.error("Bad callback given to connect to signal " + signalName);
                    return;
                }

                object.__objectSignals__[signalIndex] = object.__objectSignals__[signalIndex] || [];
                object.__objectSignals__[signalIndex].push(callback);

                // only required for "pure" signals, handled separately for properties in propertyUpdate
                if (isPropertyNotifySignal)
                    return;

                // also note that we always get notified about the destroyed signal
                if (signalName === "destroyed" || signalName === "destroyed()" || signalName === "destroyed(QObject*)")
                    return;

                // and otherwise we only need to be connected only once
                if (object.__objectSignals__[signalIndex].length == 1) {
                    webChannel.exec({
                        type: QWebChannelMessageTypes.connectToSignal,
                        object: object.__id__,
                        signal: signalIndex
                    });
                }
            },
            disconnect: function(callback) {
                if (typeof(callback) !== "function") {
                    console.error("Bad callback given to disconnect from signal " + signalName);
                    return;
                }
                // This makes a new list. This is important because it won't interfere with
                // signal processing if a disconnection happens while emittig a signal
                object.__objectSignals__[signalIndex] = (object.__objectSignals__[signalIndex] || []).filter(function(c) {
                  return c != callback;
                });
                if (!isPropertyNotifySignal && object.__objectSignals__[signalIndex].length === 0) {
                    // only required for "pure" signals, handled separately for properties in propertyUpdate
                    webChannel.exec({
                        type: QWebChannelMessageTypes.disconnectFromSignal,
                        object: object.__id__,
                        signal: signalIndex
                    });
                }
            }
        };
    }

    /**
     * Invokes all callbacks for the given signalname. Also works for property notify callbacks.
     */
    function invokeSignalCallbacks(signalName, signalArgs)
    {
        var connections = object.__objectSignals__[signalName];
        if (connections) {
            connections.forEach(function(callback) {
                callback.apply(callback, signalArgs);
            });
        }
    }

    this.propertyUpdate = function(signals, propertyMap)
    {
        // update property cache
        for (const propertyIndex of Object.keys(propertyMap)) {
            var propertyValue = propertyMap[propertyIndex];
            object.__propertyCache__[propertyIndex] = this.unwrapQObject(propertyValue);
        }

        for (const signalName of Object.keys(signals)) {
            // Invoke all callbacks, as signalEmitted() does not. This ensures the
            // property cache is updated before the callbacks are invoked.
            invokeSignalCallbacks(signalName, signals[signalName]);
        }
    }

    this.signalEmitted = function(signalName, signalArgs)
    {
        invokeSignalCallbacks(signalName, this.unwrapQObject(signalArgs));
    }

    function addMethod(methodData)
    {
        var methodName = methodData[0];
        var methodIdx = methodData[1];

        // Fully specified methods are invoked by id, others by name for host-side overload resolution
        var invokedMethod = methodName[methodName.length - 1] === ')' ? methodIdx : methodName

        object[methodName] = function() {
            var args = [];
            var callback;
            var errCallback;
            for (var i = 0; i < arguments.length; ++i) {
                var argument = arguments[i];
                if (typeof argument === "function")
                    callback = argument;
                else
                    args.push(argument);
            }

            var result;
            // during test, webChannel.exec synchronously calls the callback
            // therefore, the promise must be constucted before calling
            // webChannel.exec to ensure the callback is set up
            if (!callback && (typeof(Promise) === 'function')) {
              result = new Promise(function(resolve, reject) {
                callback = resolve;
                errCallback = reject;
              });
            }

            webChannel.exec({
                "type": QWebChannelMessageTypes.invokeMethod,
                "object": object.__id__,
                "method": invokedMethod,
                "args": args
            }, function(response) {
                if (response !== undefined) {
                    var result = object.unwrapQObject(response);
                    if (callback) {
                        (callback)(result);
                    }
                } else if (errCallback) {
                  (errCallback)();
                }
            });

            return result;
        };
    }

    function bindGetterSetter(propertyInfo)
    {
        var propertyIndex = propertyInfo[0];
        var propertyName = propertyInfo[1];
        var notifySignalData = propertyInfo[2];
        // initialize property cache with current value
        // NOTE: if this is an object, it is not directly unwrapped as it might
        // reference other QObject that we do not know yet
        object.__propertyCache__[propertyIndex] = propertyInfo[3];

        if (notifySignalData) {
            if (notifySignalData[0] === 1) {
                // signal name is optimized away, reconstruct the actual name
                notifySignalData[0] = propertyName + "Changed";
            }
            addSignal(notifySignalData, true);
        }

        Object.defineProperty(object, propertyName, {
            configurable: true,
            get: function () {
                var propertyValue = object.__propertyCache__[propertyIndex];
                if (propertyValue === undefined) {
                    // This shouldn't happen
                    console.warn("Undefined value in property cache for property \"" + propertyName + "\" in object " + object.__id__);
                }

                return propertyValue;
            },
            set: function(value) {
                if (value === undefined) {
                    console.warn("Property setter for " + propertyName + " called with undefined value!");
                    return;
                }
                object.__propertyCache__[propertyIndex] = value;
                var valueToSend = value;
                webChannel.exec({
                    "type": QWebChannelMessageTypes.setProperty,
                    "object": object.__id__,
                    "property": propertyIndex,
                    "value": valueToSend
                });
            }
        });

    }

    // ----------------------------------------------------------------------

    data.methods.forEach(addMethod);

    data.properties.forEach(bindGetterSetter);

    data.signals.forEach(function(signal) { addSignal(signal, false); });

    Object.assign(object, data.enums);
}

QObject.prototype.toJSON = function() {
    if (this.__id__ === undefined) return {};
    return {
        id: this.__id__,
        "__QObject*__": true
    };
};

//required for use with nodejs
if (typeof module === 'object') {
    module.exports = {
        QWebChannel: QWebChannel
    };
}"""

# Bo wrapper IIFE + gan ra global window de trang web goi duoc
QWEBCHANNEL_BOOT = (
    "(function(){\n" + QWEBCHANNEL_JS + "\nwindow.QWebChannel = QWebChannel;\n})();"
)

JS_AN_TOAST = r"""
(function () {
    var t = document.getElementById('toast');
    if (t) { t.classList.remove('hien'); }
    return 'an toast';
})()
"""

# Do toa do header + kiem tra chong lan + cuon ngang (dung de kiem chung)
JS_DO_HEADER = r"""
(function () {
    function r(sel) {
        var e = document.querySelector(sel);
        if (!e) { return null; }
        var b = e.getBoundingClientRect();
        return {left: Math.round(b.left), right: Math.round(b.right),
                top: Math.round(b.top), bottom: Math.round(b.bottom),
                width: Math.round(b.width), height: Math.round(b.height)};
    }
    var trai = r('.dau-trai'), giua = r('.dau-giua'), phai = r('.dau-phai');
    var chong = null;
    if (trai && giua && trai.right > giua.left) { chong = 'trai|giua'; }
    if (giua && phai && giua.right > phai.left) { chong = 'giua|phai'; }
    if (trai && phai && trai.right > phai.left) { chong = 'trai|phai'; }
    return JSON.stringify({
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
        scrollWidth: document.documentElement.scrollWidth,
        bodyScrollWidth: document.body.scrollWidth,
        coCuonNgang: document.documentElement.scrollWidth > window.innerWidth,
        header: r('#thanhDau'),
        trai: trai, giua: giua, phai: phai,
        tenApp: r('.ten-app'),
        video: r('#khungVideo'),
        theSo: r('#hangTheSo'),
        coChongLan: chong
    });
})()
"""

# Script do toa do cac vung trong HTML (don viet CSS px, goc = webview)
JS_DO_VUNG = r"""
(function () {
    function r(sel) {
        var e = document.querySelector(sel);
        if (!e) { return null; }
        var b = e.getBoundingClientRect();
        return [b.left, b.top, b.width, b.height];
    }
    var doRong = null;
    try {
        if (window.__camaDoTrang) { doRong = window.__camaDoTrang(); }
    } catch (e) { doRong = null; }

    return JSON.stringify({
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
        dpr: window.devicePixelRatio || 1,
        cot_trai: r('#cotTrai'),
        the_so: r('#hangTheSo'),
        video: r('#khungVideo'),
        dau: r('#thanhDau'),
        do_rong: doRong
    });
})()
"""

# --------------------------------------------------------------------- MAU
NEN = "#16181D"
PANEL = "#1E2128"
VIEN = "#31353F"
CHU = "#E9EAEE"
PHU = "#9AA0AC"
ACCENT = "#4C8DFF"

FONT_CHU = "Segoe UI"
FONT_MONO = "Cascadia Mono"

THU_MUC = os.path.dirname(os.path.abspath(__file__))
FILE_HTML = os.path.join(THU_MUC, "mau_gui_web", "index.html")


# --------------------------------------------------------------------- RAM
class _BộĐếmBộNhớ(ctypes.Structure):
    """PROCESS_MEMORY_COUNTERS cua Windows (stdlib, khong them dependency)."""

    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def ram_mb() -> float:
    """RAM dang dung cua tien trinh hien tai (MB)."""
    dem = _BộĐếmBộNhớ()
    dem.cb = ctypes.sizeof(dem)
    try:
        fn = ctypes.windll.psapi.GetProcessMemoryInfo
        fn.argtypes = [ctypes.c_void_p,
                       ctypes.POINTER(_BộĐếmBộNhớ),
                       ctypes.c_uint]
        fn.restype = ctypes.c_int
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if fn(handle, ctypes.byref(dem), dem.cb):
            return dem.WorkingSetSize / (1024.0 * 1024.0)
    except Exception:  # noqa: BLE001
        pass
    try:  # du phong (neu co san psutil trong venv)
        import psutil  # noqa: PLC0415

        return psutil.Process().memory_info().rss / (1024.0 * 1024.0)
    except Exception:  # noqa: BLE001
        pass
    return 0.0


# ------------------------------------------------------------------- BRIDGE
class Bridge(QObject):
    """Object QWebChannel 'bridge' - nhan tin tu JS va day nguoc len Python.

    Slot `thong_bao(text)` la bang chung giao tiep 2 chieu that su:
    JS -> Python -> console + QLabel o day cua so.
    """

    tin_nhan_den = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.so_lan = 0

    @Slot(str)
    def thong_bao(self, text: str) -> None:
        """JS goi len. In ra console + phat tin de len cua so."""
        self.so_lan += 1
        dong = "[BRIDGE] thong_bao #%d: %s" % (self.so_lan, text)
        print(dong, flush=True)
        self.tin_nhan_den.emit(dong)


class TrangThaiBar(QLabel):
    """Thanh trang thai o day cua so - tu rut gon chu khi cua so hep."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full = text
        self.setFixedHeight(28)

    def setFullText(self, text: str) -> None:
        self._full = text
        self._rut_gon()

    def _rut_gon(self) -> None:
        fm = QFontMetrics(self.font())
        self.setText(fm.elidedText(
            self._full, Qt.ElideRight, max(60, self.width() - 24)))

    def resizeEvent(self, e):                       # noqa: N802
        super().resizeEvent(e)
        self._rut_gon()


# ------------------------------------------------------------------ CUa SO
class CamAIWeb(QMainWindow):
    """Cua so native PySide6 chua webview HTML + QWebChannel."""

    def __init__(self, kich_thuoc=None, min_kich_thuoc=None, self_test="nguon",
                 duong_dan_vung=None):
        super().__init__()
        self.setWindowTitle("CamAI - Phan tich video giam sat")
        self.setMinimumSize(min_kich_thuoc if min_kich_thuoc else QSize(1200, 760))
        self.resize(1440, 900)

        icon = os.path.join(THU_MUC, "assets", "camai.png")
        if os.path.isfile(icon):
            self.setWindowIcon(QIcon(icon))

        self.t0 = time.perf_counter()
        self.thoi_gian_ms = None
        self.do_rong = None
        self.self_test = self_test
        self.duong_dan_vung = duong_dan_vung

        self._tao_khung()
        self._tao_webchannel()

        self.view.loadFinished.connect(self._trang_load_xong)

        if not os.path.isfile(FILE_HTML):
            print("KHONG tim thay file HTML: %s" % FILE_HTML, flush=True)
            return

        self.view.load(QUrl.fromLocalFile(FILE_HTML))

        if kich_thuoc:
            # Ep kich thuoc cua so de chup anh dung khung can chup.
            self.setMinimumSize(0, 0)
            self.resize(kich_thuoc)
            self.setFixedSize(kich_thuoc)

    # -------------------------------------------------------------- khung
    def _tao_khung(self) -> None:
        nen = QWidget()
        nen.setObjectName("nenChinh")
        nen.setStyleSheet("QWidget#nenChinh { background-color: %s; }" % NEN)
        self.setCentralWidget(nen)

        v = QVBoxLayout(nen)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.view = QWebEngineView()
        self.view.setStyleSheet("background-color: %s;" % NEN)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        v.addWidget(self.view, 1)

        # Thanh trang thai o day cua so: noi hien thong bao tu bridge
        self.trang_thai = TrangThaiBar(
            "Chua co tin nhan tu web. Bam nut \"BẮT ĐẦU\" trong cua so de thu QWebChannel.")
        self.trang_thai.setWordWrap(False)
        self.trang_thai.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        font = QFont(FONT_MONO, 8)
        self.trang_thai.setFont(font)
        self.trang_thai.setStyleSheet(
            "QLabel { background-color: %s; color: %s; border-top: 1px solid %s;"
            " padding-left: 12px; padding-right: 12px; }" % (PANEL, PHU, VIEN))
        v.addWidget(self.trang_thai, 0)

    # ---------------------------------------------------------- webchannel
    def _tao_webchannel(self) -> None:
        trang = self.view.page()
        trang.setBackgroundColor(QColor(NEN))
        try:
            trang.settings().setAttribute(
                QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        except Exception:  # noqa: BLE001
            pass

        self.bridge = Bridge(self)
        self.bridge.tin_nhan_den.connect(self._hien_thong_bao)

        self.channel = QWebChannel(trang)
        self.channel.registerObject("bridge", self.bridge)
        trang.setWebChannel(self.channel)

    def _hien_thong_bao(self, dong: str) -> None:
        self.trang_thai.setFullText(dong)

    # ------------------------------------------------------------- tai ve
    def _trang_load_xong(self, ok: bool) -> None:
        if not ok:
            print("LOAD HTML THAT BAI", flush=True)
            return
        self.thoi_gian_ms = (time.perf_counter() - self.t0) * 1000.0
        print("HTML da load xong. Thoi gian mo: %.0f ms" % self.thoi_gian_ms, flush=True)

        # Tiem qwebchannel.js vao trang + tao kenh
        trang = self.view.page()
        trang.runJavaScript(QWEBCHANNEL_BOOT)
        trang.runJavaScript(
            "window.__camaDoTrang && console.log('CAMAI-READY ' + JSON.stringify(window.__camaDoTrang()));")

        # Tu kiem chung: bam 1 nut trong HTML de chung minh JS -> Python chay that
        if self.self_test and self.self_test != "tat":
            QTimer.singleShot(1500, self._tu_kiem_chung)

        # Ghi toa do vung sau khi moi co con giong (cho script chup anh)
        if self.duong_dan_vung:
            QTimer.singleShot(2800, lambda: self._do_vung(self.duong_dan_vung))

    def _tu_kiem_chung(self) -> None:
        """Bam nut trong HTML -> bridge.thong_bao -> Python nhan tin (bang chung that)."""
        if self.self_test == "chay":
            chon = "document.getElementById('nutChay')"
        else:
            chon = "document.querySelector('[data-hanh]')"

        js = ("(function(){var b=%s; if(!b){return 'KHONG CO NUT';}"
              " b.click(); return 'DA BAM ' + (b.textContent||'').trim();})()" % chon)

        def xu_ly(ket_qua):
            print("TU KIEM: bam nut trong HTML -> %r" % (ket_qua,), flush=True)
            # in trang thai kenh sau khi bam (bridge da noi hay chua)
            self.view.page().runJavaScript(
                "console.log('CAMAI-SAU-BAM ' + JSON.stringify(window.__camaDoTrang()));",
                0,
                lambda r: print("TRANG THAI KENH:", r, flush=True))

        self.view.page().runJavaScript(js, 0, xu_ly)

    # ------------------------------------------------- kiem responsive
    def _kiem_rong(self, widths) -> None:
        """Do layout o nhieu be rong khac nhau (view ngoai man hinh, khong
        lam anh huong cua so chinh).

        In ra: header.top, toa do cac phan tu header, co chong lan hay khong,
        scrollWidth vs innerWidth (cuon ngang).
        """
        self._kiem_widths = list(widths)
        self._kiem_index = 0
        self._buoc_kiem_rong()

    def _buoc_kiem_rong(self) -> None:
        if self._kiem_index >= len(self._kiem_widths):
            print("KIEM RONG: HOAN TAT", flush=True)
            return

        rong = self._kiem_widths[self._kiem_index]
        view = QWebEngineView()
        view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        view.setFixedSize(rong, 900)

        def do_ngang(ket_qua):
            print("KIEM RONG %d px: %s" % (rong, ket_qua), flush=True)
            view.deleteLater()
            self._kiem_index += 1
            QTimer.singleShot(350, self._buoc_kiem_rong)

        def xong(ok):
            QTimer.singleShot(
                450, lambda: view.page().runJavaScript(JS_DO_HEADER, 0, do_ngang))

        view.loadFinished.connect(xong)
        view.setUrl(QUrl.fromLocalFile(FILE_HTML))
        view.show()

    # ---------------------------------------------------------- do vung
    def _do_vung(self, path: str) -> None:
        """Ghi toa do cac vung (toa do MAN HINH) cho script chup anh cat dung."""

        def xu_ly(chuoi):
            if not chuoi:
                print("KHONG doc duoc toa do vung", flush=True)
                return
            du = json.loads(chuoi)
            goc = self.view.mapToGlobal(QPoint(0, 0))
            dpr = du.get("dpr") or 1.0

            def quy_doi(hcn):
                if not hcn:
                    return None
                x, y, w, h = hcn
                return [
                    int(goc.x() + x * dpr),
                    int(goc.y() + y * dpr),
                    int(w * dpr),
                    int(h * dpr),
                ]

            dau = quy_doi(du.get("dau"))
            video = quy_doi(du.get("video"))
            vung = {
                "size_cua_so": [self.width(), self.height()],
                "client": [
                    int(self.mapToGlobal(QPoint(0, 0)).x()),
                    int(self.mapToGlobal(QPoint(0, 0)).y()),
                    self.width(), self.height(),
                ],
                "webview": [
                    int(goc.x()), int(goc.y()),
                    int(self.view.width() * dpr), int(self.view.height() * dpr),
                ],
                "dpr": dpr,
                "inner_width": du.get("innerWidth"),
                "inner_height": du.get("innerHeight"),
                "cot_trai": quy_doi(du.get("cot_trai")),
                "the_so": quy_doi(du.get("the_so")),
                "video": video,
                "dau": dau,
                "dau_video": None,
                "do_rong": du.get("do_rong"),
            }
            if dau and video:
                vung["dau_video"] = [
                    min(dau[0], video[0]),
                    min(dau[1], video[1]),
                    max(dau[0] + dau[2], video[0] + video[2]) - min(dau[0], video[0]),
                    max(dau[1] + dau[3], video[1] + video[3]) - min(dau[1], video[1]),
                ]

            thu_muc = os.path.dirname(path)
            if thu_muc:
                os.makedirs(thu_muc, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(vung, f, ensure_ascii=False, indent=2)

            print("FILE VUNG:", path, flush=True)
            print("KICH THUOC CUA SO:", self.width(), "x", self.height(), flush=True)
            print("VIEWPORT HTML: %sx%s  dpr=%s" % (
                du.get("innerWidth"), du.get("innerHeight"), dpr), flush=True)
            if vung.get("do_rong"):
                print("DO RONG:", json.dumps(vung["do_rong"], ensure_ascii=False), flush=True)
            print("RAM TIEN TRINH: %.1f MB" % ram_mb(), flush=True)

        # An toast truoc, roi moi do toa do (de anh chup khong thay thong bao nho)
        self.view.page().runJavaScript(
            JS_AN_TOAST, 0, lambda _r: self.view.page().runJavaScript(JS_DO_VUNG, 0, xu_ly))


def _parse_size(text):
    """'1440x900' -> QSize(1440, 900)."""
    if not text:
        return None
    chu = str(text).lower().replace("*", "x").split("x")
    if len(chu) != 2:
        raise ValueError("Kich thuoc sai dinh dang: %r (can dang 1440x900)" % text)
    return QSize(int(chu[0]), int(chu[1]))


def main() -> int:
    # Windows: console mac dinh la cp1252 -> print tieng Viet se loi.
    # Chuyen stdout/stderr sang UTF-8 truoc khi in bat ky thu gi.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    if not CO_WEBENGINE:
        print("")
        print("KHONG the chay mau giao dien webview tren may nay.")
        print("Linh do: %s" % LOI_WEBENGINE)
        print("Can cai: PySide6-Addons (co QtWebEngineWidgets) + PySide6 (co QtWebChannel).")
        print("Kiem tra: .venv\\Scripts\\python.exe -c \"from PySide6.QtWebEngineWidgets import QWebEngineView\"")
        print("")
        return 1

    parser = argparse.ArgumentParser(description="CamAI - mau giao dien webview")
    parser.add_argument("--topmost", action="store_true",
                        help="Giu cua so luon tren man hinh")
    parser.add_argument("--size", default=None,
                        help="Ep kich thuoc cua so, vi du 390x844")
    parser.add_argument("--min-size", default=None,
                        help="Kich thuoc toi thieu, vi du 360x600")
    parser.add_argument("--dump", default=None,
                        help="File ghi toa do vung (mac dinh _kk_out/mau_web/_vung.json)")
    parser.add_argument("--self-test", default="nguon",
                        choices=["nguon", "chay", "tat"],
                        help="Tu bam nut trong HTML de chung minh QWebChannel hoat dong")
    parser.add_argument("--kiem-rong", default=None,
                        help="Do layout o cac be rong, vi du 390,820,1440,1920")
    args = parser.parse_args()

    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_CHU, 9))

    kich_thuoc = _parse_size(args.size)
    min_kich_thuoc = _parse_size(args.min_size)

    duong_dan_vung = args.dump or os.path.join(
        THU_MUC, "_kk_out", "mau_web", "_vung.json")

    win = CamAIWeb(kich_thuoc=kich_thuoc, min_kich_thuoc=min_kich_thuoc,
                   self_test=args.self_test,
                   duong_dan_vung=duong_dan_vung)
    win.show()

    if args.topmost:
        win.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        win.show()
        win.raise_()
        win.activateWindow()

    if args.kiem_rong:
        widths = []
        for chu in str(args.kiem_rong).replace(" ", "").split(","):
            if chu:
                widths.append(int(chu))
        QTimer.singleShot(2500, lambda: win._kiem_rong(widths))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
