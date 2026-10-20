' ============================================================================
'  CamAI - MO APP (ban doi dung, khong hien cua so lenh)
'  Click de mo CamAI. Neu app khong mo, dung ban "Mo CamAI.bat" de xem loi.
'  Chuoi trong file nay chi dung KY TU ASCII de khong loi font khi chay.
' ============================================================================
Option Explicit

Dim shell, fso, thuMuc, pythonw, guiFile, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

thuMuc = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = thuMuc & "\.venv\Scripts\pythonw.exe"
guiFile = thuMuc & "\gui.py"

If Not fso.FileExists(pythonw) Then
    MsgBox "CamAI: khong tim thay Python trong .venv." & vbCrLf & vbCrLf & _
           "Thu muc: " & thuMuc & vbCrLf & vbCrLf & _
           "Hay chay ""Mo CamAI.bat"" de xem thong bao loi day du.", _
           vbExclamation, "CamAI"
    WScript.Quit 1
End If

If Not fso.FileExists(guiFile) Then
    MsgBox "CamAI: khong tim thay file gui.py trong thu muc nay.", _
           vbExclamation, "CamAI"
    WScript.Quit 1
End If

' windowstyle = 0 : khong hien cua so lenh
cmd = """" & pythonw & """ """ & guiFile & """"
shell.CurrentDirectory = thuMuc
shell.Run cmd, 0, False
