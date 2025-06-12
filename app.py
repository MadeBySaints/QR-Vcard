from flask import Flask, render_template, request, redirect, session, send_file
import os
import hashlib
import qrcode
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this!

# Configuration
USERS_FILE = 'data/users.txt'
QR_DATA_DIR = 'data'
QR_IMAGE_DIR = 'static/qrcodes'
PEPPER = 'your-pepper-value-here'  # Change this!
COLLECT_USER_DATA = True
ENCRYPT_DATA = False

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

def save_qr_data(uid, qr_name, vcard_string, filename):
    user_file = os.path.join(QR_DATA_DIR, f"user_{uid}.txt")
    data = {
        'qr_name': qr_name,
        'timestamp': datetime.now().isoformat(),
        'filename': filename,
        'vcard_data': vcard_string
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
            qr_name = request.form['qr_name'].strip()
            qr_size = int(request.form.get('qr_size', 10))
            
            # Build vCard with all standard fields
            vcard_lines = ["BEGIN:VCARD", "VERSION:3.0"]
            
            # Standard fields
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            if first_name or last_name:
                vcard_lines.append(f"N:{last_name};{first_name};;;")
                vcard_lines.append(f"FN:{first_name} {last_name}")
            
            # Process all standard contact fields
            standard_fields = {
                'phone_cell': 'TEL;TYPE=CELL',
                'phone_office': 'TEL;TYPE=WORK',
                'fax': 'TEL;TYPE=FAX',
                'email': 'EMAIL',
                'company': 'ORG',
                'position': 'TITLE',
                'website': 'URL',
                'notes': 'NOTE'
            }
            
            for field, vcard_key in standard_fields.items():
                if value := request.form.get(field, '').strip():
                    vcard_lines.append(f"{vcard_key}:{value}")
            
            # Process address
            street = request.form.get('street', '').strip()
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            zip_code = request.form.get('zip', '').strip()
            country = request.form.get('country', '').strip()
            
            if any([street, city, state, zip_code, country]):
                addr = f";;{street};{city};{state};{zip_code};{country}"
                vcard_lines.append(f"ADR;TYPE=WORK:{addr}")
            
            # Process custom fields
            custom_keys = [k for k in request.form if k.startswith('custom_key_')]
            for key in custom_keys:
                idx = key.split('_')[-1]
                custom_value = request.form.get(f'custom_value_{idx}', '').strip()
                if custom_value:
                    custom_key = request.form.get(key, '').strip()
                    vcard_lines.append(f"{custom_key.upper()}:{custom_value}")
            
            vcard_lines.append("END:VCARD")
            vcard = "\n".join(vcard_lines)
            
            # Generate QR code
            filename = f"{uid}_{int(datetime.now().timestamp())}.png"
            filepath = os.path.join(QR_IMAGE_DIR, filename)
            
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

# Add these new routes to your Flask app

@app.route('/delete_qr/<filename>', methods=['POST'])
def delete_qr(filename):
    if 'user' not in session:
        return redirect('/login')
    
    uid = session['user']['uid']
    user_file = os.path.join(QR_DATA_DIR, f"user_{uid}.txt")
    
    # Find and remove the QR entry from user's data file
    if os.path.exists(user_file):
        with open(user_file, 'r') as f:
            lines = f.readlines()
        
        with open(user_file, 'w') as f:
            for line in lines:
                try:
                    data = json.loads(line.strip())
                    if data['filename'] != filename:
                        f.write(line)
                    else:
                        # Delete the QR image file
                        qr_path = os.path.join(QR_IMAGE_DIR, filename)
                        if os.path.exists(qr_path):
                            os.remove(qr_path)
                except:
                    continue
    
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
    
    # Delete all QR images
    user_file = os.path.join(QR_DATA_DIR, f"user_{uid}.txt")
    if os.path.exists(user_file):
        with open(user_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    qr_path = os.path.join(QR_IMAGE_DIR, data['filename'])
                    if os.path.exists(qr_path):
                        os.remove(qr_path)
                except:
                    continue
        # Delete user data file
        os.remove(user_file)
    
    # Remove user from users.txt
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            lines = f.readlines()
        
        with open(USERS_FILE, 'w') as f:
            for line in lines:
                if not line.startswith(f"{uid}|"):
                    f.write(line)
    
    # Clear session and redirect
    session.pop('user', None)
    return redirect('/login')

@app.route('/track/<filename>')
def track(filename):
    return send_file(os.path.join(QR_IMAGE_DIR, filename), mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)