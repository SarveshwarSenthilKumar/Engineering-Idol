@echo off
echo ========================================
echo SCOPE Database Build Script
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python and try again.
    pause
    exit /b 1
)

echo Step 1: Creating database schema...
python createEventsDatabase.py
if errorlevel 1 (
    echo ERROR: Database creation failed!
    pause
    exit /b 1
)
echo SUCCESS!
echo.

echo Step 2: Generating fake data...
python fake_data_generator.py
if errorlevel 1 (
    echo ERROR: Fake data generation failed!
    pause
    exit /b 1
)
echo SUCCESS!
echo.

echo ========================================
echo Verification
echo ========================================
if exist events.db (
    echo Database file created successfully!
    for %%A in (events.db) do echo Size: %%~zA bytes
) else (
    echo ERROR: Database file not found!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Run: python app.py
echo 2. Open: http://localhost:5000
echo 3. Login with default credentials
echo.
pause
