from flask import Blueprint, session, redirect

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/dashboard')
def dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/login')
    return "Welcome Admin! Dashboard coming soon."
