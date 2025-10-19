from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error, IntegrityError
from werkzeug.security import check_password_hash
import traceback
import os
from datetime import datetime

app = Flask(__name__)
# use env SECRET_KEY in production; fallback to a dev key (replace before production)
app.secret_key = os.environ.get('SECRET_KEY') or 'Amal#@$'

# ----------------------
# Database Configuration
# ----------------------
db_config = {
    'host': 'localhost',
    'user': 'admin',
    'password': 'Ardra@2006#@$',
    'database': 'payroll'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Exception as e:
        # full traceback to Flask logger
        app.logger.exception("DB connect error")
        return None

# ----------------------
# Routes
# ----------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = (request.form.get('username') or '').strip()
    password = (request.form.get('password') or '').strip()
    app.logger.debug("Login attempt username=%r password_len=%d", username, len(password))

    if not username or not password:
        return render_template('login.html', error='Please enter username and password.')

    conn = get_db_connection()
    if conn is None:
        return render_template('login.html', error='Database connection error. See server log.')

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, username, TRIM(password) AS password FROM users WHERE username = %s LIMIT 1", (username,))
        user = cur.fetchone()
        cur.close()

        app.logger.debug("DB returned user: %r", {k:v for k,v in (user or {}).items() if k!='password'})

        if not user:
            return render_template('login.html', error='Invalid credentials.')

        stored = (user.get('password') or '').strip()
        if stored != password:
            return render_template('login.html', error='Invalid credentials.')

        session['user'] = user['username']
        session['user_id'] = user['id']
        return redirect(url_for('dashboard'))

    except Exception as e:
        # log full traceback and return a short message to the client
        app.logger.exception("Error during login DB operation")
        # For development only: include exception text in the page to help debugging
        return render_template('login.html', error=f"Database error: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if session.get('user') is None:
        return redirect(url_for('login'))

    conn = get_db_connection()
    totals = {'employees': 0, 'pending_payslips': 0, 'departments': 0}
    employees = []
    departments = []
    pending_payslips = []

    if conn:
        try:
            cur = conn.cursor()

            # total employees (only count employees from employees table)
            try:
                cur.execute("SELECT COUNT(*) FROM employees")
                totals['employees'] = int(cur.fetchone()[0] or 0)
            except Exception:
                totals['employees'] = 0

            # pending payslips count (only for existing employees)
            try:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM payslips p
                    INNER JOIN employees e ON p.employee_id = e.id
                    WHERE p.status = 'pending'
                """)
                totals['pending_payslips'] = int(cur.fetchone()[0] or 0)
            except Exception:
                totals['pending_payslips'] = 0

            # departments count
            try:
                cur.execute("SELECT COUNT(*) FROM departments")
                totals['departments'] = int(cur.fetchone()[0] or 0)
            except Exception:
                totals['departments'] = 0

            # employees list - read from employees table (use name as username)
            try:
                cur.execute("""
                    SELECT id, name, email, phone, designation, department,
                           DATE_FORMAT(join_date, '%%Y-%%m-%%d') AS join_date, salary
                    FROM employees
                    ORDER BY id DESC
                    LIMIT 100
                """)
                rows = cur.fetchall()
                employees = [{'id': r[0], 'username': r[1], 'role': 'employee'} for r in rows]
            except Exception:
                employees = []

            # departments list
            try:
                cur.execute("SELECT id, name FROM departments ORDER BY name")
                rows = cur.fetchall()
                departments = [{'id': r[0], 'name': r[1]} for r in rows]
            except Exception:
                departments = []

            # pending payslips (join to users for username)
            try:
                cur.execute("""
                    SELECT p.id, p.employee_id, p.period, p.gross, p.deductions, p.net, p.status, u.username
                    FROM payslips p
                    LEFT JOIN users u ON p.employee_id = u.id
                    WHERE p.status = 'pending'
                    ORDER BY p.created_at DESC
                    LIMIT 100
                """)
                rows = cur.fetchall()
                pending_payslips = [
                    {
                        'id': r[0],
                        'employee_id': r[1],
                        'period': r[2].isoformat() if hasattr(r[2], 'isoformat') else str(r[2]),
                        'gross': float(r[3]) if r[3] is not None else 0,
                        'deductions': float(r[4]) if r[4] is not None else 0,
                        'net': float(r[5]) if r[5] is not None else 0,
                        'status': r[6],
                        'username': (r[7] or 'Unknown')
                    } for r in rows
                ]
            except Exception:
                pending_payslips = []

            cur.close()
        except Exception:
            app.logger.exception("Error querying dashboard data")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return render_template('dashboard.html',
                           totals=totals,
                           employees=employees,
                           departments=departments,
                           pending_payslips=pending_payslips)

@app.route('/employees', methods=['POST'])
def create_employee():
    if session.get('user') is None:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    app.logger.debug("Create employee payload: %r", data)

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name required'}), 400

    email = (data.get('email') or None)
    phone = (data.get('phone') or None)
    designation = (data.get('designation') or None)
    department = (data.get('department') or None)
    join_date = (data.get('join_date') or None)
    try:
        salary = float(data.get('salary')) if data.get('salary') not in (None, '') else 0.0
    except Exception:
        salary = 0.0

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'database connection failed'}), 500

    try:
        cur = conn.cursor()
        try:
            # Insert into employees WITHOUT touching users or setting user_id
            cur.execute(
                "INSERT INTO employees (name, email, phone, designation, department, join_date, salary) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (name, email, phone, designation, department, join_date, salary)
            )
            conn.commit()
            new_id = cur.lastrowid
            cur.close()
            return jsonify({'success': True, 'id': new_id, 'name': name}), 201
        except Exception as e:
            app.logger.exception("DB insert error creating employee")
            cur.close()
            return jsonify({'error': 'database insert failed', 'detail': str(e)}), 400
    finally:
        try: conn.close()
        except: pass

@app.route('/employees/<int:emp_id>', methods=['GET', 'PUT', 'DELETE'])
def employee_detail(emp_id):
    if session.get('user') is None:
        return jsonify({'error': 'unauthorized'}), 401

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'database connection failed'}), 500

    try:
        cur = conn.cursor(dictionary=True)
        if request.method == 'GET':
            cur.execute("""
                SELECT id, name, email, phone, designation, department,
                       DATE_FORMAT(join_date, '%Y-%m-%d') AS join_date, salary
                FROM employees
                WHERE id = %s
                LIMIT 1
            """, (emp_id,))
            row = cur.fetchone()
            cur.close()
            if not row:
                return jsonify({'error': 'not found'}), 404
            # ensure 'name' exists and return same key names frontend expects
            return jsonify({
                'id': row['id'],
                'name': row.get('name'),
                'username': row.get('name'),
                'email': row.get('email'),
                'phone': row.get('phone'),
                'designation': row.get('designation'),
                'department': row.get('department'),
                'join_date': row.get('join_date'),
                'salary': float(row['salary']) if row.get('salary') is not None else None
            }), 200

        if request.method == 'PUT':
            data = request.get_json() or {}
            name = (data.get('name') or '').strip()
            if not name:
                cur.close()
                return jsonify({'error': 'name required'}), 400
            email = data.get('email')
            phone = data.get('phone')
            designation = data.get('designation')
            department = data.get('department')
            join_date = data.get('join_date')
            salary = data.get('salary')

            fields = ["name = %s"]; params = [name]
            fields.append("email = %s"); params.append(email)
            fields.append("phone = %s"); params.append(phone)
            fields.append("designation = %s"); params.append(designation)
            fields.append("department = %s"); params.append(department)
            fields.append("join_date = %s"); params.append(join_date)
            fields.append("salary = %s"); params.append(salary)
            params.append(emp_id)

            sql = "UPDATE employees SET " + ", ".join(fields) + " WHERE id = %s"
            try:
                cur.execute(sql, tuple(params))
                conn.commit()
            except Exception as e:
                cur.close()
                app.logger.exception("Error updating employee")
                return jsonify({'error': str(e)}), 400

            cur.close()
            return jsonify({'success': True, 'id': emp_id, 'name': name}), 200

        if request.method == 'DELETE':
            # prevent deleting if related payslips exist; handle FK or delete payslips first
            try:
                cur.execute("DELETE FROM employees WHERE id = %s", (emp_id,))
                conn.commit()
            except Exception as e:
                cur.close()
                return jsonify({'error': 'Cannot delete employee; related records exist or error: ' + str(e)}), 400
            cur.close()
            return jsonify({'success': True, 'id': emp_id}), 200
    finally:
        try: conn.close()
        except: pass

@app.route('/payslips', methods=['POST'])
def create_payslip():
    if session.get('user') is None:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    emp_id = data.get('employee_id')
    period = data.get('period')  # expect "YYYY-MM"
    if not emp_id or not period:
        return jsonify({'error': 'employee_id and period required'}), 400

    try:
        period_date = datetime.strptime(period + '-01', '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'invalid period format, expected YYYY-MM'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'database connection failed'}), 500

    try:
        cur = conn.cursor()
        # ensure employee exists (employees table is authoritative)
        cur.execute("SELECT id, name, salary FROM employees WHERE id = %s LIMIT 1", (emp_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({'error': 'employee not found'}), 404

        # avoid duplicate
        cur.execute("SELECT id FROM payslips WHERE employee_id = %s AND period = %s LIMIT 1", (emp_id, period_date))
        if cur.fetchone():
            cur.close()
            return jsonify({'error': 'Payslip for this employee and month already exists'}), 409

        gross = float(data.get('gross') or (row[2] if row[2] is not None else 3000.00))
        deductions = float(data.get('deductions') or round(gross * 0.10, 2))
        net = round(gross - deductions, 2)

        cur.execute(
            "INSERT INTO payslips (employee_id, period, gross, deductions, net, status, origin_status) VALUES (%s, %s, %s, %s, %s, 'pending', %s)",
            (emp_id, period_date, gross, deductions, net, 'employees')
        )
        conn.commit()
        new_id = cur.lastrowid
        app.logger.info("Created payslip id=%s for employee_id=%s period=%s", new_id, emp_id, period_date)

        cur.close()
        return jsonify({
            'success': True,
            'id': new_id,
            'employee_id': emp_id,
            'period': period,
            'gross': gross,
            'deductions': deductions,
            'net': net
        }), 201

    except Exception as e:
        app.logger.exception("Error creating payslip")
        return jsonify({'error': str(e)}), 500
    finally:
        try: conn.close()
        except: pass

@app.route('/payslips/<int:pid>', methods=['DELETE'])
def delete_payslip(pid):
    if session.get('user') is None:
        return jsonify({'error': 'unauthorized'}), 401

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'database connection failed'}), 500

    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM payslips WHERE id = %s LIMIT 1", (pid,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({'error': 'not found'}), 404

        status = row[0]
        # only allow deleting pending payslips via this action
        if status != 'pending':
            cur.close()
            return jsonify({'error': 'only pending payslips can be deleted/marked paid'}, 400)

        cur.execute("DELETE FROM payslips WHERE id = %s", (pid,))
        conn.commit()
        cur.close()
        return jsonify({'success': True, 'id': pid}), 200

    except Exception as e:
        app.logger.exception("Error deleting payslip %s", pid)
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.route('/employees', methods=['GET'])
def list_employees():
    """Return JSON list of employees (for client-side refresh)."""
    if session.get('user') is None:
        return jsonify({'error': 'unauthorized'}), 401

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'database connection failed'}), 500

    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, name, email, phone, designation, department, DATE_FORMAT(join_date, '%Y-%m-%d') AS join_date, salary FROM employees ORDER BY id DESC LIMIT 1000")
            rows = cur.fetchall()
            employees = [
                {
                    'id': r[0],
                    'name': r[1],
                    'username': r[1],           # keep username for compatibility
                    'email': r[2],
                    'phone': r[3],
                    'designation': r[4],
                    'department': r[5],
                    'join_date': r[6],
                    'salary': float(r[7]) if r[7] is not None else 0
                } for r in rows
            ]
        except Exception:
            employees = []
        cur.close()
        return jsonify({'employees': employees}), 200
    finally:
        try: conn.close()
        except: pass

@app.route('/employees/<int:emp_id>', methods=['DELETE'])
def delete_employee(emp_id):
    if session.get('user') is None:
        return jsonify({'error': 'unauthorized'}), 401

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'database connection failed'}), 500

    try:
        cur = conn.cursor(dictionary=True)
        # ensure employee exists
        cur.execute("SELECT id FROM employees WHERE id = %s LIMIT 1", (emp_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({'error': 'not found'}), 404

        try:
            # start transaction: delete dependent payslips then employee
            cur.execute("DELETE FROM payslips WHERE employee_id = %s", (emp_id,))
            cur.execute("DELETE FROM employees WHERE id = %s", (emp_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            app.logger.exception("Error deleting employee %s", emp_id)
            cur.close()
            return jsonify({'error': 'delete failed', 'detail': str(e)}), 400

        cur.close()
        return jsonify({'success': True, 'id': emp_id}), 200

    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
