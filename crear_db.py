from app import create_app
from app.extensions import db
from app.models import Rol, Categoria, EstadoPublicacion

app = create_app()

def crear_roles_iniciales():
    for nombre_rol in ['Admin', 'Usuario']:
        if not Rol.query.filter_by(nombre=nombre_rol).first():
            db.session.add(Rol(nombre=nombre_rol))
    db.session.commit()

def crear_categorias_iniciales():
    categorias = ['Ropa', 'Muebles', 'Medicamentos', 'Juguetes', 'Electrónico', 'Alimento', 'Otro']
    for nombre in categorias:
        if not Categoria.query.filter_by(nombreCategoria=nombre).first():
            db.session.add(Categoria(nombreCategoria=nombre))
    db.session.commit()

def crear_estados_iniciales():
    estados = ['Disponible', 'En progreso', 'Entregado', 'Cancelado']
    for nombre in estados:
        if not EstadoPublicacion.query.filter_by(nombreEP=nombre).first():
            db.session.add(EstadoPublicacion(nombreEP=nombre))
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        crear_roles_iniciales()
        crear_categorias_iniciales()
        crear_estados_iniciales()
        print("Base de datos creada e inicializada correctamente.")
