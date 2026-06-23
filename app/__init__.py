import os
from flask import Flask
from app.extensions import db, mail
from dotenv import load_dotenv

def create_app():
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')) 
    app = Flask(__name__)

    app.secret_key = os.environ['SECRET_KEY']
    app.config['UPLOAD_FOLDER'] = os.path.join('app', 'static', 'fotos')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///donaciones.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAIL_SERVER']   = 'smtp.gmail.com'
    app.config['MAIL_PORT']     = 587
    app.config['MAIL_USE_TLS']  = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

    db.init_app(app)
    mail.init_app(app)

    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.donaciones.routes import donaciones_bp
    app.register_blueprint(donaciones_bp)
    
    from app.admin.routes import admin_bp
    app.register_blueprint(admin_bp)
    
    from app.routes import campana_bp
    app.register_blueprint(campana_bp)

    return app
