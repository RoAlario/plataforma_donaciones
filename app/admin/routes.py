from flask import Blueprint, render_template, session, redirect, url_for
from app.models import (Publicacion, Usuario, EstadoPublicacion, Peticion, Rol,
                         EstadoPeticion, Campana, EstadoCampana, Transaccion, EstadoTransaccion)
from app.extensions import db
from app.auth.routes import requiere_admin
from datetime import datetime, timedelta

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

    try:
        solicitudes_activas = Peticion.query.filter_by(estado=EstadoPeticion.PENDIENTE).count()
    except:
        solicitudes_activas = 0

    # Estadísticas de campañas
    total_campañas = Campana.query.filter(
        Campana.fechaInicio >= inicio_mes
    ).count()
    campañas_activas = Campana.query.filter(
        Campana.estado == EstadoCampana.ACTIVA
    ).count()
    campañas_finalizadas = Campana.query.filter(
        Campana.estado == EstadoCampana.FINALIZADA
    ).count()

    # Gráfico — actividad semanal (donaciones + campañas) por día de la semana
    # Se usa UTC-3 (Argentina) para agrupar por día local
    offset_arg = timedelta(hours=-3)
    dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    donaciones_por_dia = [0] * 7
    campañas_por_dia = [0] * 7

    publicaciones = Publicacion.query.filter(
        Publicacion.fechaEmisionPublicacion >= inicio_mes
    ).all()
    for p in publicaciones:
        fecha_local = p.fechaEmisionPublicacion + offset_arg
        dia = fecha_local.weekday()
        donaciones_por_dia[dia] += 1

    campanas_mes = Campana.query.filter(
        Campana.fechaInicio >= inicio_mes
    ).all()
    for c in campanas_mes:
        fecha_local = c.fechaInicio + offset_arg
        dia = fecha_local.weekday()
        campañas_por_dia[dia] += 1

    # Ranking top 10 (donaciones + ofertas de campaña)
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
        Publicacion.fechaEmisionPublicacion.desc()).limit(5).all()
    
    peticiones_pendientes = Peticion.query.filter_by(
        estado=EstadoPeticion.PENDIENTE).order_by(Peticion.fechaEmitida.asc()).limit(5).all()
    

    return render_template('admin/home.html',
        usuario=usuario,
        total_donaciones=total_donaciones,
        usuarios_nuevos=usuarios_nuevos,
        solicitudes_activas=solicitudes_activas,
        total_campañas=total_campañas,
        campañas_activas=campañas_activas,
        campañas_finalizadas=campañas_finalizadas,
        dias=dias,
        donaciones_por_dia=donaciones_por_dia,
        campañas_por_dia=campañas_por_dia,
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
    from flask import send_file
    from fpdf import FPDF
    from io import BytesIO

    hoy = datetime.utcnow()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0)

    # Recopilar datos
    total_donaciones = Publicacion.query.filter(
        Publicacion.fechaEmisionPublicacion >= inicio_mes
    ).count()
    total_campañas = Campana.query.filter(
        Campana.fechaInicio >= inicio_mes
    ).count()
    campañas_activas = Campana.query.filter(
        Campana.estado == EstadoCampana.ACTIVA
    ).count()
    campañas_finalizadas = Campana.query.filter(
        Campana.estado == EstadoCampana.FINALIZADA
    ).count()
    usuarios_nuevos = Usuario.query.filter(
        Usuario.fechaAltaUsuario >= inicio_mes
    ).count()

    ranking = db.session.query(
        Usuario.nombre,
        Usuario.email,
        db.func.count(Publicacion.nroPublicacion).label('total')
    ).join(Publicacion, Usuario.codUsuario == Publicacion.codUsuario)\
     .join(Rol, Usuario.id_rol == Rol.id_rol)\
     .filter(Rol.nombre == 'Usuario')\
     .group_by(Usuario.codUsuario)\
     .order_by(db.desc('total'))\
     .limit(10).all()

    # Gráfico semanal
    offset_arg = timedelta(hours=-3)
    dias = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
    donaciones_por_dia = [0] * 7
    campañas_por_dia = [0] * 7

    publicaciones = Publicacion.query.filter(
        Publicacion.fechaEmisionPublicacion >= inicio_mes
    ).all()
    for p in publicaciones:
        fecha_local = p.fechaEmisionPublicacion + offset_arg
        donaciones_por_dia[fecha_local.weekday()] += 1

    campanas_mes = Campana.query.filter(
        Campana.fechaInicio >= inicio_mes
    ).all()
    for c in campanas_mes:
        fecha_local = c.fechaInicio + offset_arg
        campañas_por_dia[fecha_local.weekday()] += 1

    # Generar PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Título
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 12, 'Reporte de Actividad', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 8, f'Generado: {hoy.strftime("%d/%m/%Y %H:%M")}', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(10)

    # Estadísticas generales
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Estadísticas del mes', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, f'Total donaciones: {total_donaciones}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f'Total campañas: {total_campañas}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f'Campañas activas: {campañas_activas}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f'Campañas finalizadas: {campañas_finalizadas}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f'Usuarios nuevos: {usuarios_nuevos}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(8)

    # Actividad semanal
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Actividad semanal', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 8, 'Día        Donaciones    Campañas', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    for i, dia in enumerate(dias):
        pdf.cell(0, 7, f'{dia:<12}{donaciones_por_dia[i]:<14}{campañas_por_dia[i]}',
                 new_x='LMARGIN', new_y='NEXT')
    pdf.ln(8)

    # Ranking top 10
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Top 10 donantes del mes', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    if ranking:
        pdf.cell(0, 8, '#    Nombre                 Email                          Donaciones', new_x='LMARGIN', new_y='NEXT')
        for idx, (nombre, email, total) in enumerate(ranking, 1):
            pdf.cell(0, 7, f'{idx:<5}{nombre:<23}{email:<33}{total}',
                     new_x='LMARGIN', new_y='NEXT')
    else:
        pdf.cell(0, 8, 'No hay donaciones registradas en el período.', new_x='LMARGIN', new_y='NEXT')

    # Guardar en memoria
    pdf_buffer = BytesIO()
    pdf_bytes = pdf.output()
    pdf_buffer.write(pdf_bytes)
    pdf_buffer.seek(0)

    filename = f'reporte_actividad_{hoy.strftime("%Y%m%d_%H%M")}.pdf'
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)