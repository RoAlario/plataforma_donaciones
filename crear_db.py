from app import create_app
from app.extensions import db
from app.models import Usuario, Rol, Categoria
from werkzeug.security import generate_password_hash
from datetime import datetime

app = create_app()

with app.app_context():
    db.create_all()
    print("Tablas creadas correctamente.")

    for nombre_rol in ['Admin', 'Usuario']:
        if not Rol.query.filter_by(nombre=nombre_rol).first():
            db.session.add(Rol(nombre=nombre_rol))
    db.session.commit()
    print("Roles creados.")

    categorias = ['Ropa', 'Muebles', 'Medicamentos', 'Juguetes', 'Electrónico', 'Alimento', 'Otro']
    for nombre in categorias:
        if not Categoria.query.filter_by(nombreCategoria=nombre).first():
            db.session.add(Categoria(nombreCategoria=nombre))
    db.session.commit()
    print("Categorías creadas.")

    if not Usuario.query.filter_by(email='juan.perez@ejemplo.com').first():
        rol_usuario = Rol.query.filter_by(nombre='Usuario').first()
        db.session.add(Usuario(
            nombre='Juan Pérez Rodríguez', email='juan.perez@ejemplo.com',
            telefono='1234567890', ubicacion='Mendoza, Argentina',
            contrasena=generate_password_hash('123456'),
            fechaAltaUsuario=datetime(2022, 3, 15),
            cantDonaciones=0, puedeCrearCampanias=False,
            id_rol=rol_usuario.id_rol
        ))
        print("Usuario de prueba creado -> juan.perez@ejemplo.com / 123456")

    if not Usuario.query.filter_by(email='admin@plataforma.com').first():
        rol_admin = Rol.query.filter_by(nombre='Admin').first()
        db.session.add(Usuario(
            nombre='Administrador', email='admin@plataforma.com',
            telefono='1234567890', ubicacion='Mendoza, Argentina',
            contrasena=generate_password_hash('admin123'),
            fechaAltaUsuario=datetime(2022, 1, 1),
            cantDonaciones=0, puedeCrearCampanias=True,
            id_rol=rol_admin.id_rol
        ))
        print("Admin de prueba creado -> admin@plataforma.com / admin123")

    db.session.commit()
    print("Base de datos lista para usar.")
