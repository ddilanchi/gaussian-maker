@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set INPUT_DIR=%SCRIPT_DIR%input
set OUTPUT_DIR=%SCRIPT_DIR%output

echo ============================================
echo  Gaussian Maker
echo ============================================
echo  Input folder:  %INPUT_DIR%
echo  Output folder: %OUTPUT_DIR%
echo ============================================
echo.

:: Check for video files in input folder
set VIDEO_COUNT=0
for %%F in ("%INPUT_DIR%\*.mp4" "%INPUT_DIR%\*.MOV" "%INPUT_DIR%\*.mov" "%INPUT_DIR%\*.avi" "%INPUT_DIR%\*.mkv" "%INPUT_DIR%\*.webm") do (
    if exist "%%F" set /a VIDEO_COUNT+=1
)

if %VIDEO_COUNT%==0 (
    echo No video files found in input folder.
    echo.
    echo Drop your video files ^(.mp4, .MOV, .avi, .mkv^) into:
    echo   %INPUT_DIR%
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
        gm run "%%F" --output "%OUTPUT_DIR%\!VIDEO_NAME!" --trainer nerfstudio --fps 2 --format ply --format splat
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
echo  All done. Check the output folder:
echo  %OUTPUT_DIR%
echo ============================================
echo.
pause
