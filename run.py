from app import create_app
from app.extensions import db
from app.models import Rol

app = create_app()

def crear_roles_iniciales():
    for nombre_rol in ['Admin', 'Usuario']:
        if not Rol.query.filter_by(nombre=nombre_rol).first():
            db.session.add(Rol(nombre=nombre_rol))
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        crear_roles_iniciales()
    app.run(debug=True)