from flask import render_template, request, redirect, url_for, session, flash, current_app
from flask_mail import Message
from app.extensions import db, mail
from datetime import date
from app.extensions import db
from app.models import EstadoPeticion, Peticion, Usuario
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


@campana_bp.route('/admin/rechazar_peticion/<int:id>', methods=['POST'])
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
    return redirect(url_for('campana.gestionar_campana'))