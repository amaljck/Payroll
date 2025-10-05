from flask import Flask, jsonify
from flask_mysqldb import MySQL

app = Flask(__name__)

# Database Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'amaljck'
app.config['MYSQL_PASSWORD'] = 'Ardra@2006#@$'
app.config['MYSQL_DB'] = 'payroll'

mysql = MySQL(app)

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT 'Connected to MariaDB!'")
    result = cur.fetchone()
    cur.close()
    return jsonify({'message': result[0]})

if __name__ == '__main__':
    app.run(debug=True)
