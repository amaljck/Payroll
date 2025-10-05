from flask import Flask
from db import mysql
from config import Config
import os

# Correct path to your front-end folder
frontend_path = os.path.join(os.path.dirname(__file__), '../front-end')

# Initialize Flask
app = Flask(
    __name__,
    static_folder=frontend_path,  # Serve front-end as static files
    template_folder=os.path.join(frontend_path, 'html')  # optional: if you put HTML here
)
app.config.from_object(Config)

# Initialize MySQL
mysql.init_app(app)

# Import and register blueprints
from routes.auth import auth_bp
from routes.employees import employees_bp
from routes.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(employees_bp, url_prefix='/employees')
app.register_blueprint(admin_bp, url_prefix='/admin')

if __name__ == '__main__':
    app.run(debug=True)

