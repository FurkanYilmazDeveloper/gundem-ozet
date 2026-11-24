@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Gundem Ozet - tek dosyalik .exe hazirlaniyor...
py -m pip install --upgrade pyinstaller || goto hata
py -m PyInstaller --onefile --noconsole --clean --name GundemOzet gundem_ozet.pyw || goto hata
for /f "usebackq delims=" %%d in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESK=%%d"
copy /y "dist\GundemOzet.exe" "%DESK%\GundemOzet.exe" >nul
echo.
echo Tamam! Masaustunde GundemOzet.exe olusturuldu.
pause
exit /b 0
:hata
echo.
echo Bir sorun oldu. Python yuklu mu? (python.org - kurulumda "Add python.exe to PATH" isaretli olmali)
pause
