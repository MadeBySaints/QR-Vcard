# QR-Vcard
A QR-VCard Generator with a front facing flask website


📇 vCard QR Code Generator (Flask-based)
A full-featured Flask web app for generating, managing, and serving vCard QR codes with optional data encryption and flat-file user storage. Built for privacy-conscious users and small businesses, this app requires no database and supports per-user dashboards, custom fields, and downloadable codes.

🔧 Features
🔐 User Registration & Login with secure password hashing (sha256 + pepper)

🧾 vCard QR Generation with:

Names, phone, email, company, website

Work address support

Unlimited custom fields

🗃️ Per-user QR Management (list, view, delete)

📁 Flat File Storage (no DB required)

🧊 QR Code Output with high error correction

🔒 vCard data hashing for privacy (no raw vCard stored - optional)

🧼 Simple and clean HTML templates

🛰️ Production-ready using Waitress (WSGI)

📦 Installation
Requirements
Python 3.7+

Git (optional)

Internet connection for dependency install

# Install Instructions (Windows)
Clone or download the repo and extract to a folder of your choosing

Run the setup script "setup_and_run.bat" (installs required dependencies & starts app):


Then visit:

👉 http://localhost:8080

🔐 Account System
User credentials stored in data/users.txt

QR metadata stored in data/user_<uid>.txt

Each user gets a subfolder under static/qrcodes/<uid>/


🌐 Running in Production
Uses Waitress for production:

python -m waitress --listen=0.0.0.0:8080 app:app

To make this available to people on the web, you will need to do some port forwarding.
There are many guides on port forwarding available on the internet.

MIT License

