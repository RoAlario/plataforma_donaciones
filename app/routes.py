from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from flask_mail import Message
from app.extensions import db, mail
from datetime import date, datetime, timedelta
from app.models import EstadoPeticion, Peticion, Usuario, Categoria, Campana, EstadoCampana, OfertaCampana, Transaccion, EstadoTransaccion, Notificacion
from app.auth.routes import login_requerido, requiere_admin
import random

campana_bp = Blueprint('campana', __name__)
@campana_bp.route('/campana/solicitar_campana', methods=['GET', 'POST'])
@login_requerido
def solicitar_campana():
    usuario = Usuario.query.get(session['usuario_id'])
    peticion_pendiente = Peticion.query.filter_by(
        usuario_id=usuario.codUsuario,
        estado=EstadoPeticion.PENDIENTE
    ).first()

    if request.method == 'POST':

        # Si ya hay una solicitud pendiente, no se permite crear otra
        if peticion_pendiente:
            return render_template(
                'campana/solicitar_campana.html',
                usuario=usuario,
                peticion_pendiente=True,
            )

        cuitoCuil     = request.form.get('cuitoCuil', '').strip()
        razonPeticion = request.form.get('razonPeticion', '').strip()
        

        # Validación CUIT
        cuitoCuil_limpio = cuitoCuil.replace('-', '')
        if not cuitoCuil_limpio.isdigit() or len(cuitoCuil_limpio) != 11:
            return render_template('campana/solicitar_campana.html',
                                    usuario=usuario,
                                    error='El CUIT debe tener 11 dígitos (formato: XX-XXXXXXXX-X).')
        
        if not razonPeticion or len(razonPeticion) < 10:
            return render_template('campana/solicitar_campana.html', 
                                    usuario=usuario,
                                    error='La razón debe tener al menos 10 caracteres.')
        ultimo_nro = db.session.query(db.func.max(Peticion.nroPeticion)).scalar()
        nuevo_nro  = (ultimo_nro or 0) + 1

        nueva_peticion = Peticion(
            nroPeticion   = nuevo_nro,
            razonPeticion = razonPeticion,
            fechaEmitida  = date.today(),
            cuitoCuil     = cuitoCuil,
            estado        = EstadoPeticion.PENDIENTE,
            usuario_id    = usuario.codUsuario
        )
        db.session.add(nueva_peticion)
        db.session.commit()

        return render_template(
            'campana/solicitar_campana.html',
            usuario=usuario,
            exito='¡Solicitud enviada! Un administrador evaluará tu pedido.',
            redirigir=True   
        )

    return render_template(
    'campana/solicitar_campana.html',
    usuario=usuario,
    peticion_pendiente=peticion_pendiente,
    error=None
)

@campana_bp.route('/admin/campana/gestionar_campanas')
@requiere_admin
def gestionar_campanas():
    peticiones = Peticion.query.filter_by(
        estado=EstadoPeticion.PENDIENTE
    ).order_by(Peticion.fechaEmitida.asc()).all()

    return render_template(
        'campana/gestionar_campanas.html',
        peticiones=peticiones,
        usuario=Usuario.query.get(session['usuario_id'])
    )


@campana_bp.route('/admin/campana/aceptar_peticion/<int:id>', methods=['POST'])
@requiere_admin
def aceptar_peticion(id):
    peticion = Peticion.query.get_or_404(id)
    solicitante = Usuario.query.get(peticion.usuario_id)

    #Validación de estado de la petición  
    if peticion.estado != EstadoPeticion.PENDIENTE:
        flash('Esta petición ya fue procesada.', 'error')
        return redirect(url_for('campana.gestionar_campanas'))

    # Actualizar estado y habilitar campañas
    peticion.estado = EstadoPeticion.ACEPTADA
    solicitante.puedeCrearCampanias = True
    db.session.commit()

    # Enviar email de confirmación
    try:
        msg = Message(
            subject='¡Tu solicitud de campaña fue aprobada!',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[solicitante.email]
        )
        msg.body = (
            f'Hola {solicitante.nombre},\n\n'
            f'Tu solicitud de campaña fue aprobada. '
            f'Ya podés crear y gestionar campañas en la plataforma.\n\n'
            f'¡Gracias por ser parte de la comunidad!'
        )
        mail.send(msg)
    except Exception as e:
        print(f'[MAIL ERROR] {e}')

    flash('Solicitud aprobada correctamente.', 'success')
    return redirect(url_for('campana.gestionar_campanas'))


@campana_bp.route('/admin/campana/rechazar_peticion/<int:id>', methods=['POST'])
@requiere_admin
def rechazar_peticion(id):
    peticion  = Peticion.query.get_or_404(id)
    solicitante = Usuario.query.get(peticion.usuario_id)
    motivo    = request.form.get('motivo', '').strip()

    if len(motivo) < 10:
        flash('El motivo de rechazo debe tener al menos 10 caracteres.', 'error')
        return redirect(url_for('campana.gestionar_campanas'))

    # Actualizar estado
    peticion.estado = EstadoPeticion.RECHAZADA
    db.session.commit()

    # Enviar email con motivo
    try:
        msg = Message(
            subject='Tu solicitud de campaña fue rechazada',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[solicitante.email]
        )
        msg.body = (
            f'Hola {solicitante.nombre},\n\n'
            f'Lamentablemente tu solicitud de campaña fue rechazada.\n\n'
            f'Motivo: {motivo}\n\n'
            f'Si tenés dudas, podés contactarnos.'
        )
        mail.send(msg)
    except Exception as e:
        print(f'[MAIL ERROR] {e}')

    flash('Solicitud rechazada correctamente.', 'error')
    return redirect(url_for('campana.gestionar_campanas'))

@campana_bp.route('/campana/publicar', methods=['GET', 'POST'])
@login_requerido
def publicar_campana():
    usuario = Usuario.query.get(session['usuario_id'])

    if not usuario.puedeCrearCampanias:
        return render_template(
            'campana/publicar_campana.html',
            usuario=usuario,
            sin_permiso=True
        )

    categorias = Categoria.query.filter_by(fechaBajaCategoria=None).all()
    errores = {}

    if request.method == 'POST':
        titulo       = request.form.get('titulo', '').strip()
        descripcion  = request.form.get('descripcion', '').strip()
        ubicacion    = request.form.get('ubicacion', '').strip()
        categoria_id = request.form.get('categoria_id', '')
        cantidad     = request.form.get('cantidad', '')
        fecha_fin    = request.form.get('fecha_fin', '')

        if not titulo:
            errores['titulo'] = 'El nombre de la campaña es obligatorio.'
        if not ubicacion:
            errores['ubicacion'] = 'La ubicación es obligatoria.'
        if not categoria_id:
            errores['categoria'] = 'Debe seleccionar una categoría.'
        if not cantidad or not cantidad.isdigit() or int(cantidad) <= 0:
            errores['cantidad'] = 'La cantidad debe ser un número mayor a 0.'
        if not fecha_fin:
            errores['fecha_fin'] = 'La fecha de finalización es obligatoria.'
        else:
            from datetime import date
            fecha = date.fromisoformat(fecha_fin)
            if fecha <= date.today():
                errores['fecha_fin'] = 'La fecha de finalización debe ser posterior al día de hoy.'

        if errores:
            return render_template(
                'campana/publicar_campana.html',
                usuario=usuario,
                categorias=categorias,
                errores=errores,
                valores=request.form
            )

        foto_nombre = None
        foto = request.files.get('foto')
        if foto and foto.filename != '':
            from werkzeug.utils import secure_filename
            import os
            ext = foto.filename.rsplit('.', 1)[-1].lower()
            if ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
                foto_nombre = secure_filename(foto.filename)
                from flask import current_app
                carpeta = current_app.config['UPLOAD_FOLDER']
                os.makedirs(carpeta, exist_ok=True)
                foto.save(os.path.join(carpeta, foto_nombre))

        nueva_campana = Campana(
            titulo=titulo,
            descripcion=descripcion,
            ubicacion=ubicacion,
            fechaFinalizacion=datetime.strptime(fecha_fin, '%Y-%m-%d'),
            foto=foto_nombre,
            cantidadNecesaria=int(cantidad),
            estado=EstadoCampana.ACTIVA,
            codCategoria=categoria_id,
            codUsuario=usuario.codUsuario
        )
        db.session.add(nueva_campana)
        db.session.commit()

        flash('¡Campaña publicada exitosamente!', 'success')
        return redirect(url_for('donaciones.home'))

    return render_template(
        'campana/publicar_campana.html',
        usuario=usuario,
        categorias=categorias,
        errores={},
        valores={}
    )


def generar_codigo_transaccion():
    nums = [random.randint(100, 999) for _ in range(3)]
    return f'{nums[0]}-{nums[1]}-{nums[2]}'


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


# ─── DETALLE CAMPAÑA ──────────────────────────────────────
@campana_bp.route('/campana/<int:id>')
@login_requerido
def detalle_campana(id):
    campana = Campana.query.get_or_404(id)
    creador = Usuario.query.get(campana.codUsuario)
    return render_template('campana/detalle_campana.html',
        campana=campana, creador=creador)


# ─── OFRECER AYUDA ────────────────────────────────────────
@campana_bp.route('/campana/<int:id>/ofrecer', methods=['GET', 'POST'])
@login_requerido
def ofrecer_ayuda(id):
    campana = Campana.query.get_or_404(id)
    usuario = Usuario.query.get(session['usuario_id'])
    unidades_restantes = campana.unidades_restantes()

    if campana.codUsuario == usuario.codUsuario:
        flash('No podés ofrecer ayuda en tu propia campaña.', 'error')
        return redirect(url_for('campana.detalle_campana', id=id))

    if unidades_restantes <= 0:
        flash('Esta campaña ya completó su meta.', 'error')
        return redirect(url_for('campana.detalle_campana', id=id))

    ya_ofrecio = OfertaCampana.query.filter_by(
        campana_id=id, usuario_id=usuario.codUsuario
    ).first()

    errores = {}
    if request.method == 'POST':
        if ya_ofrecio:
            flash('Ya ofreciste ayuda en esta campaña.', 'error')
            return redirect(url_for('campana.detalle_campana', id=id))

        cantidad = request.form.get('cantidad', '')
        if not cantidad or not cantidad.isdigit() or int(cantidad) <= 0:
            errores['cantidad'] = 'Ingresá una cantidad válida.'
        elif int(cantidad) > unidades_restantes:
            errores['cantidad'] = f'Solo quedan {unidades_restantes} unidades por cubrir.'

        if not errores:
            cant = int(cantidad)
            nueva_oferta = OfertaCampana(
                cantidad_ofrecida=cant,
                campana_id=id,
                usuario_id=usuario.codUsuario
            )
            db.session.add(nueva_oferta)

            campana.cantidadDonada = (campana.cantidadDonada or 0) + cant

            codigo = generar_codigo_transaccion()
            nueva_transaccion = Transaccion(
                codigoVerif=codigo,
                fechaExpiracion=datetime.utcnow() + timedelta(hours=24),
                codPublicacion=None,
                codDonante=campana.codUsuario,
                codBeneficiario=usuario.codUsuario,
                campana_id=campana.idCampana
            )
            db.session.add(nueva_transaccion)
            db.session.flush()

            nueva_oferta.transaccion = nueva_transaccion
            db.session.commit()

            # Notificación al creador
            notif = Notificacion(
                mensaje=f'{usuario.nombre} ofreció {cant} unidades para tu campaña "{campana.titulo}"',
                usuario_id=campana.codUsuario,
                enlace=url_for('campana.coordinacion_campana', id=nueva_transaccion.idTransaccion)
            )
            db.session.add(notif)
            db.session.commit()

            # Email al creador
            try:
                msg = Message(
                    subject=f'Nueva oferta en tu campaña "{campana.titulo}"',
                    sender=current_app.config['MAIL_USERNAME'],
                    recipients=[campana.usuario.email]
                )
                msg.body = (
                    f'Hola {campana.usuario.nombre},\n\n'
                    f'{usuario.nombre} ofreció {cant} unidades para tu campaña "{campana.titulo}".\n\n'
                    f'Ingresá a la plataforma para coordinar la entrega.'
                )
                mail.send(msg)
            except Exception as e:
                print(f'[MAIL ERROR] {e}')

            flash('¡Oferta enviada! Empezá a coordinar la entrega.', 'success')
            return redirect(url_for('campana.coordinacion_campana', id=nueva_transaccion.idTransaccion))

    return render_template('campana/ofrecer_ayuda.html',
        campana=campana, unidades_restantes=unidades_restantes,
        ya_ofrecio=ya_ofrecio, errores=errores)


# ─── MIS OFERTAS DE CAMPAÑA ───────────────────────────────
@campana_bp.route('/campana/mis-ofertas')
@login_requerido
def mis_ofertas_campana():
    usuario = Usuario.query.get(session['usuario_id'])
    ofertas = OfertaCampana.query.filter_by(
        usuario_id=usuario.codUsuario
    ).order_by(OfertaCampana.fecha_oferta.desc()).all()
    return render_template('campana/mis_ofertas.html',
        usuario=usuario, ofertas=ofertas)


# ─── OFERTAS RECIBIDAS (creador) ──────────────────────────
@campana_bp.route('/campana/<int:id>/ofertas')
@login_requerido
def ofertas_recibidas_campana(id):
    campana = Campana.query.get_or_404(id)
    usuario = Usuario.query.get(session['usuario_id'])

    if campana.codUsuario != usuario.codUsuario:
        flash('No tenés permisos para ver esto.', 'error')
        return redirect(url_for('donaciones.home'))

    ofertas = OfertaCampana.query.filter_by(
        campana_id=id
    ).order_by(OfertaCampana.fecha_oferta.desc()).all()

    return render_template('campana/ofertas_recibidas.html',
        usuario=usuario, campana=campana, ofertas=ofertas)


# ─── COORDINACIÓN CAMPAÑA ─────────────────────────────────
@campana_bp.route('/campana/coordinacion/<int:id>')
@login_requerido
def coordinacion_campana(id):
    transaccion = Transaccion.query.get_or_404(id)
    usuario = Usuario.query.get(session['usuario_id'])

    if transaccion.codDonante != usuario.codUsuario and transaccion.codBeneficiario != usuario.codUsuario:
        flash('No tenés permisos para ver esta página.', 'error')
        return redirect(url_for('donaciones.home'))

    es_donante = transaccion.codDonante == usuario.codUsuario
    publicacion = transaccion.campana
    oferta = OfertaCampana.query.filter_by(transaccion_id=transaccion.idTransaccion).first()

    return render_template('campana/coordinacion_campana.html',
        transaccion=transaccion, usuario=usuario, es_donante=es_donante,
        publicacion=publicacion, donante=transaccion.donante,
        beneficiario=transaccion.beneficiario, oferta=oferta,
        tiempo=tiempo_transcurrido(publicacion.fechaInicio))


# ─── VERIFICAR CÓDIGO CAMPAÑA ────────────────────────────
@campana_bp.route('/campana/coordinacion/<int:id>/verificar', methods=['POST'])
@login_requerido
def verificar_codigo_campana(id):
    usuario_id = session.get('usuario_id')
    transaccion = Transaccion.query.get_or_404(id)

    if transaccion.codBeneficiario != usuario_id:
        flash('No tenés permisos para esta acción.', 'error')
        return redirect(url_for('donaciones.home'))

    codigo_ingresado = request.form.get('codigo', '').strip()
    if datetime.utcnow() > transaccion.fechaExpiracion:
        _expirar_transaccion_campana(transaccion)
        flash('El código expiró. La oferta fue cancelada.', 'error')
        return redirect(url_for('donaciones.home'))

    if codigo_ingresado == transaccion.codigoVerif:
        transaccion.estado = EstadoTransaccion.VERIFICADA
        db.session.commit()
        return redirect(url_for('campana.coordinacion_campana', id=id))
    else:
        flash('Código incorrecto. Intentá de nuevo.', 'error')
        return redirect(url_for('campana.coordinacion_campana', id=id))


# ─── CONFIRMAR FECHA CAMPAÑA ──────────────────────────────
@campana_bp.route('/campana/coordinacion/<int:id>/fecha', methods=['POST'])
@login_requerido
def confirmar_fecha_campana(id):
    usuario_id = session.get('usuario_id')
    transaccion = Transaccion.query.get_or_404(id)

    if transaccion.codDonante != usuario_id and transaccion.codBeneficiario != usuario_id:
        flash('No tenés permisos para esta acción.', 'error')
        return redirect(url_for('donaciones.home'))

    fecha_str = request.form.get('fecha_entrega', '')
    if not fecha_str:
        flash('Debés seleccionar una fecha de entrega.', 'error')
        return redirect(url_for('campana.coordinacion_campana', id=id))

    transaccion.fechaEntrega = datetime.strptime(fecha_str, '%Y-%m-%d')
    db.session.commit()
    flash('¡Fecha de entrega confirmada!', 'success')
    return redirect(url_for('campana.coordinacion_campana', id=id))


# ─── GENERAR CÓDIGO ENTREGA CAMPAÑA ──────────────────────
@campana_bp.route('/campana/coordinacion/<int:id>/generar-codigo-entrega', methods=['POST'])
@login_requerido
def generar_codigo_entrega_campana(id):
    usuario_id = session.get('usuario_id')
    transaccion = Transaccion.query.get_or_404(id)

    if transaccion.codBeneficiario != usuario_id:
        flash('No tenés permisos para esta acción.', 'error')
        return redirect(url_for('donaciones.home'))

    codigo = generar_codigo_transaccion()
    transaccion.codigoEntrega = codigo
    db.session.commit()

    try:
        msg = Message(
            subject='Código de verificación de entrega',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[transaccion.beneficiario.email]
        )
        msg.body = (
            f'Hola {transaccion.beneficiario.nombre},\n\n'
            f'Tu código de verificación de entrega es: {codigo}\n\n'
            f'Entregáselo al creador de la campaña para confirmar la recepción.'
        )
        mail.send(msg)
    except Exception as e:
        print(f'[MAIL ERROR] {e}')

    flash('Código de entrega generado y enviado a tu email.', 'success')
    return redirect(url_for('campana.coordinacion_campana', id=id))


# ─── VERIFICAR ENTREGA CAMPAÑA ────────────────────────────
@campana_bp.route('/campana/coordinacion/<int:id>/verificar-entrega', methods=['POST'])
@login_requerido
def verificar_entrega_campana(id):
    usuario_id = session.get('usuario_id')
    transaccion = Transaccion.query.get_or_404(id)

    if transaccion.codDonante != usuario_id:
        flash('No tenés permisos para esta acción.', 'error')
        return redirect(url_for('donaciones.home'))

    codigo_ingresado = request.form.get('codigo_entrega', '').strip()
    if codigo_ingresado != transaccion.codigoEntrega:
        flash('Código de entrega incorrecto.', 'error')
        return redirect(url_for('campana.coordinacion_campana', id=id))

    publicacion = transaccion.campana
    transaccion.estado = EstadoTransaccion.FINALIZADA

    donante = transaccion.donante
    beneficiario = transaccion.beneficiario
    donante.cantDonaciones = (donante.cantDonaciones or 0) + 1
    db.session.commit()

    # Notificaciones
    notif_donante = Notificacion(
        mensaje=f'¡Tu oferta para "{publicacion.titulo}" fue entregada con éxito!',
        usuario_id=donante.codUsuario,
        enlace=url_for('campana.coordinacion_campana', id=id)
    )
    notif_beneficiario = Notificacion(
        mensaje=f'¡Recibiste la donación para "{publicacion.titulo}" con éxito!',
        usuario_id=beneficiario.codUsuario,
        enlace=url_for('campana.coordinacion_campana', id=id)
    )
    db.session.add(notif_donante)
    db.session.add(notif_beneficiario)
    db.session.commit()

    # Emails
    try:
        for dest in [donante, beneficiario]:
            msg = Message(
                subject=f'Oferta para "{publicacion.titulo}" finalizada',
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[dest.email]
            )
            msg.body = (
                f'Hola {dest.nombre},\n\n'
                f'La oferta para la campaña "{publicacion.titulo}" fue completada exitosamente.\n'
                f'¡Gracias por ser parte de la comunidad!'
            )
            mail.send(msg)
    except Exception as e:
        print(f'[MAIL ERROR] {e}')

    flash('¡Oferta finalizada con éxito!', 'success')
    return redirect(url_for('campana.coordinacion_campana', id=id))


def _expirar_transaccion_campana(transaccion):
    transaccion.estado = EstadoTransaccion.EXPIRADA
    campana = transaccion.campana
    if campana:
        oferta = OfertaCampana.query.filter_by(transaccion_id=transaccion.idTransaccion).first()
        if oferta:
            campana.cantidadDonada = max(0, (campana.cantidadDonada or 0) - oferta.cantidad_ofrecida)
    db.session.commit()
    try:
        for destinatario in [transaccion.donante, transaccion.beneficiario]:
            msg = Message(
                subject='Oferta de campaña expirada',
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[destinatario.email]
            )
            msg.body = (
                f'Hola {destinatario.nombre},\n\n'
                f'La oferta para la campaña "{campana.titulo}" expiró '
                f'porque no se verificó el código en 24 horas.\n'
            )
            mail.send(msg)
    except Exception as e:
        print(f'[MAIL ERROR] {e}')
    db.session.commit()
    