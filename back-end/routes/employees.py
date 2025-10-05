from flask import Blueprint, jsonify, session, redirect
from db import mysql

employees_bp = Blueprint('employees_bp', __name__)

# Employee dashboard
@employees_bp.route('/dashboard')
def dashboard():
    if 'role' not in session or session['role'] != 'employee':
        return redirect('/login')
    return "Welcome Employee! Dashboard coming soon."

# API: List all employees
@employees_bp.route('/list', methods=['GET'])
def get_employees():
    if 'role' not in session or session['role'] != 'employee':
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name, designation, salary FROM employees")
    data = cur.fetchall()
    cur.close()

    return jsonify(data)

