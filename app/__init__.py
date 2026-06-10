import os
from flask import Flask
from app.extensions import db, mail
from dotenv import load_dotenv

def create_app():
    load_dotenv() 
    app = Flask(__name__)

    app.secret_key = os.environ['SECRET_KEY']
    app.config['UPLOAD_FOLDER'] = os.path.join('app', 'static', 'fotos')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plataforma.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAIL_SERVER']   = 'smtp.gmail.com'
    app.config['MAIL_PORT']     = 587
    app.config['MAIL_USE_TLS']  = True
    app.config['MAIL_USERNAME'] = 'utnfrm.10@gmail.com'
    app.config['MAIL_PASSWORD'] = os.environ['MAIL_PASSWORD']

    db.init_app(app)
    mail.init_app(app)

    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.donaciones.routes import donaciones_bp
    app.register_blueprint(donaciones_bp)
    
    from app.routes import campana_bp
    app.register_blueprint(campana_bp)

    return app
