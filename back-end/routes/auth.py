from flask import Blueprint, request, redirect, session, flash, url_for, render_template
from db import mysql

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, password, role FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()

        if user:
            db_password = user['password']
            role = user['role']
            user_id = user['id']

            # Simple password check (later replace with hashing)
            if password == db_password:
                session['user_id'] = user_id
                session['role'] = role

                if role == 'admin':
                    return redirect('/admin/dashboard')
                else:
                    return redirect('/employees/dashboard')
            else:
                flash('Incorrect password', 'error')
        else:
            flash('Username not found', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
