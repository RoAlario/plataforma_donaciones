<<<<<<< HEAD
from flask import render_template, request, redirect, url_for, session, flash, current_app
from flask_mail import Message
from app.extensions import db, mail
=======
from flask import render_template, request, redirect, url_for, session, flash
from flask import current_app
from flask_mail import Message
>>>>>>> 109511b (US-03: Evaluar Peticiones, falta home del admin)
from datetime import date
from app.extensions import db, mail
from app.models import EstadoPeticion, Peticion, Usuario, Campana, Categoria, EstadoCampana
from app.auth.routes import login_requerido, requiere_admin
from flask import Blueprint


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

        cuitoCuil     = request.form['cuitoCuil']
        razonPeticion = request.form['razonPeticion']
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
        peticion_pendiente=peticion_pendiente
    )

@campana_bp.route('/admin/campana/gestionar_campana')
@requiere_admin
def gestionar_campana():
    peticiones = Peticion.query.filter_by(
        estado=EstadoPeticion.PENDIENTE
    ).order_by(Peticion.fechaEmitida.asc()).all()

    return render_template(
        'campana/gestionar_campana.html',
        peticiones=peticiones,
        usuario=Usuario.query.get(session['usuario_id'])
    )


@campana_bp.route('/admin/campana/aceptar_peticion/<int:id>', methods=['POST'])
@requiere_admin
def aceptar_peticion(id):
    peticion = Peticion.query.get_or_404(id)
    solicitante = Usuario.query.get(peticion.usuario_id)

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
    return redirect(url_for('campana.gestionar_campana'))


@campana_bp.route('/admin/campana/rechazar_peticion/<int:id>', methods=['POST'])
@requiere_admin
def rechazar_peticion(id):
    peticion  = Peticion.query.get_or_404(id)
    solicitante = Usuario.query.get(peticion.usuario_id)
    motivo    = request.form.get('motivo', '').strip()

    if len(motivo) < 10:
        flash('El motivo de rechazo debe tener al menos 10 caracteres.', 'error')
        return redirect(url_for('campana.gestionar_campana'))

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
<<<<<<< HEAD
    return redirect(url_for('campana.gestionar_campana'))
=======
    return redirect(url_for('campana.gestionar_campanas'))

@campana_bp.route('/campana/publicar', methods=['GET', 'POST'])
@login_requerido
def publicar_campana():
    usuario = Usuario.query.get(session['usuario_id'])

    # Verificar permiso
    if not usuario.puedeCrearCampanias:
        return render_template(
            'campana/publicar_campana.html',
            usuario=usuario,
            sin_permiso=True
        )

    categorias = Categoria.query.filter_by(fechaBajaCategoria=None).all()
    errores = {}

    if request.method == 'POST':
        titulo      = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        ubicacion   = request.form.get('ubicacion', '').strip()
        categoria_id = request.form.get('categoria_id', '')
        cantidad    = request.form.get('cantidad', '')
        fecha_fin   = request.form.get('fecha_fin', '')

        # Validaciones
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
>>>>>>> 83c9222 (US-04: Publicar Campaña Completa)
