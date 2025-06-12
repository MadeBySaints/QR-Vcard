@echo off
:: Fixed setup script for vCard QR Flask app
:: Resolves virtual environment path issues

echo Setting up Python virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment
    pause
    exit /b
)

echo Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo Failed to activate virtual environment
    pause
    exit /b
)

echo Installing required Python packages...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip
    pause
    exit /b
)

pip install flask qrcode pillow pycryptodome
if errorlevel 1 (
    echo Failed to install packages
    pause
    exit /b
)

echo Running the Flask app...
set FLASK_APP=app.py
set FLASK_ENV=development

:: Fix for launcher error - use python -m flask instead of flask.exe
echo.
echo Starting Flask application...
python -m flask run
if errorlevel 1 (
    echo Failed to start Flask application
    pause
    exit /b
)

pause