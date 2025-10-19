import mysql.connector, traceback
conf = {'host':'localhost','user':'admin','password':'Ardra@2006#@$','database':'payroll'}
try:
    conn = mysql.connector.connect(**conf)
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users LIMIT 1")
    print(cur.fetchall())
    cur.close(); conn.close()
except Exception as e:
    print("DB connect/query error:")
    traceback.print_exc()
