@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set INPUT_DIR=%SCRIPT_DIR%input
set OUTPUT_DIR=%SCRIPT_DIR%output
set PYTHONPATH=%SCRIPT_DIR%
set PYTHON=python
set GM=%PYTHON% -m gaussian_maker.cli

echo ============================================
echo  Gaussian Maker
echo ============================================
echo  Input folder:  %INPUT_DIR%
echo  Output folder: %OUTPUT_DIR%
echo ============================================
echo.

:: Verify Python is available
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo ============================================
echo  Step 1/6: Upgrading pip
echo ============================================
%PYTHON% -m pip install --upgrade pip --quiet

echo ============================================
echo  Step 2/6: Installing binary packages
echo ============================================
%PYTHON% -m pip install fpsample --prefer-binary --quiet
if errorlevel 1 (
    echo [ERROR] Could not install fpsample.
    echo Install Visual Studio C++ Build Tools from:
    echo   https://visualstudio.microsoft.com/visual-cpp-build-tools/
    pause
    exit /b 1
)
echo [OK] Binary packages ready.

echo ============================================
echo  Step 3/6: Installing PyTorch with CUDA
echo ============================================
echo Trying CUDA 12.4 (works with NVIDIA driver 525+)...
%PYTHON% -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --quiet
%PYTHON% -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
if errorlevel 1 (
    echo CUDA 12.4 not working, trying CUDA 11.8...
    %PYTHON% -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118 --quiet
    %PYTHON% -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] GPU not detected. Training will run on CPU ^(slow^).
        echo           Make sure NVIDIA drivers are up to date.
    ) else (
        for /f "tokens=*" %%g in ('%PYTHON% -c "import torch; print(torch.cuda.get_device_name(0))"') do echo [OK] GPU: %%g
    )
) else (
    for /f "tokens=*" %%g in ('%PYTHON% -c "import torch; print(torch.cuda.get_device_name(0))"') do echo [OK] GPU: %%g
)

echo ============================================
echo  Step 4/6: Installing Python packages
echo ============================================
%PYTHON% -m pip install imageio-ffmpeg -r "%SCRIPT_DIR%requirements.txt" --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause
    exit /b 1
)
echo [OK] Python packages ready.

echo ============================================
echo  Step 5/6: Setting up FFmpeg
echo ============================================
set FFMPEG_WRAPPER=%SCRIPT_DIR%.ffmpeg
if not exist "%FFMPEG_WRAPPER%" mkdir "%FFMPEG_WRAPPER%"
for /f "tokens=*" %%i in ('%PYTHON% -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"') do set FFMPEG_EXE=%%i
copy /y "%FFMPEG_EXE%" "%FFMPEG_WRAPPER%\ffmpeg.exe" >nul
set PATH=%FFMPEG_WRAPPER%;%PATH%
echo [OK] FFmpeg ready.

echo ============================================
echo  Step 6/6: Setting up COLMAP
echo ============================================
where colmap >nul 2>&1
if errorlevel 1 (
    set COLMAP_DIR=%SCRIPT_DIR%.colmap
    if exist "!COLMAP_DIR!\colmap.exe" (
        echo [OK] Using cached COLMAP.
    ) else (
        echo Downloading COLMAP 3.10 for Windows...
        if not exist "!COLMAP_DIR!" mkdir "!COLMAP_DIR!"
        powershell -Command "& {$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/colmap/colmap/releases/download/3.10/colmap-x86_64-windows-cuda.zip' -OutFile '$env:TEMP\colmap.zip'}"
        if errorlevel 1 (
            echo [ERROR] Failed to download COLMAP. Check internet connection.
            pause
            exit /b 1
        )
        echo Extracting COLMAP...
        powershell -Command "Expand-Archive -Path '$env:TEMP\colmap.zip' -DestinationPath '!COLMAP_DIR!' -Force"
        del /q "%TEMP%\colmap.zip" >nul 2>&1
    )
    :: Find colmap.exe anywhere inside the extracted folder
    for /f "tokens=*" %%i in ('dir /b /s "!COLMAP_DIR!\colmap.exe" 2^>nul') do set COLMAP_BIN_DIR=%%~dpi
    if "!COLMAP_BIN_DIR!"=="" (
        echo [ERROR] colmap.exe not found after extraction.
        pause
        exit /b 1
    )
    set PATH=!COLMAP_BIN_DIR!;%PATH%
    echo [OK] COLMAP ready: !COLMAP_BIN_DIR!
) else (
    echo [OK] COLMAP already on PATH.
)

echo.
echo [OK] All dependencies ready. Starting pipeline...
echo.

:: Check for video files
set VIDEO_COUNT=0
for %%F in ("%INPUT_DIR%\*.mp4" "%INPUT_DIR%\*.MOV" "%INPUT_DIR%\*.mov" "%INPUT_DIR%\*.avi" "%INPUT_DIR%\*.mkv" "%INPUT_DIR%\*.webm") do (
    if exist "%%F" set /a VIDEO_COUNT+=1
)

if %VIDEO_COUNT%==0 (
    echo No video files found in input folder.
    echo Drop your videos into: %INPUT_DIR%
    echo.
    pause
    exit /b 1
)

echo Found %VIDEO_COUNT% video file(s). Processing...
echo.

:: Process each video file
for %%F in ("%INPUT_DIR%\*.mp4" "%INPUT_DIR%\*.MOV" "%INPUT_DIR%\*.mov" "%INPUT_DIR%\*.avi" "%INPUT_DIR%\*.mkv" "%INPUT_DIR%\*.webm") do (
    if exist "%%F" (
        set VIDEO_NAME=%%~nF
        echo ------------------------------------------
        echo Processing: %%~nxF
        echo ------------------------------------------
        %GM% run "%%F" --output "%OUTPUT_DIR%\!VIDEO_NAME!" --trainer nerfstudio --fps 2 --format ply --format splat
        if errorlevel 1 (
            echo.
            echo [ERROR] Failed to process %%~nxF
            echo.
        ) else (
            echo.
            echo [DONE] Output saved to: %OUTPUT_DIR%\!VIDEO_NAME!
            echo.
        )
    )
)

echo ============================================
echo  All done! Check: %OUTPUT_DIR%
echo ============================================
echo.
pause
