' ============================================================================
'  CamAI - MO APP BAN DESKTOP (PySide6 + QWebEngineView)
'  Click de mo CamAI. Neu app khong mo, dung ban "Mo CamAI.bat" de xem loi.
'  Chuoi trong file nay chi dung KY TU ASCII de khong loi font khi chay.
' ============================================================================
Option Explicit

Dim shell, fso, thuMuc, pythonw, appFile, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

thuMuc = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = thuMuc & "\.venv\Scripts\pythonw.exe"
appFile = thuMuc & "\app_qt.py"

If Not fso.FileExists(pythonw) Then
    MsgBox "CamAI: khong tim thay Python trong .venv." & vbCrLf & vbCrLf & _
           "Thu muc: " & thuMuc & vbCrLf & vbCrLf & _
           "Hay chay ""Mo CamAI.bat"" de xem thong bao loi day du.", _
           vbExclamation, "CamAI"
    WScript.Quit 1
End If

If Not fso.FileExists(appFile) Then
    MsgBox "CamAI: khong tim thay file app_qt.py trong thu muc nay." & vbCrLf & vbCrLf & _
           "Thu muc: " & thuMuc, _
           vbExclamation, "CamAI"
    WScript.Quit 1
End If

' windowstyle = 0 : khong hien cua so lenh
cmd = """" & pythonw & """ """ & appFile & """"
shell.CurrentDirectory = thuMuc
shell.Run cmd, 0, False
