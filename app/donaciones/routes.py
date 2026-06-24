from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from flask_mail import Message
from flask import jsonify
from app.extensions import db, mail
from app.models import (Publicacion, Categoria, Usuario, EstadoPublicacion, Direccion,
                         SolicitudDonacion, EstadoSolicitudDonacion, Notificacion, Transaccion, EstadoTransaccion)
from app.auth.routes import login_requerido
from datetime import datetime, timedelta
import random

donaciones_bp = Blueprint('donaciones', __name__)

def tiempo_transcurrido(fecha):
    diff = datetime.utcnow() - fecha
    minutos = diff.seconds // 60
    horas = diff.seconds // 3600
    dias = diff.days
    if dias > 0:
        return f'Hace {dias} día{"s" if dias > 1 else ""}'
    elif horas > 0:
        return f'Hace {horas} hora{"s" if horas > 1 else ""}'
    elif minutos > 0:
        return f'Hace {minutos} minuto{"s" if minutos > 1 else ""}'
    return 'Hace un momento'

@donaciones_bp.route('/home')
def home():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(usuario_id)
    categorias = Categoria.query.filter_by(fechaBajaCategoria=None).all()

    busqueda = request.args.get('q', '').strip()
    categoria_id = request.args.get('categoria', '')

    query = Publicacion.query.filter_by(fechaFinPublicacion=None)

    if busqueda:
        query = query.filter(
            Publicacion.titulo.ilike(f'%{busqueda}%') |
            Publicacion.descripcionPublicacion.ilike(f'%{busqueda}%')
        )
    if categoria_id:
        query = query.filter_by(codCategoria=categoria_id)

    publicaciones = query.order_by(
        Publicacion.fechaEmisionPublicacion.desc()
    ).all()

    for p in publicaciones:
        p.tiempo = tiempo_transcurrido(p.fechaEmisionPublicacion)

    return render_template('donaciones/home.html',
        usuario=usuario,
        categorias=categorias,
        publicaciones=publicaciones,
        busqueda=busqueda,
        categoria_seleccionada=categoria_id
    )
    

@donaciones_bp.route('/publicar', methods=['GET', 'POST'])
def publicar():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(usuario_id)
    categorias = Categoria.query.filter_by(fechaBajaCategoria=None).all()

    # Verificar límite de 5 publicaciones activas
    publicaciones_activas = Publicacion.query.join(EstadoPublicacion).filter(
        Publicacion.codUsuario == usuario_id,
        EstadoPublicacion.nombreEP.in_(['Disponible', 'En progreso'])
    ).count()

    if publicaciones_activas >= 5:
        flash('Acción bloqueada. Ha alcanzado el límite de publicaciones activas o posee entregas previas sin verificar.', 'error')
        return redirect(url_for('donaciones.home'))

    errores = {}

    if request.method == 'POST':
        titulo        = request.form.get('titulo', '').strip()
        descripcion   = request.form.get('descripcion', '').strip()
        direccion     = request.form.get('direccion', '').strip()
        categoria_id  = request.form.get('categoria_id', '')
        fecha_venc    = request.form.get('fecha_vencimiento', '')
        conservacion  = request.form.get('conservacion', '')

        # Validaciones
        if not titulo:
            errores['titulo'] = 'El nombre del producto es obligatorio.'
        if not direccion:
            errores['direccion'] = 'Debe ingresar una ubicación válida.'
        if not categoria_id:
            errores['categoria'] = 'Debe seleccionar una categoría.'

        # Validar fecha vencimiento para Alimentos y Medicamentos
        categoria = Categoria.query.get(categoria_id) if categoria_id else None
        if categoria and categoria.nombreCategoria in ['Alimento', 'Medicamentos']:
            if not fecha_venc:
                errores['fecha_vencimiento'] = 'La fecha de vencimiento es obligatoria para esta categoría.'
            else:
                from datetime import date
                fecha = date.fromisoformat(fecha_venc)
                if fecha <= date.today():
                    errores['fecha_vencimiento'] = 'El producto está vencido. No puede publicarse.'

        # Validar conservación para Ropa, Muebles, Electrónico
        if categoria and categoria.nombreCategoria in ['Ropa', 'Muebles', 'Electrónico']:
            if not conservacion:
                errores['conservacion'] = 'El estado de conservación es obligatorio.'
            elif conservacion == 'Inservible / Roto':
                errores['conservacion'] = 'No se pueden publicar productos en estado Inservible / Roto.'

        if errores:
            return render_template('donaciones/publicar.html',
                errores=errores, categorias=categorias,
                valores=request.form)

        # Guardar dirección
        nueva_dir = Direccion(nombreCalle=direccion)
        db.session.add(nueva_dir)
        db.session.flush()

        # Foto
        foto_nombre = None
        foto = request.files.get('foto')
        if foto and foto.filename != '':
            from werkzeug.utils import secure_filename
            from flask import current_app
            import os
            ext = foto.filename.rsplit('.', 1)[-1].lower()
            if ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
                foto_nombre = secure_filename(foto.filename)
                carpeta = current_app.config['UPLOAD_FOLDER']
                os.makedirs(carpeta, exist_ok=True)
                foto.save(os.path.join(carpeta, foto_nombre))

        # Estado "Disponible"
        estado = EstadoPublicacion.query.filter_by(nombreEP='Disponible').first()

        # Guardar publicación
        nueva_pub = Publicacion(
            titulo=titulo,
            descripcionPublicacion=descripcion,
            ubicacion=direccion,
            fotos=foto_nombre,
            codCategoria=categoria_id,
            codUsuario=usuario_id,
            codEstadoPublicacion=estado.codEstadoPublicacion,
            nroDireccion=nueva_dir.nroDireccion,
            fechaVencimiento=datetime.strptime(fecha_venc, '%Y-%m-%d') if fecha_venc else None,
            categoriaOtro=request.form.get('categoriaOtro', ''),
            genero=request.form.get('genero', ''),
            talle=request.form.get('talle', ''),
            color=request.form.get('color', ''),
            material=request.form.get('material', ''),
           )
        
        db.session.add(nueva_pub)
        db.session.commit()

        flash('¡Se publicó la donación exitosamente!', 'success')
        return redirect(url_for('donaciones.home'))

    return render_template('donaciones/publicar.html',
        errores={}, categorias=categorias, valores={})
    
@donaciones_bp.route('/donacion/<int:id>')
def detalle(id):
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('auth.login'))

    publicacion = Publicacion.query.get_or_404(id)
    donante = Usuario.query.get(publicacion.codUsuario)
    usuario = Usuario.query.get(usuario_id)

    print(f"--- DEBUG DETALLE ---")
    print(f"Publicacion ID: {publicacion.nroPublicacion}")
    print(f"codUsuario en publicacion: {publicacion.codUsuario}")
    print(f"Donante ID: {donante.codUsuario if donante else 'None'}")
    print(f"Donante nombre: {donante.nombre if donante else 'None'}")
    print(f"Donante email: {donante.email if donante else 'None'}")
    print(f"Usuario logueado ID: {session.get('usuario_id')}")
    print(f"----------------------")
    
    donaciones_realizadas = Publicacion.query.filter_by(codUsuario=donante.codUsuario).count()

    return render_template('donaciones/detalle.html',
        p=publicacion,
        donante=donante,
        usuario=usuario,
        donaciones_realizadas=donaciones_realizadas,
        tiempo=tiempo_transcurrido(publicacion.fechaEmisionPublicacion)
    )

# --- Solicitar donación ---
@donaciones_bp.route('/donacion/<int:id>/solicitar', methods=['GET', 'POST'])
@login_requerido
def solicitar_donacion(id):
    publicacion = Publicacion.query.get_or_404(id)
    usuario = Usuario.query.get(session['usuario_id'])

    # Validaciones
    if publicacion.codUsuario == usuario.codUsuario:
        flash('No podés solicitar tu propia donación.', 'error')
        return redirect(url_for('donaciones.detalle', id=id))

    # Verificar límite de 2 solicitudes pendientes
    pendientes = SolicitudDonacion.query.filter_by(
        usuario_id=usuario.codUsuario,
        estado=EstadoSolicitudDonacion.PENDIENTE
    ).count()
    if pendientes >= 2:
        flash('Alcanzaste el límite de 2 solicitudes pendientes.', 'error')
        return redirect(url_for('donaciones.detalle', id=id))

    # Verificar si ya solicitó esta donación
    ya_solicito = SolicitudDonacion.query.filter_by(
        publicacion_id=id,
        usuario_id=usuario.codUsuario
    ).first()
    if ya_solicito:
        ya_solicito_msg = True
    else:
        ya_solicito_msg = False

    errores = {}
    if request.method == 'POST':
        if ya_solicito_msg:
            flash('Ya solicitaste esta donación anteriormente.', 'error')
            return redirect(url_for('donaciones.detalle', id=id))

        razon = request.form.get('razon', '').strip()
        if not razon or len(razon) < 10:
            errores['razon'] = 'La razón debe tener al menos 10 caracteres.'

        if not errores:
            nueva_solicitud = SolicitudDonacion(
                razon=razon,
                publicacion_id=id,
                usuario_id=usuario.codUsuario,
                estado=EstadoSolicitudDonacion.PENDIENTE
            )
            db.session.add(nueva_solicitud)

            # Cambiar estado de la donación a "A evaluar"
            if publicacion.codEstadoPublicacion and publicacion.estado.nombreEP == 'Disponible':
                estado_evaluar = EstadoPublicacion.query.filter_by(nombreEP='A evaluar').first()
                if estado_evaluar:
                    publicacion.codEstadoPublicacion = estado_evaluar.codEstadoPublicacion

            # Notificación al donante
            donante = Usuario.query.get(publicacion.codUsuario)
            notif = Notificacion(
                mensaje=f'{usuario.nombre} solicitó tu donación "{publicacion.titulo}"',
                usuario_id=donante.codUsuario,
                enlace=url_for('donaciones.detalle', id=publicacion.nroPublicacion)
            )
            db.session.add(notif)
            db.session.commit()

            # Email al donante
            try:
                msg = Message(
                    subject=f'Nueva solicitud para "{publicacion.titulo}"',
                    sender=current_app.config['MAIL_USERNAME'],
                    recipients=[donante.email]
                )
                msg.body = (
                    f'Hola {donante.nombre},\n\n'
                    f'{usuario.nombre} solicitó tu donación "{publicacion.titulo}".\n'
                    f'Razón: {razon}\n\n'
                    f'Ingresá a la plataforma para aceptar o rechazar.'
                )
                mail.send(msg)
            except Exception as e:
                print(f'[MAIL ERROR] {e}')

            flash('Solicitud enviada correctamente.', 'success')
            return redirect(url_for('donaciones.detalle', id=id))

    return render_template('donaciones/solicitar.html',
                           publicacion=publicacion,
                           usuario=usuario,
                           errores=errores,
                           ya_solicito=ya_solicito_msg)


# --- Solicitudes recibidas (donante) ---
@donaciones_bp.route('/mis-solicitudes-recibidas')
@login_requerido
def solicitudes_recibidas():
    return redirect(url_for('donaciones.mis_donaciones'))


# --- Aceptar solicitud ---
@donaciones_bp.route('/solicitud/<int:id>/aceptar', methods=['POST'])
@login_requerido
def aceptar_solicitud(id):
    solicitud = SolicitudDonacion.query.get_or_404(id)
    publicacion = Publicacion.query.get(solicitud.publicacion_id)
    usuario = Usuario.query.get(session['usuario_id'])

    # Solo el donante puede aceptar
    if publicacion.codUsuario != usuario.codUsuario:
        flash('No tenés permisos para esta acción.', 'error')
        return redirect(url_for('donaciones.home'))

    solicitud.estado = EstadoSolicitudDonacion.ACEPTADA
    # Cambiar estado de donación a "En progreso"
    estado_progreso = EstadoPublicacion.query.filter_by(nombreEP='En progreso').first()
    if estado_progreso:
        publicacion.codEstadoPublicacion = estado_progreso.codEstadoPublicacion

    # Notificación al solicitante (aceptada)
    solicitante = Usuario.query.get(solicitud.usuario_id)
    notif = Notificacion(
        mensaje=f'Tu solicitud para "{publicacion.titulo}" fue aceptada',
        usuario_id=solicitante.codUsuario,
        enlace=url_for('donaciones.detalle', id=publicacion.nroPublicacion)
    )
    db.session.add(notif)

    # Rechazar automáticamente las otras solicitudes pendientes
    otras_pendientes = SolicitudDonacion.query.filter(
        SolicitudDonacion.publicacion_id == publicacion.nroPublicacion,
        SolicitudDonacion.id != solicitud.id,
        SolicitudDonacion.estado == EstadoSolicitudDonacion.PENDIENTE
    ).all()

    for otra in otras_pendientes:
        otra.estado = EstadoSolicitudDonacion.RECHAZADA
        otro_solicitante = Usuario.query.get(otra.usuario_id)
        notif_rechazada = Notificacion(
            mensaje=f'Tu solicitud para "{publicacion.titulo}" fue rechazada automáticamente porque el donante aceptó otra solicitud.',
            usuario_id=otro_solicitante.codUsuario,
            enlace=url_for('donaciones.detalle', id=publicacion.nroPublicacion)
        )
        db.session.add(notif_rechazada)

    db.session.commit()

    # Email
    try:
        msg = Message(
            subject=f'Tu solicitud de "{publicacion.titulo}" fue aceptada',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[solicitante.email]
        )
        msg.body = (
            f'Hola {solicitante.nombre},\n\n'
            f'Tu solicitud para la donación "{publicacion.titulo}" fue aceptada.\n'
            f'Contactá al donante para coordinar la entrega.'
        )
        mail.send(msg)
    except Exception as e:
        print(f'[MAIL ERROR] {e}')

    flash('Solicitud aceptada. La donación pasó a "En progreso".', 'success')
    return redirect(url_for('donaciones.solicitudes_recibidas'))

# --- Rechazar solicitud ---
@donaciones_bp.route('/solicitud/<int:id>/rechazar', methods=['POST'])
@login_requerido
def rechazar_solicitud(id):
    solicitud = SolicitudDonacion.query.get_or_404(id)
    publicacion = Publicacion.query.get(solicitud.publicacion_id)
    usuario = Usuario.query.get(session['usuario_id'])

    if publicacion.codUsuario != usuario.codUsuario:
        flash('No tenés permisos para esta acción.', 'error')
        return redirect(url_for('donaciones.home'))

    motivo = request.form.get('motivo', '').strip()
    if len(motivo) < 10:
        flash('El motivo debe tener al menos 10 caracteres.', 'error')
        return redirect(url_for('donaciones.solicitudes_recibidas'))

    solicitud.estado = EstadoSolicitudDonacion.RECHAZADA

    # Notificación al solicitante
    solicitante = Usuario.query.get(solicitud.usuario_id)
    notif = Notificacion(
        mensaje=f'Tu solicitud para "{publicacion.titulo}" fue rechazada. Motivo: {motivo}',
        usuario_id=solicitante.codUsuario,
        enlace=url_for('donaciones.detalle', id=publicacion.nroPublicacion)
    )
    db.session.add(notif)
    db.session.commit()

    # Email
    try:
        msg = Message(
            subject=f'Tu solicitud de "{publicacion.titulo}" fue rechazada',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[solicitante.email]
        )
        msg.body = (
            f'Hola {solicitante.nombre},\n\n'
            f'Tu solicitud para la donación "{publicacion.titulo}" fue rechazada.\n'
            f'Motivo: {motivo}'
        )
        mail.send(msg)
    except Exception as e:
        print(f'[MAIL ERROR] {e}')

    flash('Solicitud rechazada.', 'error')
    return redirect(url_for('donaciones.solicitudes_recibidas'))


# --- Notificaciones ---
@donaciones_bp.route('/notificaciones')
@login_requerido
def notificaciones():
    usuario = Usuario.query.get(session['usuario_id'])
    Notificacion.query.filter_by(
        usuario_id=usuario.codUsuario, leida=False
    ).update({'leida': True})
    db.session.commit()
    return redirect(url_for('donaciones.solicitudes_recibidas'))


@donaciones_bp.route('/api/notificaciones-no-leidas')
@login_requerido
def notificaciones_no_leidas():
    usuario = Usuario.query.get(session['usuario_id'])
    count = Notificacion.query.filter_by(
        usuario_id=usuario.codUsuario, leida=False
    ).count()
    return {'count': count}

# --- API notificaciones ---
@donaciones_bp.route('/api/notificaciones')
@login_requerido
def api_notificaciones():
    usuario = Usuario.query.get(session['usuario_id'])
    notifs = Notificacion.query.filter_by(usuario_id=usuario.codUsuario)\
        .order_by(Notificacion.fecha.desc()).limit(10).all()
    return jsonify([{
        'id': n.id,
        'mensaje': n.mensaje,
        'fecha': n.fecha.strftime('%d/%m/%Y %H:%M'),
        'leida': n.leida,
        'enlace': n.enlace
    } for n in notifs])


@donaciones_bp.route('/api/notificaciones/marcar-leidas', methods=['POST'])
@login_requerido
def marcar_notificaciones_leidas():
    usuario = Usuario.query.get(session['usuario_id'])
    Notificacion.query.filter_by(usuario_id=usuario.codUsuario, leida=False)\
        .update({'leida': True})
    db.session.commit()
    return jsonify({'ok': True})

# --- Mis donaciones (publicaciones propias) ---
@donaciones_bp.route('/mis-donaciones')
@login_requerido
def mis_donaciones():
    usuario = Usuario.query.get(session['usuario_id'])
    publicaciones = Publicacion.query.filter_by(
        codUsuario=usuario.codUsuario,
        fechaFinPublicacion=None
    ).order_by(Publicacion.fechaEmisionPublicacion.desc()).all()

    for p in publicaciones:
        p.tiempo = tiempo_transcurrido(p.fechaEmisionPublicacion)
        p.cant_solicitudes_pendientes = SolicitudDonacion.query.filter_by(
            publicacion_id=p.nroPublicacion,
            estado=EstadoSolicitudDonacion.PENDIENTE
        ).count()

    return render_template('donaciones/mis_donaciones.html',
                           usuario=usuario,
                           publicaciones=publicaciones)
    
# --- Ver solicitudes de una donación propia ---
@donaciones_bp.route('/mis-donaciones/<int:id>/solicitudes')
@login_requerido
def mis_donaciones_solicitudes(id):
    usuario = Usuario.query.get(session['usuario_id'])
    publicacion = Publicacion.query.get_or_404(id)

    if publicacion.codUsuario != usuario.codUsuario:
        flash('No tenés permisos para ver esto.', 'error')
        return redirect(url_for('donaciones.mis_donaciones'))

    solicitudes = SolicitudDonacion.query.filter_by(
        publicacion_id=id
    ).order_by(SolicitudDonacion.fechaSolicitud.desc()).all()

    return render_template('donaciones/mis_donaciones_solicitudes.html',
                           usuario=usuario,
                           publicacion=publicacion,
                           solicitudes=solicitudes)
  
  # --- Mis solicitudes enviadas ---
@donaciones_bp.route('/mis-solicitudes')
@login_requerido
def mis_solicitudes():
    usuario = Usuario.query.get(session['usuario_id'])
    solicitudes = SolicitudDonacion.query.filter_by(
        usuario_id=usuario.codUsuario
    ).order_by(SolicitudDonacion.fechaSolicitud.desc()).all()

    return render_template('donaciones/mis_solicitudes.html',
                           usuario=usuario,
                           solicitudes=solicitudes)

def generar_codigo_transaccion():
    nums = [random.randint(100, 999) for _ in range(3)]
    return f'{nums[0]}-{nums[1]}-{nums[2]}'

@donaciones_bp.route('/coordinacion/<int:id>')
def coordinacion(id):
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('auth.login'))
    transaccion = Transaccion.query.get_or_404(id)
    usuario = Usuario.query.get(usuario_id)
    es_donante = transaccion.codDonante == usuario_id
    return render_template('donaciones/coordinacion.html',
        transaccion=transaccion, usuario=usuario, es_donante=es_donante,
        publicacion=transaccion.publicacion, donante=transaccion.donante,
        beneficiario=transaccion.beneficiario,
        tiempo=tiempo_transcurrido(transaccion.publicacion.fechaEmisionPublicacion)
    )

@donaciones_bp.route('/coordinacion/<int:id>/verificar', methods=['POST'])
def verificar_codigo(id):
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('auth.login'))
    transaccion = Transaccion.query.get_or_404(id)
    codigo_ingresado = request.form.get('codigo', '').strip()
    if datetime.utcnow() > transaccion.fechaExpiracion:
        _expirar_transaccion(transaccion)
        flash('El código expiró. La donación volvió a estar disponible.', 'error')
        return redirect(url_for('donaciones.home'))
    if codigo_ingresado == transaccion.codigoVerif:
        transaccion.estado = EstadoTransaccion.VERIFICADA
        db.session.commit()
        return redirect(url_for('donaciones.coordinacion', id=id))
    else:
        flash('Código incorrecto. Intentá de nuevo.', 'error')
        return redirect(url_for('donaciones.coordinacion', id=id))

@donaciones_bp.route('/coordinacion/<int:id>/fecha', methods=['POST'])
def confirmar_fecha(id):
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('auth.login'))
    transaccion = Transaccion.query.get_or_404(id)
    fecha_str = request.form.get('fecha_entrega', '')
    if not fecha_str:
        flash('Debés seleccionar una fecha de entrega.', 'error')
        return redirect(url_for('donaciones.coordinacion', id=id))
    transaccion.fechaEntrega = datetime.strptime(fecha_str, '%Y-%m-%d')
    db.session.commit()
    flash('¡Fecha de entrega confirmada!', 'success')
    return redirect(url_for('donaciones.coordinacion', id=id))

def _expirar_transaccion(transaccion):
    transaccion.estado = EstadoTransaccion.EXPIRADA
    publicacion = transaccion.publicacion
    estado_disponible = EstadoPublicacion.query.filter_by(nombreEP='Disponible').first()
    publicacion.codEstadoPublicacion = estado_disponible.codEstadoPublicacion
    db.session.commit()
    try:
        for destinatario in [transaccion.donante, transaccion.beneficiario]:
            msg = Message(
                subject='Solicitud de donación expirada',
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[destinatario.email]
            )
            msg.body = (
                f'Hola {destinatario.nombre},\n\n'
                f'La solicitud de donación "{publicacion.titulo}" expiró '
                f'porque no se verificó el código en 24 horas.\n'
                f'La donación volvió a estar disponible para otros usuarios.'
            )
            mail.send(msg)
    except Exception as e:
        print(f'[MAIL ERROR] {e}')

