import pytest
from app import create_app, db
from app.models import Usuario, Rol


# ── Fixtures ─────────────────────────────────────────────────────────
# Un "fixture" es un recurso que los tests necesitan para funcionar.
# Este crea una app Flask con una base de datos en memoria (temporal)
# que se destruye al terminar cada test.

@pytest.fixture
def app():
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })

    with app.app_context():
        db.create_all()

        # Crear el rol "Usuario" (obligatorio para crear usuarios)
        rol = Rol(nombre='Usuario')
        db.session.add(rol)
        db.session.commit()

        yield app  # <-- acá se entrega la app al test

        db.drop_all()  # <-- al terminar, se borra todo


# ── Tests ────────────────────────────────────────────────────────────

class TestCrearUsuarios:
    """Tests para verificar que se pueden crear usuarios en la base de datos."""

    def test_crear_un_usuario(self, app):
        """Verifica que se puede crear un solo usuario correctamente."""
        with app.app_context():
            rol = Rol.query.filter_by(nombre='Usuario').first()

            usuario = Usuario(
                nombre='Juan Perez',
                email='juan@test.com',
                telefono='1122334455',
                contrasena='clave123',
                id_rol=rol.id_rol
            )
            db.session.add(usuario)
            db.session.commit()

            # Verificar que se creó exactamente 1 usuario
            assert Usuario.query.count() == 1, \
                "Se esperaba 1 usuario en la base de datos"

            # Verificar que los datos sean correctos
            Juan = Usuario.query.filter_by(email='juan@test.com').first()
            assert Juan is not None, \
                "No se encontró el usuario con email 'juan@test.com'"
            assert Juan.nombre == 'Juan Perez', \
                f"El nombre debería ser 'Juan Perez', pero se obtuvo '{Juan.nombre}'"
            assert Juan.telefono == '1122334455', \
                f"El teléfono debería ser '1122334455', pero se obtuvo '{Juan.telefono}'"

    def test_crear_10_usuarios(self, app):
        """Verifica que se pueden crear 10 usuarios en un bucle."""
        with app.app_context():
            rol = Rol.query.filter_by(nombre='Usuario').first()

            # Crear 10 usuarios
            for i in range(1, 11):
                usuario = Usuario(
                    nombre=f"Usuario{i}",
                    email=f"usuario{i}@test.com",
                    telefono=f"11{i:08d}",
                    contrasena="clave123",
                    id_rol=rol.id_rol
                )
                db.session.add(usuario)

            db.session.commit()

            # Verificar que se crearon los 10
            total = Usuario.query.count()
            assert total == 10, \
                f"Se esperaban 10 usuarios, pero se crearon {total}"

    def test_emails_son_unicos(self, app):
        """Verifica que no se pueden crear dos usuarios con el mismo email."""
        with app.app_context():
            rol = Rol.query.filter_by(nombre='Usuario').first()

            usuario1 = Usuario(
                nombre='Ana',
                email='ana@test.com',
                telefono='1111111111',
                contrasena='clave123',
                id_rol=rol.id_rol
            )
            db.session.add(usuario1)
            db.session.commit()

            # Intentar crear otro usuario con el mismo email
            usuario2 = Usuario(
                nombre='Otra Ana',
                email='ana@test.com',  # <-- email duplicado
                telefono='2222222222',
                contrasena='clave456',
                id_rol=rol.id_rol
            )
            db.session.add(usuario2)

            # Debe fallar por email duplicado
            with pytest.raises(Exception):
                db.session.commit()

    def test_buscar_usuario_por_email(self, app):
        """Verifica que se puede buscar un usuario por su email."""
        with app.app_context():
            rol = Rol.query.filter_by(nombre='Usuario').first()

            usuario = Usuario(
                nombre='Carlos',
                email='carlos@test.com',
                telefono='3333333333',
                contrasena='clave789',
                id_rol=rol.id_rol
            )
            db.session.add(usuario)
            db.session.commit()

            encontrado = Usuario.query.filter_by(email='carlos@test.com').first()
            assert encontrado is not None, \
                "No se encontró el usuario con email 'carlos@test.com'"
            assert encontrado.nombre == 'Carlos', \
                f"El nombre debería ser 'Carlos', pero se obtuvo '{encontrado.nombre}'"

    def test_usuario_tiene_rol(self, app):
        """Verifica que un usuario tiene el rol asignado correctamente."""
        with app.app_context():
            rol = Rol.query.filter_by(nombre='Usuario').first()

            usuario = Usuario(
                nombre='Maria',
                email='maria@test.com',
                telefono='4444444444',
                contrasena='clave000',
                id_rol=rol.id_rol
            )
            db.session.add(usuario)
            db.session.commit()

            assert usuario.rol is not None, \
                "El usuario debería tener un rol asignado"
            assert usuario.rol.nombre == 'Usuario', \
                f"El rol debería ser 'Usuario', pero se obtuvo '{usuario.rol.nombre}'"
            assert usuario.es_usuario() == True, \
                "El método es_usuario() debería devolver True"
            assert usuario.es_admin() == False, \
                "El método es_admin() debería devolver False"
