import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'glow_secret_key_2026'

# --- THE FIX: ALLOW LARGE IMAGE DATA (16MB) ---
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

# Firebase Setup
cred = credentials.Certificate("serviceAccountKey.json")
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
            user = auth.create_user(email=email, password=pw)
            db.collection('users').document(user.uid).set({
                'name': name, 'email': email, 'password': pw
            })
            session['user_id'] = user.uid
            session['user_name'] = name
            return redirect(url_for('profile'))
        except:
            flash("Signup failed. Try a different email.")
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pw = request.form.get('password')
        
        # --- ADMIN LOGIN LOGIC ---
        if email == "admin@glowthesis.com" and pw == "admin123":
            session['user_id'] = 'ADMIN'
            session['user_name'] = 'System Admin'
            return redirect(url_for('admin'))
        
        # --- REGULAR USER LOGIN ---
        try:
            user = auth.get_user_by_email(email)
            u_data = db.collection('users').document(user.uid).get().to_dict()
            if u_data and u_data.get('password') == pw:
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
        # We catch the image data but don't need to save it to a folder
        # for a simulation-based demo.
        session['goal'] = request.form.get('goal')
        session['sun'] = request.form.get('sun')
        return redirect(url_for('results'))
    return render_template('analyse.html')

@app.route('/results')
def results():
    g = session.get('goal', 'acne')
    recs = {
        'acne': {'morning': 'Salicylic Wash', 'evening': 'Retinoid', 'tip': 'Clean pillowcases.'},
        'redness': {'morning': 'Gentle Cleanser', 'evening': 'Cica Cream', 'tip': 'No hot water.'},
        'texture': {'morning': 'Vitamin C', 'evening': 'AHA Serum', 'tip': 'SPF is vital.'},
        'pigment': {'morning': 'SPF 50', 'evening': 'Niacinamide', 'tip': 'Avoid peak sun.'}
    }
    return render_template('results.html', advice=recs.get(g), sun=session.get('sun'))

@app.route('/profile')
def profile():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    
    # 1. Get User Info
    user_doc = db.collection('users').document(user_id).get().to_dict()
    
    # 2. Get Scan History (Ordered by date)
    scans_ref = db.collection('users').document(user_id).collection('scans').order_by('timestamp', direction='DESCENDING').stream()
    
    scan_history = []
    for s in scans_ref:
        scan_history.append(s.to_dict())

    scans_ref = db.collection('users').document(user_id).collection('scans').order_by('timestamp', direction='DESCENDING').stream()

    scan_history = []
    for s in scans_ref:
        data = s.to_dict()
        data['id'] = s.id  # <--- THIS IS THE KEY! We need the Firestore document ID
        scan_history.append(data)

    return render_template('profile.html', 
                           name=user_doc.get('name', 'Glow User'), 
                           goal=user_doc.get('goal', 'Set a goal'),
                           scans=scan_history)

@app.route('/admin')
def admin():  # <--- This is the name Flask looks for
    if session.get('user_id') != 'ADMIN':
        flash("Access Denied: Admins Only.")
        return redirect(url_for('home'))

    users_ref = db.collection('users').stream()
    all_users = []
    for u in users_ref:
        user_data = u.to_dict()
        user_data['id'] = u.id  # Crucial for the table to work!
        all_users.append(user_data)
        
    return render_template('admin.html', users=all_users)

@app.route('/save_scan', methods=['POST'])
def save_scan():
    if not session.get('user_id'):
        flash("Please log in to save your results.")
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    
    # Collect data from the hidden inputs in the form
    data = {
        'image_data': request.form.get('image_data'),
        'goal': request.form.get('goal'),
        'timestamp': datetime.now(),
        'clarity': 88  # Placeholder for your AI score
    }

    # Push to Firebase sub-collection
    db.collection('users').document(user_id).collection('scans').add(data)
    
    flash("Successfully saved to your dashboard!")
    return redirect(url_for('profile'))


@app.route('/update_goal', methods=['POST'])
def update_goal(): # <--- Flask looks for this name
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    new_goal = request.form.get('goal')
    user_id = session.get('user_id')
    
    # Update the goal in Firestore
    db.collection('users').document(user_id).update({
        'goal': new_goal
    })
    
    # Update the session so the UI reflects the change immediately
    session['goal'] = new_goal 
    
    return redirect(url_for('profile'))

@app.route('/delete_scan/<scan_id>')
def delete_scan(scan_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    
    # Delete the specific document from the user's scan history
    db.collection('users').document(user_id).collection('scans').document(scan_id).delete()
    
    flash("Record deleted permanently.")
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)