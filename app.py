from flask import Flask, render_template, request, redirect, url_for, session, flash
from extensions import db, mail
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
import random, string, re

app = Flask(__name__)

# ── Configuración ──────────────────────────────────────────────────────────────
app.secret_key = 'clave_secreta_cambiar'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plataforma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = 'utnfrm.10@gmail.com'    # ← cambiá esto
app.config['MAIL_PASSWORD'] = 'fezr xfck miad zofe'  # ← cambiá esto

db.init_app(app)
mail.init_app(app)

from models import Usuario, Rol

# ── Helpers ────────────────────────────────────────────────────────────────────
def generar_codigo():
    return ''.join(random.choices(string.digits, k=6))

def es_email_valido(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email)

def es_telefono_valido(tel):
    return re.match(r'^\d{7,14}$', tel)

def enviar_email(destinatario, asunto, cuerpo):
    """Envía un email. Lanza excepción si falla."""
    msg = Message(
        subject=asunto,
        sender=app.config['MAIL_USERNAME'],
        recipients=[destinatario]
    )
    msg.body = cuerpo
    mail.send(msg)

# ══════════════════════════════════════════════════════════════════════════════
# REGISTRO  →  VERIFICACIÓN
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    errores = {}

    if request.method == 'POST':
        nombre    = request.form.get('nombre', '').strip()
        email     = request.form.get('email', '').strip()
        telefono  = request.form.get('telefono', '').strip()
        ubicacion = request.form.get('ubicacion', '').strip()
        contra    = request.form.get('contrasena', '')
        contra2   = request.form.get('repetir_contrasena', '')

        # ── Validaciones ───────────────────────────────────────────────────
        if not nombre or len(nombre) < 2:
            errores['nombre'] = 'El nombre debe tener al menos 2 caracteres.'

        if not email:
            errores['email'] = 'El email es obligatorio.'
        elif not es_email_valido(email):
            errores['email'] = 'El formato del email no es válido.'
        elif Usuario.query.filter_by(email=email).first():
            # El email ya existe como usuario verificado en la BD
            errores['email'] = 'El correo electrónico ingresado ya se encuentra vinculado a una cuenta activa.'

        if not telefono or not es_telefono_valido(telefono):
            errores['telefono'] = 'El teléfono debe tener entre 7 y 14 dígitos.'

        if not contra or len(contra) < 6:
            errores['contrasena'] = 'La contraseña debe tener al menos 6 caracteres.'
        elif contra != contra2:
            errores['repetir_contrasena'] = 'Las contraseñas no coinciden.'

        if errores:
            return render_template('registro.html', errores=errores,
                                   valores={'nombre': nombre, 'email': email,
                                            'telefono': telefono, 'ubicacion': ubicacion})

        # ── Guardar datos en SESIÓN (NO en BD todavía) ─────────────────────
        codigo = generar_codigo()
        session['registro_pendiente'] = {
            'nombre':     nombre,
            'email':      email,
            'telefono':   telefono,
            'ubicacion':  ubicacion,
            'contrasena': generate_password_hash(contra),
            'codigo':     codigo,
        }

        # ── Intentar enviar el email ────────────────────────────────────────
        try:
            enviar_email(
                email,
                'Verificá tu cuenta',
                f'Tu código de verificación es: {codigo}\n\nIngresalo en la plataforma para activar tu cuenta.'
            )
        except Exception as e:
            # Si el mail falla, avisamos pero igual redirigimos
            # (en desarrollo podés ver el código en la consola)
            print(f'[MAIL ERROR] {e}')
            print(f'[DEV] Código de verificación para {email}: {codigo}')

        return redirect(url_for('verificar'))

    return render_template('registro.html', errores={}, valores={})


@app.route('/verificar', methods=['GET', 'POST'])
def verificar():
    pendiente = session.get('registro_pendiente')
    if not pendiente:
        return redirect(url_for('registro'))

    error = None

    if request.method == 'POST':
        digitos = [request.form.get(f'd{i}', '') for i in range(1, 7)]
        codigo_ingresado = ''.join(digitos)

        if codigo_ingresado == pendiente['codigo']:
            # Buscar rol Usuario (siempre existe porque lo cargamos al iniciar)
            rol_usuario = Rol.query.filter_by(nombre='Usuario').first()

            nuevo = Usuario(
                nombre              = pendiente['nombre'],
                email               = pendiente['email'],
                telefono            = pendiente['telefono'],
                ubicacion           = pendiente['ubicacion'],
                contrasena          = pendiente['contrasena'],
                id_rol              = rol_usuario.id_rol,
                puedeCrearCampanias = False,
            )
            db.session.add(nuevo)
            db.session.commit()

            session.pop('registro_pendiente', None)
            flash('¡Cuenta creada con éxito! Ya podés iniciar sesión.', 'success')
            return redirect(url_for('login'))
        else:
            error = 'El código ingresado no es correcto. Revisá tu email.'

    return render_template('verificar.html', error=error)


@app.route('/reenviar-codigo-registro')
def reenviar_codigo_registro():
    pendiente = session.get('registro_pendiente')
    if not pendiente:
        return redirect(url_for('registro'))

    # Generamos un código nuevo y lo actualizamos en sesión
    nuevo_codigo = generar_codigo()
    session['registro_pendiente'] = {**pendiente, 'codigo': nuevo_codigo}
    # Necesario para que Flask detecte el cambio en la sesión
    session.modified = True

    try:
        enviar_email(
            pendiente['email'],
            'Nuevo código de verificación',
            f'Tu nuevo código de verificación es: {nuevo_codigo}'
        )
    except Exception as e:
        print(f'[MAIL ERROR] {e}')
        print(f'[DEV] Nuevo código para {pendiente["email"]}: {nuevo_codigo}')

    return redirect(url_for('verificar'))


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email  = request.form.get('email', '').strip()
        contra = request.form.get('contrasena', '')

        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario or not check_password_hash(usuario.contrasena, contra):
            error = 'Email o contraseña incorrectos.'
        else:
            session['usuario_id'] = usuario.codUsuario
            flash(f'¡Bienvenido/a, {usuario.nombre}!', 'success')
            return redirect(url_for('home'))

    return render_template('login.html', error=error)


# ══════════════════════════════════════════════════════════════════════════════
# OLVIDÉ MI CONTRASEÑA
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/olvide-contrasena', methods=['GET', 'POST'])
def olvide_contrasena():
    """Paso 1: el usuario ingresa su email."""
    error  = None
    exito  = None

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario:
            error = 'No existe ninguna cuenta con ese email.'
        else:
            codigo = generar_codigo()
            usuario.codigoVerif = codigo
            db.session.commit()

            try:
                enviar_email(
                    email,
                    'Código para restablecer contraseña',
                    f'Tu código para restablecer la contraseña es: {codigo}\n\nSi no lo pediste, ignorá este mensaje.'
                )
                exito = 'Te enviamos un código a tu email. Ingresalo a continuación.'
            except Exception as e:
                print(f'[MAIL ERROR] {e}')
                print(f'[DEV] Código recuperación para {email}: {codigo}')
                exito = 'Te enviamos un código a tu email. Ingresalo a continuación.'

            session['email_recuperar'] = email
            return redirect(url_for('verificar_recuperacion'))

    return render_template('olvide_contrasena.html', error=error, exito=exito)


@app.route('/verificar-recuperacion', methods=['GET', 'POST'])
def verificar_recuperacion():
    """Paso 2: el usuario ingresa el código de 6 dígitos."""
    email = session.get('email_recuperar')
    if not email:
        return redirect(url_for('olvide_contrasena'))

    error = None

    if request.method == 'POST':
        digitos = [request.form.get(f'd{i}', '') for i in range(1, 7)]
        codigo_ingresado = ''.join(digitos)

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.codigoVerif == codigo_ingresado:
            # Código correcto → habilitamos el paso 3
            session['recuperacion_verificada'] = True
            return redirect(url_for('nueva_contrasena'))
        else:
            error = 'El código ingresado no es correcto.'

    return render_template('verificar_recuperacion.html', error=error)


@app.route('/nueva-contrasena', methods=['GET', 'POST'])
def nueva_contrasena():
    """Paso 3: el usuario ingresa su nueva contraseña."""
    email = session.get('email_recuperar')
    verificada = session.get('recuperacion_verificada')

    if not email or not verificada:
        return redirect(url_for('olvide_contrasena'))

    errores = {}

    if request.method == 'POST':
        contra  = request.form.get('contrasena', '')
        contra2 = request.form.get('repetir_contrasena', '')

        if not contra or len(contra) < 6:
            errores['contrasena'] = 'La contraseña debe tener al menos 6 caracteres.'
        elif contra != contra2:
            errores['repetir_contrasena'] = 'Las contraseñas no coinciden.'

        if not errores:
            usuario = Usuario.query.filter_by(email=email).first()
            usuario.contrasena  = generate_password_hash(contra)
            usuario.codigoVerif = None
            db.session.commit()

            session.pop('email_recuperar', None)
            session.pop('recuperacion_verificada', None)
            flash('¡Contraseña actualizada! Ya podés iniciar sesión.', 'success')
            return redirect(url_for('login'))

    return render_template('nueva_contrasena.html', errores=errores)


# ══════════════════════════════════════════════════════════════════════════════
# HOME (placeholder)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/home')
def home():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(usuario_id)
    return f'<h2>Hola {usuario.nombre}, bienvenido/a!</h2>'



# ══════════════════════════════════════════════════════════════════════════════
# DECORADORES DE ROL
# ══════════════════════════════════════════════════════════════════════════════

from functools import wraps

def login_requerido(f):
    """Redirige al login si no hay sesión activa."""
    @wraps(f)
    def decorador(*args, **kwargs):
        if not session.get('usuario_id'):
            flash('Tenés que iniciar sesión primero.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorador

def requiere_admin(f):
    """Solo permite acceso a usuarios con rol Admin."""
    @wraps(f)
    def decorador(*args, **kwargs):
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return redirect(url_for('login'))
        usuario = Usuario.query.get(usuario_id)
        if not usuario or not usuario.es_admin():
            flash('No tenés permisos para acceder a esa sección.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorador

def requiere_campania(f):
    """Solo permite acceso a usuarios con puedeCrearCampanias = True."""
    @wraps(f)
    def decorador(*args, **kwargs):
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return redirect(url_for('login'))
        usuario = Usuario.query.get(usuario_id)
        if not usuario or not usuario.puedeCrearCampanias:
            flash('No tenés permisos para crear campañas.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorador


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZAR BD Y ROLES
# ══════════════════════════════════════════════════════════════════════════════

def crear_roles_iniciales():
    """Crea los roles Admin y Usuario si no existen."""
    for nombre_rol in ['Admin', 'Usuario']:
        if not Rol.query.filter_by(nombre=nombre_rol).first():
            db.session.add(Rol(nombre=nombre_rol))
    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        crear_roles_iniciales()
    app.run(debug=True)