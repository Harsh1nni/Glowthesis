import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import cv2
import numpy as np
import base64
import random
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json

#port = int(os.environ.get("PORT", 5000))
#app.run(host="0.0.0.0", port=port)

app = Flask(__name__)
app.secret_key = 'glow_secret_key_2026'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Firebase
firebase_key = json.loads(os.environ.get("FIREBASE_KEY"))

cred = credentials.Certificate(firebase_key)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        pw = request.form.get('password')
        name = request.form.get('name')

        try:
            hashed_pw = generate_password_hash(pw)

            user = auth.create_user(email=email, password=pw)

            db.collection('users').document(user.uid).set({
                'name': name,
                'email': email,
                'password': hashed_pw
            })

            session['user_id'] = user.uid
            session['user_name'] = name

            return redirect(url_for('profile'))

        except Exception as e:
            print("SIGNUP ERROR:", e)
            flash(str(e))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pw = request.form.get('password')

        if email == "admin@glowthesis.com" and pw == "admin123":
            session['user_id'] = 'ADMIN'
            session['user_name'] = 'System Admin'
            return redirect(url_for('admin'))

        try:
            user = auth.get_user_by_email(email)
            u_data = db.collection('users').document(user.uid).get().to_dict()

            if u_data and check_password_hash(u_data.get('password'), pw):
                session['user_id'] = user.uid
                session['user_name'] = u_data.get('name')
                return redirect(url_for('profile'))
            else:
                flash("Incorrect password.")

        except:
            flash("User not found.")

    return render_template('login.html')


@app.route('/analyse', methods=['GET', 'POST'])
def analyse():
    if request.method == 'POST':
        img_data = request.form.get('image_data')
        print("DEBUG IMAGE RECEIVED:", img_data[:30] if img_data else "NO IMAGE")

        goal = request.form.get('goal')
        sun = request.form.get('sun')

        if not img_data or img_data.strip() == "":
            flash("Please capture or upload an image first.")
            return redirect(url_for('analyse'))

        clarity, redness, confidence = perform_skin_analysis(img_data)

        print("DEBUG ANALYSIS:", clarity, redness, confidence)
        if clarity == 0 and redness == 0:
            flash("No clear face detected. Please ensure your face is visible with good lighting.")
            return redirect(url_for('analyse'))

        
        if redness > 30:
            final = "redness"
        elif clarity < 50:
            final = "texture"
        else:
            final = goal

        recs = {
            'acne': {'morning': 'Salicylic Cleanser', 'evening': 'Retinoid', 'tip': 'Keep skin clean and avoid touching face.'},
            'redness': {'morning': 'Gentle Cleanser', 'evening': 'Cica Cream', 'tip': 'Avoid hot water and harsh products.'},
            'texture': {'morning': 'Vitamin C Serum', 'evening': 'AHA Exfoliant', 'tip': 'Exfoliate regularly but gently.'},
            'pigment': {'morning': 'SPF 50', 'evening': 'Niacinamide', 'tip': 'Avoid sun exposure during peak hours.'},
            'normal': {'morning': 'Cleanser + Moisturiser', 'evening': 'Hydration Cream', 'tip': 'Maintain a balanced routine.'}
        }

        return render_template(
            'results.html',
            image_data=img_data,
            clarity=clarity,
            redness=redness,
            confidence=confidence,
            goal=final,
            sun=sun,
            advice=recs.get(final) 
        )

    return render_template('analyse.html')

'''
# results
@app.route('/results')
def results():
    clarity = session.get('live_clarity', 0)
    redness = session.get('live_redness', 0)
    confidence = session.get('confidence', 0)
    print("DEBUG RESULTS:", clarity, redness, confidence)
    goal = session.get('goal', 'acne')

    # (scan + goal combined)
    if redness > 30:
        final = "redness"
    elif clarity < 50:
        final = "texture"
    else:
        final = goal

    recs = {
        'acne': {'morning': 'Salicylic Cleanser', 'evening': 'Retinoid', 'tip': 'Keep skin clean and avoid touching face.'},
        'redness': {'morning': 'Gentle Cleanser', 'evening': 'Cica Cream', 'tip': 'Avoid hot water and harsh products.'},
        'texture': {'morning': 'Vitamin C Serum', 'evening': 'AHA Exfoliant', 'tip': 'Exfoliate regularly but gently.'},
        'pigment': {'morning': 'SPF 50', 'evening': 'Niacinamide', 'tip': 'Avoid sun exposure during peak hours.'},
        'normal': {'morning': 'Cleanser + Moisturiser', 'evening': 'Hydration Cream', 'tip': 'Maintain a balanced routine.'}
    }

    return render_template('results.html',
                            advice=recs.get(final),
                            sun=session.get('sun'),
                            goal=final,
                            clarity=clarity,
                            redness=redness,
                            confidence=confidence,
                            image_data=session.get('temp_image'))

                            '''

@app.route('/profile')
def profile():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    user_doc = db.collection('users').document(user_id).get().to_dict()

    scans_ref = db.collection('users').document(user_id)\
        .collection('scans').order_by('timestamp', direction='DESCENDING').stream()

    scan_history = []
    for s in scans_ref:
        data = s.to_dict()

        scan_history.append({
            'id': s.id,
            'image_data': data.get('image_data', ''),
            'goal': data.get('goal', 'unknown'),
            'timestamp': data.get('timestamp', None),
            'clarity': data.get('clarity', 0),
            'redness': data.get('redness', 0),
            'confidence': data.get('confidence', 0)
        })

    if scan_history:
        avg_clarity = sum([s['clarity'] for s in scan_history]) / len(scan_history)
        progress = round(min(100, avg_clarity), 1)
    else:
        progress = 0

    return render_template('profile.html',
                            name=user_doc.get('name', 'User'),
                            goal=user_doc.get('goal', 'Set goal'),
                            scans=scan_history,
                            progress=progress)

@app.route('/scan/<scan_id>')
def view_scan(scan_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    doc = db.collection('users')\
        .document(session['user_id'])\
        .collection('scans')\
        .document(scan_id)\
        .get()

    if not doc.exists:
        flash("Scan not found")
        return redirect(url_for('profile'))

    scan = doc.to_dict()

    return render_template('scan_detail.html', scan=scan)

def is_skin_present(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower = np.array([0, 30, 80])
    upper = np.array([25, 255, 255])

    mask = cv2.inRange(hsv, lower, upper)

    skin_ratio = np.sum(mask > 0) / mask.size

    print("DEBUG skin ratio:", skin_ratio)

    return skin_ratio > 0.30

# AI function 
def perform_skin_analysis(image_b64):
    print("DEBUG: function started")
    encoded_data = image_b64.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        print("DEBUG ERROR: image failed to decode")
        return 0, 0, 0

    print("DEBUG: image shape =", img.shape)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # face detection
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=3,
        minSize=(50, 50)
    )

    if len(faces) == 0:
        print("DEBUG: No face detected")
        return 0, 0, 0

    x, y, w, h = faces[0]
    face = img[y:y+h, x:x+w]

    img = face

    if not is_skin_present(img):
        print("DEBUG: No skin detected")
        return 0, 0, 0

    # normalise lighting
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    img = cv2.merge((l, a, b))
    img = cv2.cvtColor(img, cv2.COLOR_LAB2BGR)

    # redness (relative)
    mean_red = np.mean(img[:, :, 2])
    mean_green = np.mean(img[:, :, 1])
    redness = max(0, (mean_red - mean_green) / 2)

    # texture
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)
    edge_ratio = np.sum(edges > 0) / edges.size
    texture = 100 - (edge_ratio * 150)

    clarity = round(max(0, min(100, texture)), 1)
    redness = round(max(0, min(100, redness)), 1)

    confidence = round(random.uniform(75, 95), 1)

    return clarity, redness, confidence


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/save_scan', methods=['POST'])
def save_scan():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    img_data = request.form.get('image_data')
    goal = request.form.get('goal')

    # Run analysis again (so saved data is consistent)
    clarity, redness, confidence = perform_skin_analysis(img_data)

    data = {
        'image_data': img_data,
        'goal': goal,
        'timestamp': datetime.now(),
        'clarity': clarity,
        'redness': redness,
        'confidence': confidence
    }

    db.collection('users').document(session['user_id']).collection('scans').add(data)

    flash("Scan saved successfully!")
    return redirect(url_for('profile'))

@app.route('/admin')
def admin():
    if session.get('user_id') != 'ADMIN':
        return redirect(url_for('login'))

    users_ref = db.collection('users').stream()

    all_users = []
    for u in users_ref:
        data = u.to_dict()
        data['id'] = u.id
        all_users.append(data)

    return render_template('admin.html', users=all_users)

@app.route('/update_goal', methods=['POST'])
def update_goal():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    new_goal = request.form.get('goal')

    # update in Firestore
    db.collection('users').document(session['user_id']).update({
        'goal': new_goal
    })

    flash("Goal updated successfully!")
    return redirect(url_for('profile'))
@app.route('/delete_scan/<scan_id>', methods=['POST'])
def delete_scan(scan_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    db.collection('users')\
        .document(session['user_id'])\
        .collection('scans')\
        .document(scan_id)\
        .delete()

    flash("Scan deleted successfully.")
    return redirect(url_for('profile'))



if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

