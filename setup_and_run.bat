@echo off
:: Run vCard QR Flask app with Waitress (global Python install, no venv)

echo Installing required Python packages globally (or user-wide)...
python -m pip install --upgrade pip
pip install flask qrcode pillow pycryptodome waitress

echo Starting Flask application using Waitress...
python -m waitress --listen=0.0.0.0:8080 app:app

pause
