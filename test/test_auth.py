import pytest
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app import create_app, db
from app.models import (Usuario, Rol, Categoria, Publicacion, EstadoPublicacion,
                         SolicitudDonacion, EstadoSolicitudDonacion, Campana,
                         EstadoCampana, Direccion)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def app():
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })

    with app.app_context():
        db.create_all()

        # Roles
        rol_usuario = Rol(nombre='Usuario')
        rol_admin = Rol(nombre='Admin')
        db.session.add_all([rol_usuario, rol_admin])
        db.session.flush()

        # Categorías
        cat_alimento = Categoria(nombreCategoria='Alimento')
        cat_ropa = Categoria(nombreCategoria='Ropa')
        db.session.add_all([cat_alimento, cat_ropa])
        db.session.flush()

        # Estados de publicación
        estado_disponible = EstadoPublicacion(nombreEP='Disponible')
        estado_evaluar = EstadoPublicacion(nombreEP='A evaluar')
        db.session.add_all([estado_disponible, estado_evaluar])

        db.session.commit()

        yield app

        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def rol_usuario():
    return Rol.query.filter_by(nombre='Usuario').first()


@pytest.fixture
def cat_alimento():
    return Categoria.query.filter_by(nombreCategoria='Alimento').first()


@pytest.fixture
def estado_disponible():
    return EstadoPublicacion.query.filter_by(nombreEP='Disponible').first()


# ── Helpers ──────────────────────────────────────────────────────────

def crear_usuario(app, nombre, email, telefono, password='clave123',
                  puede_crear=False, rol_id=None):
    """Crea un usuario directamente en la DB (sin pasar por el registro)."""
    with app.app_context():
        rol = rol_id or Rol.query.filter_by(nombre='Usuario').first().id_rol
        usuario = Usuario(
            nombre=nombre,
            email=email,
            telefono=telefono,
            contrasena=generate_password_hash(password),
            id_rol=rol,
            puedeCrearCampanias=puede_crear,
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario.codUsuario


def crear_publicacion(app, usuario_id, categoria_id, estado_id,
                      titulo='Donación de prueba', fecha_venc=None):
    """Crea una publicación directamente en la DB."""
    with app.app_context():
        pub = Publicacion(
            titulo=titulo,
            descripcionPublicacion='Descripción de prueba',
            ubicacion='Calle Falsa 123',
            codCategoria=categoria_id,
            codUsuario=usuario_id,
            codEstadoPublicacion=estado_id,
            fechaVencimiento=fecha_venc,
        )
        db.session.add(pub)
        db.session.commit()
        return pub.nroPublicacion


def login(client, email, password):
    """Hace login via el test client (POST al form)."""
    return client.post('/login', data={
        'email': email,
        'contrasena': password,
    }, follow_redirects=True)


# ══════════════════════════════════════════════════════════════════════
# 1. REGISTRO DE USUARIO
# ══════════════════════════════════════════════════════════════════════

class TestRegistro:
    """Tests del proceso de registro de usuario."""

    def test_registro_guarda_usuario_en_db(self, app, client):
        """Verifica que después del registro + verificación, el usuario queda en la DB."""
        with app.app_context():
            # Paso 1: enviar form de registro
            client.post('/registro', data={
                'nombre': 'Juan Perez',
                'email': 'juan@test.com',
                'telefono': '1122334455',
                'ubicacion': 'Buenos Aires',
                'contrasena': 'clave123',
                'repetir_contrasena': 'clave123',
            }, follow_redirects=True)

            # Paso 2: obtener el código de la sesión y verificar
            with client.session_transaction() as sess:
                codigo = sess.get('registro_pendiente', {}).get('codigo', '')

            digitos = {f'd{i+1}': codigo[i] for i in range(6)}
            client.post('/verificar', data=digitos, follow_redirects=True)

            # Paso 3: verificar que el usuario existe en la DB
            usuario = Usuario.query.filter_by(email='juan@test.com').first()
            assert usuario is not None, \
                "El usuario no se guardó en la base de datos"
            assert usuario.nombre == 'Juan Perez'

    def test_contrasena_esta_hasheada(self, app, client):
        """Verifica que la contraseña NO se guarda en texto plano."""
        with app.app_context():
            client.post('/registro', data={
                'nombre': 'Maria Lopez',
                'email': 'maria@test.com',
                'telefono': '1199887766',
                'ubicacion': 'Córdoba',
                'contrasena': 'micontraseña',
                'repetir_contrasena': 'micontraseña',
            }, follow_redirects=True)

            with client.session_transaction() as sess:
                codigo = sess.get('registro_pendiente', {}).get('codigo', '')

            digitos = {f'd{i+1}': codigo[i] for i in range(6)}
            client.post('/verificar', data=digitos, follow_redirects=True)

            usuario = Usuario.query.filter_by(email='maria@test.com').first()
            assert usuario is not None

            # La contraseña en texto plano NO debe coincidir con lo guardado
            assert usuario.contrasena != 'micontraseña', \
                "La contraseña se guardó en texto plano (debería estar hasheada)"

            # Pero check_password_hash debe poder verificarla
            assert check_password_hash(usuario.contrasena, 'micontraseña'), \
                "El hash de la contraseña no es válido"


# ══════════════════════════════════════════════════════════════════════
# 2. LOGIN CORRECTO E INCORRECTO
# ══════════════════════════════════════════════════════════════════════

class TestLogin:
    """Tests del proceso de login."""

    def test_login_correcto(self, app, client):
        """Verifica que con email y contraseña correctos se puede loguear."""
        crear_usuario(app, 'Carlos', 'carlos@test.com', '1111111111', 'miClave')

        response = login(client, 'carlos@test.com', 'miClave')

        # Debe redirigir al home de donaciones (200 después del redirect)
        assert response.status_code == 200
        # La sesión debe tener el usuario_id
        with client.session_transaction() as sess:
            assert 'usuario_id' in sess, \
                "El login no guardó usuario_id en la sesión"

    def test_login_contrasena_incorrecta(self, app, client):
        """Verifica que con contraseña incorrecta se rechaza el login."""
        crear_usuario(app, 'Pedro', 'pedro@test.com', '2222222222', 'claveReal')

        response = login(client, 'pedro@test.com', 'claveIncorrecta')

        # Debe quedarse en la página de login (sin sesión)
        with client.session_transaction() as sess:
            assert 'usuario_id' not in sess, \
                "El login aceptó una contraseña incorrecta"

    def test_login_email_inexistente(self, app, client):
        """Verifica que con un email que no existe se rechaza el login."""
        response = login(client, 'noexiste@test.com', 'cualquiera')

        with client.session_transaction() as sess:
            assert 'usuario_id' not in sess, \
                "El login aceptó un email inexistente"


# ══════════════════════════════════════════════════════════════════════
# 3. PERMISOS DE CAMPAÑA
# ══════════════════════════════════════════════════════════════════════

class TestPermisosCampana:
    """Tests de permisos para crear campañas."""

    def test_usuario_sin_permiso_ve_mensaje(self, app, client):
        """Un usuario SIN puedeCrearCampanias ve el mensaje de sin permiso."""
        user_id = crear_usuario(app, 'Ana', 'ana@test.com', '3333333333',
                                puede_crear=False)
        login(client, 'ana@test.com', 'clave123')

        response = client.get('/campana/publicar')

        assert response.status_code == 200
        assert b'sin_permiso' in response.data or b'permiso' in response.data.lower() \
            or b'No ten' in response.data, \
            "El usuario sin permiso debería ver un mensaje de sin permiso"

    def test_usuario_con_permiso_ve_formulario(self, app, client):
        """Un usuario CON puedeCrearCampanias ve el formulario de publicación."""
        user_id = crear_usuario(app, 'Roberto', 'roberto@test.com', '4444444444',
                                puede_crear=True)
        login(client, 'roberto@test.com', 'clave123')

        response = client.get('/campana/publicar')

        assert response.status_code == 200
        # Debe contener campos del formulario
        assert b'titulo' in response.data.lower() or b'camp' in response.data.lower(), \
            "El usuario con permiso debería ver el formulario de campaña"

    def test_usuario_sin_permiso_no_puede_crear_campana(self, app, client):
        """Un usuario SIN permiso no puede crear una campaña aunque intente POST."""
        user_id = crear_usuario(app, 'Luis', 'luis@test.com', '5555555555',
                                puede_crear=False)
        login(client, 'luis@test.com', 'clave123')

        with app.app_context():
            cat = Categoria.query.first()

        response = client.post('/campana/publicar', data={
            'titulo': 'Campaña test',
            'descripcion': 'Test',
            'ubicacion': 'Calle Test',
            'categoria_id': cat.codCategoria,
            'cantidad': '10',
            'fecha_fin': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        }, follow_redirects=True)

        with app.app_context():
            total = Campana.query.count()
            assert total == 0, \
                "Un usuario sin permiso no debería poder crear campañas"


# ══════════════════════════════════════════════════════════════════════
# 4. LÍMITE DE SOLICITUDES (2 pendientes máximo)
# ══════════════════════════════════════════════════════════════════════

class TestLimiteSolicitudes:
    """Tests del límite de 2 solicitudes pendientes por usuario."""

    def test_dos_solicitudes_se_aceptan(self, app, client):
        """Un usuario puede hacer 2 solicitudes de donación."""
        # Crear donante y receptor
        donante_id = crear_usuario(app, 'Donante', 'donante@test.com', '6666666666')
        receptor_id = crear_usuario(app, 'Receptor', 'receptor@test.com', '7777777777')

        login(client, 'receptor@test.com', 'clave123')

        with app.app_context():
            estado = EstadoPublicacion.query.filter_by(nombreEP='Disponible').first()

            # Crear 2 publicaciones de otro usuario
            pub1 = crear_publicacion(app, donante_id, 1, estado.codEstadoPublicacion,
                                     titulo='Donación 1')
            pub2 = crear_publicacion(app, donante_id, 1, estado.codEstadoPublicacion,
                                     titulo='Donación 2')

        # Hacer 2 solicitudes
        with app.app_context():
            pub1_id = Publicacion.query.filter_by(titulo='Donación 1').first().nroPublicacion
            pub2_id = Publicacion.query.filter_by(titulo='Donación 2').first().nroPublicacion

        resp1 = client.post(f'/donacion/{pub1_id}/solicitar', data={
            'razon': 'Necesito esta donación para ayudar a mi familia'
        }, follow_redirects=True)
        resp2 = client.post(f'/donacion/{pub2_id}/solicitar', data={
            'razon': 'También necesito esta otra donación urgentemente'
        }, follow_redirects=True)

        with app.app_context():
            total = SolicitudDonacion.query.filter_by(
                usuario_id=receptor_id,
                estado=EstadoSolicitudDonacion.PENDIENTE
            ).count()
            assert total == 2, \
                f"Se esperaban 2 solicitudes pendientes, pero hay {total}"

    def test_tercera_solicitud_es_rechazada(self, app, client):
        """Un usuario con 2 solicitudes pendientes NO puede hacer una 3ra."""
        donante_id = crear_usuario(app, 'Donante2', 'donante2@test.com', '8888888888')
        receptor_id = crear_usuario(app, 'Receptor2', 'receptor2@test.com', '9999999999')

        login(client, 'receptor2@test.com', 'clave123')

        with app.app_context():
            estado = EstadoPublicacion.query.filter_by(nombreEP='Disponible').first()

            pub1 = crear_publicacion(app, donante_id, 1, estado.codEstadoPublicacion, 'Pub 1')
            pub2 = crear_publicacion(app, donante_id, 1, estado.codEstadoPublicacion, 'Pub 2')
            pub3 = crear_publicacion(app, donante_id, 1, estado.codEstadoPublicacion, 'Pub 3')

        with app.app_context():
            ids = [
                Publicacion.query.filter_by(titulo=f'Pub {i}').first().nroPublicacion
                for i in range(1, 4)
            ]

        # Hacer las 2 primeras (deben aceptarse)
        client.post(f'/donacion/{ids[0]}/solicitar', data={
            'razon': 'Primera solicitud válida con más de 10 caracteres'
        }, follow_redirects=True)
        client.post(f'/donacion/{ids[1]}/solicitar', data={
            'razon': 'Segunda solicitud válida también con suficientes caracteres'
        }, follow_redirects=True)

        # La 3ra debe ser rechazada
        with app.app_context():
            antes = SolicitudDonacion.query.filter_by(usuario_id=receptor_id).count()

        client.post(f'/donacion/{ids[2]}/solicitar', data={
            'razon': 'Tercera solicitud que debería ser rechazada por límite'
        }, follow_redirects=True)

        with app.app_context():
            despues = SolicitudDonacion.query.filter_by(usuario_id=receptor_id).count()
            assert despues == antes, \
                f"La 3ra solicitud debería ser rechazada. Antes: {antes}, Después: {despues}"


# ══════════════════════════════════════════════════════════════════════
# 5. PUBLICACIÓN DE DONACIÓN (fecha vencimiento para alimentos)
# ══════════════════════════════════════════════════════════════════════

class TestPublicacionDonacion:
    """Tests de validación al publicar una donación."""

    def test_alimento_sin_fecha_venc_fallla(self, app, client):
        """Publicar alimento SIN fecha de vencimiento debe fallar."""
        user_id = crear_usuario(app, 'FoodUser', 'food@test.com', '1010101010')
        login(client, 'food@test.com', 'clave123')

        with app.app_context():
            cat = Categoria.query.filter_by(nombreCategoria='Alimento').first()

        response = client.post('/publicar', data={
            'titulo': 'Lata de arroz',
            'descripcion': 'Arroz de 1kg',
            'direccion': 'Calle Alimentos 100',
            'categoria_id': cat.codCategoria,
            'fecha_vencimiento': '',  # <-- sin fecha
        }, follow_redirects=True)

        with app.app_context():
            pubs = Publicacion.query.filter_by(titulo='Lata de arroz').count()
            assert pubs == 0, \
                "No debería guardarse una publicación de alimento sin fecha de vencimiento"

    def test_alimento_con_fecha_venc_guarda(self, app, client):
        """Publicar alimento CON fecha de vencimiento futura debe guardarse."""
        user_id = crear_usuario(app, 'FoodUser2', 'food2@test.com', '2020202020')
        login(client, 'food2@test.com', 'clave123')

        fecha_futura = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')

        with app.app_context():
            cat = Categoria.query.filter_by(nombreCategoria='Alimento').first()

        response = client.post('/publicar', data={
            'titulo': 'Lata de tomate',
            'descripcion': 'Tomate triturado',
            'direccion': 'Calle Conserva 200',
            'categoria_id': cat.codCategoria,
            'fecha_vencimiento': fecha_futura,
        }, follow_redirects=True)

        with app.app_context():
            pub = Publicacion.query.filter_by(titulo='Lata de tomate').first()
            assert pub is not None, \
                "La publicación de alimento con fecha futura debería guardarse"

    def test_alimento_con_fecha_vencida_fallla(self, app, client):
        """Publicar alimento con fecha de vencimiento pasada debe fallar."""
        user_id = crear_usuario(app, 'FoodUser3', 'food3@test.com', '3030303030')
        login(client, 'food3@test.com', 'clave123')

        fecha_pasada = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

        with app.app_context():
            cat = Categoria.query.filter_by(nombreCategoria='Alimento').first()

        response = client.post('/publicar', data={
            'titulo': 'Leche vencida',
            'descripcion': 'Leche enter',
            'direccion': 'Calle Vencida 300',
            'categoria_id': cat.codCategoria,
            'fecha_vencimiento': fecha_pasada,
        }, follow_redirects=True)

        with app.app_context():
            pubs = Publicacion.query.filter_by(titulo='Leche vencida').count()
            assert pubs == 0, \
                "No debería guardarse una publicación con fecha de vencimiento pasada"
