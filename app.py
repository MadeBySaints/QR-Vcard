from flask import Flask, render_template, request, redirect, session, send_file
import os
import hashlib
import qrcode
from datetime import datetime
import json
import shutil

app = Flask(__name__)
app.secret_key = 'b6f6380c02b54d2cb561305ae2f1e9ca0281ce1a77bbde680000aad8b853ccea'  # Change this!
# Open a terminal and use:
# python -c 'import secrets; print(secrets.token_hex(32))'
# paste the result above.

# Configuration
USERS_FILE = 'data/users.txt'
QR_DATA_DIR = 'data'
QR_IMAGE_DIR = 'static/qrcodes'  # Parent directory for all user QR codes
PEPPER = 'dec5a2630515519ec51afc9e258748d81e99a54157002b694027ea54e6725c04'  # Change this!
# Open a terminal and use:
# python -c 'import secrets; print(secrets.token_hex(32))'
# paste the result above.
COLLECT_USER_DATA = True
ENCRYPT_DATA = True

# Ensure directories exist
os.makedirs(QR_DATA_DIR, exist_ok=True)
os.makedirs(QR_IMAGE_DIR, exist_ok=True)

def hash_password(password):
    return hashlib.sha256((password + PEPPER).encode()).hexdigest()

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        lines = f.readlines()
    return {line.split('|')[1]: line.strip().split('|') for line in lines}

def save_user(uid, username, email, hashed_password):
    with open(USERS_FILE, 'a') as f:
        f.write(f"{uid}|{username}|{email}|{hashed_password}\n")

def get_next_uid():
    if not os.path.exists(USERS_FILE):
        return 100010001
    with open(USERS_FILE, 'r') as f:
        lines = f.readlines()
    if not lines:
        return 100010001
    return int(lines[-1].split('|')[0]) + 1

def ensure_user_dir(uid):
    """Create user-specific directory if it doesn't exist"""
    user_dir = os.path.join(QR_IMAGE_DIR, str(uid))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def save_qr_data(uid, qr_name, vcard_string, filename):
    user_file = os.path.join(QR_DATA_DIR, f"user_{uid}.txt")
    data = {
        'qr_name': qr_name,
        'timestamp': datetime.now().isoformat(),
        'filename': filename,
        'vcard_data': vcard_string if not ENCRYPT_DATA else None,
        'vcard_encrypted': encrypt_data(vcard_string) if ENCRYPT_DATA else None
    }
    with open(user_file, 'a') as f:
        f.write(json.dumps(data) + '\n')

def encrypt_data(data):
    """One-way hash data using SHA-256 with application pepper"""
    if not isinstance(data, str):
        data = str(data)
    return hashlib.sha256((data + PEPPER).encode()).hexdigest()

# Example usage in save_qr_data()
def save_qr_data(uid, qr_name, vcard_string, filename):
    user_file = os.path.join(QR_DATA_DIR, f"user_{uid}.txt")
    data = {
        'qr_name': qr_name,
        'timestamp': datetime.now().isoformat(),
        'filename': filename,
        'vcard_hash': encrypt_data(vcard_string)  # Stores hash instead of raw data
    }
    with open(user_file, 'a') as f:
        f.write(json.dumps(data) + '\n')

@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')
    return redirect('/dashboard')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if username in users:
            return "User already exists"
        uid = get_next_uid()
        hashed = hash_password(password)
        save_user(uid, username, email, hashed)
        session['user'] = {'uid': uid, 'username': username}
        return redirect('/dashboard')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        hashed = hash_password(password)
        if username not in users or users[username][3] != hashed:
            return "Invalid credentials"
        session['user'] = {'uid': int(users[username][0]), 'username': username}
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    uid = session['user']['uid']
    user_file = os.path.join(QR_DATA_DIR, f"user_{uid}.txt")
    qrs = []
    
    if os.path.exists(user_file):
        with open(user_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    qrs.append({
                        'name': data['qr_name'],
                        'date': data['timestamp'],
                        'filename': data['filename']
                    })
                except:
                    continue

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    total = len(qrs)
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    page_start = (page - 1) * per_page
    page_end = page_start + per_page

    return render_template(
        'dashboard.html',
        qrs=qrs,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        page_start=page_start,
        page_end=page_end
    )

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    if 'user' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        try:
            uid = session['user']['uid']
            user_dir = ensure_user_dir(uid)  # Get user-specific directory
            qr_name = request.form['qr_name'].strip()
            qr_size = int(request.form.get('qr_size', 10))
            
            # Build vCard
            vcard_lines = ["BEGIN:VCARD", "VERSION:3.0"]
            
            # Standard fields
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            if first_name or last_name:
                vcard_lines.append(f"N:{last_name};{first_name};;;")
                vcard_lines.append(f"FN:{first_name} {last_name}")
            
            # Contact info
            if phone := request.form.get('phone_cell', '').strip():
                vcard_lines.append(f"TEL;TYPE=CELL:{phone}")
            if email := request.form.get('email', '').strip():
                vcard_lines.append(f"EMAIL:{email}")
            if company := request.form.get('company', '').strip():
                vcard_lines.append(f"ORG:{company}")
            
            # Address
            street = request.form.get('street', '').strip()
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            zip_code = request.form.get('zip', '').strip()
            country = request.form.get('country', '').strip()
            
            if any([street, city, state, zip_code, country]):
                addr = f"{street};{city};{state};{zip_code};{country}"
                vcard_lines.append(f"ADR;TYPE=WORK:;;{addr}")
            
            if website := request.form.get('website', '').strip():
                vcard_lines.append(f"URL:{website}")
            
            # Custom fields
            custom_keys = [k for k in request.form if k.startswith('custom_key_')]
            for key in custom_keys:
                idx = key.split('_')[-1]
                custom_value = request.form.get(f'custom_value_{idx}', '').strip()
                if custom_value:
                    custom_key = request.form.get(key, '').strip()
                    vcard_lines.append(f"{custom_key.upper()}:{custom_value}")
            
            vcard_lines.append("END:VCARD")
            vcard = "\n".join(vcard_lines)
            
            # Generate QR code in user's directory
            filename = f"{int(datetime.now().timestamp())}.png"
            filepath = os.path.join(user_dir, filename)
            
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=qr_size,
                border=4,
            )
            qr.add_data(vcard)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(filepath)
            
            if COLLECT_USER_DATA:
                save_qr_data(uid, qr_name, vcard, filename)
            
            return redirect('/dashboard')
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return redirect('/generate')
    
    return render_template('generate.html')

@app.route('/track/<filename>')
def track(filename):
    if 'user' not in session:
        return redirect('/login')
    
    uid = session['user']['uid']
    user_dir = os.path.join(QR_IMAGE_DIR, str(uid))
    return send_file(os.path.join(user_dir, filename), mimetype='image/png')

@app.route('/delete_qr/<filename>', methods=['POST'])
def delete_qr(filename):
    if 'user' not in session:
        return redirect('/login')
    
    uid = session['user']['uid']
    user_file = os.path.join(QR_DATA_DIR, f"user_{uid}.txt")
    user_dir = os.path.join(QR_IMAGE_DIR, str(uid))
    
    # Remove from user's data file
    if os.path.exists(user_file):
        with open(user_file, 'r') as f:
            lines = f.readlines()
        
        with open(user_file, 'w') as f:
            for line in lines:
                try:
                    data = json.loads(line.strip())
                    if data['filename'] != filename:
                        f.write(line)
                except:
                    continue
    
    # Delete the QR image file
    qr_path = os.path.join(user_dir, filename)
    if os.path.exists(qr_path):
        os.remove(qr_path)
    
    return redirect('/dashboard')

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user' not in session:
        return redirect('/login')
    
    uid = session['user']['uid']
    username = session['user']['username']
    password = request.form.get('password', '')
    
    # Verify password
    users = load_users()
    if username not in users or users[username][3] != hash_password(password):
        return "Incorrect password", 401
    
    # Delete user's QR directory
    user_dir = os.path.join(QR_IMAGE_DIR, str(uid))
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
    
    # Delete user data file
    user_file = os.path.join(QR_DATA_DIR, f"user_{uid}.txt")
    if os.path.exists(user_file):
        os.remove(user_file)
    
    # Remove from users.txt
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            lines = f.readlines()
        
        with open(USERS_FILE, 'w') as f:
            for line in lines:
                if not line.startswith(f"{uid}|"):
                    f.write(line)
    
    session.pop('user', None)
    return redirect('/login')
