from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'asdfghjkl'

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
    except Error as e:
        print(f"Error connecting to DB: {e}")
        return None

# ----------------------
# Routes
# ----------------------

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
