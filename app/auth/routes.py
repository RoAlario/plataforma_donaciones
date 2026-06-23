from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from app.extensions import db, mail
from app.models import Usuario, Rol
import random, string, re

import os
from werkzeug.utils import secure_filename

EXTENSIONES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'gif'}

def extension_valida(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS
auth_bp = Blueprint('auth', __name__)

def generar_codigo():
    return ''.join(random.choices(string.digits, k=6))

def es_email_valido(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email)

def es_telefono_valido(tel):
    return re.match(r'^\d{7,14}$', tel)

def enviar_email(destinatario, asunto, cuerpo):
    from flask import current_app
    msg = Message(
        subject=asunto,
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[destinatario]
    )
    msg.body = cuerpo
    mail.send(msg)

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    errores = {}
    
    if request.method == 'POST':
        nombre    = request.form.get('nombre', '').strip()
        email     = request.form.get('email', '').strip()
        telefono  = request.form.get('telefono', '').strip()
        ubicacion = request.form.get('ubicacion', '').strip()
        contra    = request.form.get('contrasena', '')
        contra2   = request.form.get('repetir_contrasena', '')

        if not nombre or len(nombre) < 3:
            errores['nombre'] = 'El nombre debe tener al menos 3 caracteres.'
        if not email:
            errores['email'] = 'El email es obligatorio.'
        elif not es_email_valido(email):
            errores['email'] = 'El formato del email no es válido.'
        elif Usuario.query.filter_by(email=email).first():
            errores['email'] = 'El correo electrónico ingresado ya se encuentra vinculado a una cuenta activa.'
        if not telefono or not es_telefono_valido(telefono):
            errores['telefono'] = 'El teléfono debe tener entre 7 y 14 dígitos.'
        if not ubicacion:
            errores['ubicacion'] = 'La ubicación es obligatoria.'
        if not contra or len(contra) < 6:
            errores['contrasena'] = 'La contraseña debe tener al menos 6 caracteres.'
        elif contra != contra2:
            errores['repetir_contrasena'] = 'Las contraseñas no coinciden.'

        # Foto de perfil (opcional)
        from flask import current_app
        foto_nombre = None
        foto = request.files.get('foto_perfil')
        if foto and foto.filename != '':
            if extension_valida(foto.filename):
                foto_nombre = secure_filename(foto.filename)
                carpeta = current_app.config['UPLOAD_FOLDER']
                os.makedirs(carpeta, exist_ok=True)
                foto.save(os.path.join(carpeta, foto_nombre))
            else:
                errores['foto_perfil'] = 'Solo se permiten imágenes (jpg, png, gif).'
                
        if errores:
            return render_template('registro.html', errores=errores,
                                   valores={'nombre': nombre, 'email': email,
                                            'telefono': telefono, 'ubicacion': ubicacion})

        codigo = generar_codigo()
        session['registro_pendiente'] = {
            'nombre': nombre, 'email': email, 'telefono': telefono,
            'ubicacion': ubicacion, 'contrasena': generate_password_hash(contra),
            'codigo': codigo,
            'foto_perfil': foto_nombre,
        }
        
        try:
            enviar_email(email, 'Verificá tu cuenta',
                f'Tu código de verificación es: {codigo}')
        except Exception as e:
            print(f'[MAIL ERROR] {e}')
            flash('No se pudo enviar el email de verificación. Podés reenviarlo desde la pantalla de verificación.', 'error')
        return redirect(url_for('auth.verificar'))
    return render_template('registro.html', errores={}, valores={})

@auth_bp.route('/verificar', methods=['GET', 'POST'])
def verificar():
    pendiente = session.get('registro_pendiente')
    if not pendiente:
        return redirect(url_for('auth.registro'))
    error = None
    if request.method == 'POST':
        digitos = [request.form.get(f'd{i}', '') for i in range(1, 7)]
        codigo_ingresado = ''.join(digitos)
        if codigo_ingresado == pendiente['codigo']:
            rol_usuario = Rol.query.filter_by(nombre='Usuario').first()
            nuevo = Usuario(
                nombre=pendiente['nombre'], email=pendiente['email'],
                telefono=pendiente['telefono'], ubicacion=pendiente['ubicacion'],
                contrasena=pendiente['contrasena'], id_rol=rol_usuario.id_rol,
                puedeCrearCampanias=False,
                foto_perfil=pendiente.get('foto_perfil'),
            )
            
            db.session.add(nuevo)
            db.session.commit()
            session.pop('registro_pendiente', None)
            flash('¡Cuenta creada con éxito! Ya podés iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        else:
            error = 'El código ingresado no es correcto. Revisá tu email.'
    return render_template('verificar.html', error=error)

@auth_bp.route('/reenviar-codigo-registro')
def reenviar_codigo_registro():
    pendiente = session.get('registro_pendiente')
    if not pendiente:
        return redirect(url_for('auth.registro'))
    nuevo_codigo = generar_codigo()
    session['registro_pendiente'] = {**pendiente, 'codigo': nuevo_codigo}
    session.modified = True
    try:
        enviar_email(pendiente['email'], 'Nuevo código de verificación',
            f'Tu nuevo código es: {nuevo_codigo}')
    except Exception as e:
        print(f'[MAIL ERROR] {e}')
    return redirect(url_for('auth.verificar'))

@auth_bp.route('/login', methods=['GET', 'POST'])
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
            flash('¡Bienvenido/a!', 'success')
            if usuario.es_admin():
                return redirect(url_for('admin.home'))
            return redirect(url_for('donaciones.home'))
    return render_template('login.html', error=error)

@auth_bp.route('/olvide-contrasena', methods=['GET', 'POST'])
def olvide_contrasena():
    error = None
    exito = None
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
                enviar_email(email, 'Código para restablecer contraseña',
                    f'Tu código es: {codigo}')
                session['email_recuperar'] = email
                return redirect(url_for('auth.verificar_recuperacion'))
            except Exception as e:
                print(f'[MAIL ERROR] {e}')
                error = 'Hubo un error al enviar el email. Intentá de nuevo.'
    return render_template('olvide_contrasena.html', error=error, exito=exito)

@auth_bp.route('/verificar-recuperacion', methods=['GET', 'POST'])
def verificar_recuperacion():
    email = session.get('email_recuperar')
    if not email:
        return redirect(url_for('auth.olvide_contrasena'))
    error = None
    if request.method == 'POST':
        digitos = [request.form.get(f'd{i}', '') for i in range(1, 7)]
        codigo_ingresado = ''.join(digitos)
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.codigoVerif == codigo_ingresado:
            session['recuperacion_verificada'] = True
            return redirect(url_for('auth.nueva_contrasena'))
        else:
            error = 'El código ingresado no es correcto.'
    return render_template('verificar_recuperacion.html', error=error)

@auth_bp.route('/nueva-contrasena', methods=['GET', 'POST'])
def nueva_contrasena():
    email = session.get('email_recuperar')
    verificada = session.get('recuperacion_verificada')
    if not email or not verificada:
        return redirect(url_for('auth.olvide_contrasena'))
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
            usuario.contrasena = generate_password_hash(contra)
            usuario.codigoVerif = None
            db.session.commit()
            session.pop('email_recuperar', None)
            session.pop('recuperacion_verificada', None)
            flash('Contraseña actualizada. Ya podés iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('nueva_contrasena.html', errores=errores)

def login_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if not session.get('usuario_id'):
            flash('Tenés que iniciar sesión primero.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorador

def requiere_admin(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return redirect(url_for('auth.login'))
        usuario = Usuario.query.get(usuario_id)
        if not usuario or not usuario.es_admin():
            flash('No tenés permisos para acceder a esa sección.', 'error')
            return redirect(url_for('donaciones.home'))
        return f(*args, **kwargs)
    return decorador

def requiere_campania(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return redirect(url_for('auth.login'))
        usuario = Usuario.query.get(usuario_id)
        if not usuario or not usuario.puedeCrearCampanias:
            flash('No tenés permisos para crear campañas.', 'error')
            return redirect(url_for('donaciones.home'))
        return f(*args, **kwargs)
    return decorador

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Cerraste sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))  