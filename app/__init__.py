from flask import Flask
from app.extensions import db, mail

def create_app():
    app = Flask(__name__)

    app.secret_key = 'clave_secreta_cambiar'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plataforma.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAIL_SERVER']   = 'smtp.gmail.com'
    app.config['MAIL_PORT']     = 587
    app.config['MAIL_USE_TLS']  = True
    app.config['MAIL_USERNAME'] = 'utnfrm.10@gmail.com'
    app.config['MAIL_PASSWORD'] = 'fezr xfck miad zofe'

    db.init_app(app)
    mail.init_app(app)

    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    return app