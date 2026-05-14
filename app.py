from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import os
import random
import string

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret_key_change_me')

# Fetch the Neon database URL from the environment (Render will provide this)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    # Connects to Neon Postgres instead of a local SQLite file
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def generate_random_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def init_db():
    # If there's no DB URL yet, don't try to build the tables
    if not DATABASE_URL:
        return
        
    conn = get_db()
    cur = conn.cursor()
    # Note: Postgres uses SERIAL instead of AUTOINCREMENT
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY, 
                        username TEXT UNIQUE NOT NULL, 
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,
                        is_approved INTEGER DEFAULT 0,
                        confirm_code TEXT
                    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS invites (
                        id SERIAL PRIMARY KEY, 
                        code TEXT UNIQUE, 
                        is_used INTEGER DEFAULT 0
                    )''')
    
    # Create default admin if none exists
    cur.execute('SELECT * FROM users WHERE username = %s', ('admin',))
    admin = cur.fetchone()
    if not admin:
        hashed_pw = generate_password_hash('admin123') 
        cur.execute('INSERT INTO users (username, password, role, is_approved) VALUES (%s, %s, %s, %s)', 
                     ('admin', hashed_pw, 'admin', 1))
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) # Returns row as dictionary
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            if user['is_approved'] == 0:
                flash(f"Account pending! Give this code to the admin: {user['confirm_code']}")
                return redirect(url_for('login'))
            
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('admin_dash') if user['role'] == 'admin' else url_for('user_dash'))
        else:
            flash('Invalid credentials.')
            
    return render_template('index.html', view='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        invite_code = request.form['invite_code']
        
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute('SELECT * FROM invites WHERE code = %s AND is_used = 0', (invite_code,))
        invite = cur.fetchone()
        
        if not invite:
            flash('Invalid or already used invite code.')
            cur.close()
            conn.close()
            return redirect(url_for('register'))
            
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        if cur.fetchone():
            flash('Username taken.')
            cur.close()
            conn.close()
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        confirm_code = generate_random_code(8)
        
        cur.execute('INSERT INTO users (username, password, role, is_approved, confirm_code) VALUES (%s, %s, %s, %s, %s)',
                     (username, hashed_pw, 'user', 0, confirm_code))
        cur.execute('UPDATE invites SET is_used = 1 WHERE code = %s', (invite_code,))
        conn.commit()
        cur.close()
        conn.close()
        
        flash(f'Account created! Give this confirmation code to the admin to unlock your account: {confirm_code}')
        return redirect(url_for('login'))
        
    return render_template('index.html', view='register')

@app.route('/admin', methods=['GET', 'POST'])
def admin_dash():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        if 'generate_invite' in request.form:
            new_invite = generate_random_code(6)
            cur.execute('INSERT INTO invites (code) VALUES (%s)', (new_invite,))
            flash(f'New Invite Code Generated: {new_invite}')
            
        elif 'approve_user' in request.form:
            c_code = request.form['confirm_code']
            cur.execute('SELECT * FROM users WHERE confirm_code = %s AND is_approved = 0', (c_code,))
            user = cur.fetchone()
            if user:
                cur.execute('UPDATE users SET is_approved = 1 WHERE confirm_code = %s', (c_code,))
                flash(f"User '{user['username']}' has been approved!")
            else:
                flash('Invalid confirmation code.')
        conn.commit()
        
    cur.execute('SELECT * FROM invites WHERE is_used = 0')
    invites = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('index.html', view='admin', invites=invites)

@app.route('/user', methods=['GET', 'POST'])
def user_dash():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        user_input = request.form['future_data']
        flash(f'You entered: {user_input} (This will be saved in the future!)')
        
    return render_template('index.html', view='user')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
