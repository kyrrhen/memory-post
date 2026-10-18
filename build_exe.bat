@echo off
setlocal
cd /d "%~dp0"

echo Building unified MemoryPost.exe ...
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name MemoryPost ^
  --icon "%~dp0assets\icon.ico" ^
  --distpath "%~dp0dist" ^
  --workpath "%~dp0build" ^
  --specpath "%~dp0build" ^
  --add-data "%~dp0assets\icon.ico;assets" ^
  --version-file "%~dp0packaging\version_info.txt" ^
  --exclude-module tkinter ^
  --exclude-module torch ^
  --exclude-module torchvision ^
  --exclude-module skimage ^
  --exclude-module scipy ^
  --exclude-module matplotlib ^
  --exclude-module IPython ^
  --exclude-module tensorflow ^
  --exclude-module lightning ^
  --exclude-module pandas ^
  --exclude-module sklearn ^
  --exclude-module cv2 ^
  "%~dp0memory_post.py"
if errorlevel 1 goto :error

echo.
echo Build complete:
echo   %~dp0dist\MemoryPost.exe
exit /b 0

:error
echo.
echo Build failed. Check the PyInstaller output above.
exit /b 1

