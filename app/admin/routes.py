from flask import Blueprint, render_template, session, redirect, url_for
from app.models import Publicacion, Usuario, EstadoPublicacion, Peticion, Rol, EstadoPeticion
from app.extensions import db
from app.auth.routes import requiere_admin
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/home')
@requiere_admin
def home():
    usuario = Usuario.query.get(session['usuario_id'])
    hoy = datetime.utcnow()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0)

    # Stat cards
    total_donaciones = Publicacion.query.filter(
        Publicacion.fechaEmisionPublicacion >= inicio_mes
    ).count()

    usuarios_nuevos = Usuario.query.filter(
        Usuario.fechaAltaUsuario >= inicio_mes
    ).count()

    from app.models import Peticion
    try:
        solicitudes_activas = Peticion.query.count()
    except:
        solicitudes_activas = 0

    # Gráfico — donaciones por día de la semana
    dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    donaciones_por_dia = [0] * 7
    publicaciones = Publicacion.query.filter(
        Publicacion.fechaEmisionPublicacion >= inicio_mes
    ).all()
    for p in publicaciones:
        dia = p.fechaEmisionPublicacion.weekday()
        donaciones_por_dia[dia] += 1

    # Ranking top 10
    ranking = db.session.query(
        Usuario,
        db.func.count(Publicacion.nroPublicacion).label('total')
    ).join(Publicacion, Usuario.codUsuario == Publicacion.codUsuario)\
     .join(Rol, Usuario.id_rol == Rol.id_rol)\
     .filter(Rol.nombre == 'Usuario')\
     .group_by(Usuario.codUsuario)\
     .order_by(db.desc('total'))\
     .limit(10).all()

    # Estados para ABM
    estados = EstadoPublicacion.query.all()

    # Moderación — últimas 5 publicaciones
    moderacion = Publicacion.query.order_by(
        Publicacion.fechaEmisionPublicacion.desc()
    ).limit(5).all()
    
    peticiones_pendientes = Peticion.query.filter_by(
        estado=EstadoPeticion.PENDIENTE
    ).order_by(Peticion.fechaEmitida.asc()).limit(5).all()
    

    return render_template('admin/home.html',
        usuario=usuario,
        total_donaciones=total_donaciones,
        usuarios_nuevos=usuarios_nuevos,
        solicitudes_activas=solicitudes_activas,
        dias=dias,
        donaciones_por_dia=donaciones_por_dia,
        ranking=ranking,
        estados=estados,
        moderacion=moderacion,
        peticiones_pendientes=peticiones_pendientes,
    )
    
@admin_bp.route('/admin/estado/editar', methods=['POST'])
@requiere_admin
def editar_estado():
    from flask import request, flash
    estado_id = request.form.get('estado_id')
    nombre = request.form.get('nombre', '').strip()
    estado = EstadoPublicacion.query.get_or_404(estado_id)
    estado.nombreEP = nombre
    db.session.commit()
    flash('Estado actualizado correctamente.', 'success')
    return redirect(url_for('admin.home'))

@admin_bp.route('/admin/estado/nuevo', methods=['POST'])
@requiere_admin
def nuevo_estado():
    from flask import request, flash
    nombre = request.form.get('nombre', '').strip()
    if nombre:
        db.session.add(EstadoPublicacion(nombreEP=nombre))
        db.session.commit()
        flash('Estado creado correctamente.', 'success')
    return redirect(url_for('admin.home'))

@admin_bp.route('/admin/publicacion/eliminar/<int:id>', methods=['POST'])
@requiere_admin
def eliminar_publicacion(id):
    from flask import flash
    pub = Publicacion.query.get_or_404(id)
    db.session.delete(pub)
    db.session.commit()
    flash('Publicación eliminada.', 'success')
    return redirect(url_for('admin.home'))

@admin_bp.route('/admin/exportar-pdf')
@requiere_admin
def exportar_pdf():
    from flask import flash
    flash('Función de exportar PDF próximamente.', 'success')
    return redirect(url_for('admin.home'))