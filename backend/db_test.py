import mysql.connector
from mysql.connector import Error

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='admin',
        password='Ardra@2006#@$',
        database='payroll'
    )
    if conn.is_connected():
        print("Connected to MariaDB!")
        conn.close()
except Error as e:
    print(f"Error: {e}")
