from flask import render_template, request, redirect, url_for, session
from datetime import date
from app.extensions import db
from app.models import EstadoPeticion, Peticion, Usuario
from app.auth.routes import login_requerido
from flask import Blueprint

campana_bp = Blueprint('campana', __name__)

@campana_bp.route('/solicitar_campana', methods=['GET', 'POST'])
@login_requerido
def solicitar_campana():
    usuario = Usuario.query.get(session['usuario_id'])
    peticion_pendiente = Peticion.query.filter_by(
        usuario_id=usuario.codUsuario,
        estado=EstadoPeticion.PENDIENTE
    ).first()

    # Verifica si ya tiene una solicitud pendiente
    peticion_pendiente = Peticion.query.filter_by(
        usuario_id=usuario.codUsuario,
        estado=EstadoPeticion.PENDIENTE
    ).first()

    if request.method == 'POST':
<<<<<<< HEAD
=======
        # Si ya hay una solicitud pendiente, no se permite crear otra
>>>>>>> 8f0f6c1 (US-02: Solicitar Petición de campaña : Completa)
        if peticion_pendiente:
            return render_template(
                'solicitar_campana.html',
                usuario=usuario,
                peticion_pendiente=True,
            )
<<<<<<< HEAD
        
=======

>>>>>>> 8f0f6c1 (US-02: Solicitar Petición de campaña : Completa)
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
            'solicitar_campana.html',
            usuario=usuario,
<<<<<<< HEAD
            
            exito='¡Solicitud enviada! Un administrador evaluará tu pedido.',
            rederigir=True
=======
            exito='¡Solicitud enviada! Un administrador evaluará tu pedido.',
            rederigir=True
        )

    return render_template(
        'solicitar_campana.html',
        usuario=usuario,
        peticion_pendiente=peticion_pendiente
>>>>>>> 8f0f6c1 (US-02: Solicitar Petición de campaña : Completa)
        )