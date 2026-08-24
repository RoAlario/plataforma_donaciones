from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, flash
from app.models import (Publicacion, Usuario, EstadoPublicacion, Peticion, Rol,
                         EstadoPeticion, Campana, EstadoCampana, Transaccion, EstadoTransaccion)
from app.extensions import db
from app.auth.routes import requiere_admin
from datetime import datetime, timedelta, timezone

admin_bp = Blueprint('admin', __name__)

MESES_ES = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
            7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}

def sanitize_pdf(text):
    """Reemplaza caracteres no soportados por Helvetica en fpdf2."""
    replacements = {
        '\u2014': '-', '\u2013': '-',  # em dash, en dash
        '\u00e1': 'a', '\u00e9': 'e', '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
        '\u00f1': 'n', '\u00fc': 'u', '\u00e4': 'a',
        '\u00c1': 'A', '\u00c9': 'E', '\u00cd': 'I', '\u00d3': 'O', '\u00da': 'U',
        '\u00d1': 'N', '\u00dc': 'U',
        '\u00ba': '', '\u00aa': '',  # º ª
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def semana_a_rango(week_str):
    try:
        year, week = map(int, week_str.split('-W'))
    except (ValueError, AttributeError):
        year, week = map(int, semana_actual_str().split('-W'))
    lunes = datetime.strptime(f'{year}-W{week}-1', '%G-W%V-%u')
    offset_arg = timedelta(hours=-3)
    lunes_local = lunes + offset_arg
    domingo_local = lunes_local + timedelta(days=6, hours=23, minutes=59, seconds=59)
    lunes_utc = lunes_local - offset_arg
    domingo_utc = domingo_local - offset_arg
    return lunes_utc, domingo_utc, lunes_local, domingo_local

def semana_a_label(week_str):
    try:
        year, week = map(int, week_str.split('-W'))
    except (ValueError, AttributeError):
        year, week = map(int, semana_actual_str().split('-W'))
    lunes = datetime.strptime(f'{year}-W{week}-1', '%G-W%V-%u')
    domingo = lunes + timedelta(days=6)
    return f"{lunes.day} {MESES_ES[lunes.month]} - {domingo.day} {MESES_ES[domingo.month]} {domingo.year}"

def semana_actual_str():
    hoy = datetime.now(timezone.utc).replace(tzinfo=None)
    offset_arg = timedelta(hours=-3)
    hoy_local = hoy + offset_arg
    iso = hoy_local.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"

def semana_anterior(week_str):
    year, week = map(int, week_str.split('-W'))
    d = datetime.strptime(f'{year}-W{week}-1', '%G-W%V-%u') - timedelta(weeks=1)
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"

def semana_siguiente(week_str):
    year, week = map(int, week_str.split('-W'))
    d = datetime.strptime(f'{year}-W{week}-1', '%G-W%V-%u') + timedelta(weeks=1)
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"

def datos_semana(week_str):
    lunes_utc, domingo_utc, _, _ = semana_a_rango(week_str)
    dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    donaciones = [0] * 7
    campanas = [0] * 7

    publicaciones = Publicacion.query.filter(
        Publicacion.fechaEmisionPublicacion >= lunes_utc,
        Publicacion.fechaEmisionPublicacion <= domingo_utc
    ).all()
    for p in publicaciones:
        offset_arg = timedelta(hours=-3)
        fecha_local = p.fechaEmisionPublicacion + offset_arg
        donaciones[fecha_local.weekday()] += 1

    campanas_data = Campana.query.filter(
        Campana.fechaInicio >= lunes_utc,
        Campana.fechaInicio <= domingo_utc
    ).all()
    for c in campanas_data:
        offset_arg = timedelta(hours=-3)
        fecha_local = c.fechaInicio + offset_arg
        campanas[fecha_local.weekday()] += 1

    return dias, donaciones, campanas

@admin_bp.route('/admin/api/chart-data')
def chart_data():
    if 'usuario_id' not in session:
        return jsonify(error='No autenticado'), 401
    usuario = Usuario.query.get(session['usuario_id'])
    if not usuario or not usuario.es_admin():
        return jsonify(error='No autorizado'), 403
    week = request.args.get('week', semana_actual_str())
    dias, donaciones, campanas = datos_semana(week)
    label = semana_a_label(week)
    return jsonify(dias=dias, donaciones=donaciones, campanas=campanas, semana_label=label, semana=week)

@admin_bp.route('/admin/home')
@requiere_admin
def home():
    usuario = Usuario.query.get(session['usuario_id'])
    hoy = datetime.now(timezone.utc).replace(tzinfo=None)
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

    total_campañas = Campana.query.filter(
        Campana.fechaInicio >= inicio_mes
    ).count()
    campañas_activas = Campana.query.filter(
        Campana.estado == EstadoCampana.ACTIVA
    ).count()
    campañas_finalizadas = Campana.query.filter(
        Campana.estado == EstadoCampana.FINALIZADA
    ).count()

    # Gráfico — semana actual
    week_actual = semana_actual_str()
    label_actual = semana_a_label(week_actual)

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

    estados = EstadoPublicacion.query.all()

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
        week_actual=week_actual,
        label_actual=label_actual,
        ranking=ranking,
        estados=estados,
        moderacion=moderacion,
        peticiones_pendientes=peticiones_pendientes,
    )
    
@admin_bp.route('/admin/estado/editar', methods=['POST'])
@requiere_admin
def editar_estado():
    estado_id = request.form.get('estado_id')
    nombre = request.form.get('nombre', '').strip()
    if not nombre:
        flash('El nombre del estado es obligatorio.', 'error')
        return redirect(url_for('admin.home'))
    if len(nombre) > 20:
        flash('El nombre del estado no puede tener más de 20 caracteres.', 'error')
        return redirect(url_for('admin.home'))
    estado = EstadoPublicacion.query.get_or_404(estado_id)
    estado.nombreEP = nombre
    db.session.commit()
    flash('Estado actualizado correctamente.', 'success')
    return redirect(url_for('admin.home'))

@admin_bp.route('/admin/estado/nuevo', methods=['POST'])
@requiere_admin
def nuevo_estado():
    nombre = request.form.get('nombre', '').strip()
    if not nombre:
        flash('El nombre del estado es obligatorio.', 'error')
        return redirect(url_for('admin.home'))
    if len(nombre) > 20:
        flash('El nombre del estado no puede tener más de 20 caracteres.', 'error')
        return redirect(url_for('admin.home'))
    db.session.add(EstadoPublicacion(nombreEP=nombre))
    db.session.commit()
    flash('Estado creado correctamente.', 'success')
    return redirect(url_for('admin.home'))

@admin_bp.route('/admin/publicacion/eliminar/<int:id>', methods=['POST'])
@requiere_admin
def eliminar_publicacion(id):
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

    hoy = datetime.now(timezone.utc).replace(tzinfo=None)
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

    # Gráfico semanal (semana actual)
    week_actual = semana_actual_str()
    label_semana = semana_a_label(week_actual)
    dias, donaciones_por_dia, campañas_por_dia = datos_semana(week_actual)

    # Generar gráfico con matplotlib
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    chart_buffer = BytesIO()
    x = np.arange(len(dias))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 3.5))
    barras_don = ax.bar(x - width/2, donaciones_por_dia, width, label='Donaciones', color='#efb181', edgecolor='none')
    barras_camp = ax.bar(x + width/2, campañas_por_dia, width, label='Campañas', color='#6CAAB0', edgecolor='none')

    ax.set_ylabel('Cantidad')
    ax.set_xticks(x)
    ax.set_xticklabels(dias)
    ax.legend()
    max_val = max(max(donaciones_por_dia, default=0), max(campañas_por_dia, default=0))
    ax.set_ylim(bottom=0, top=max(max_val + 1, 1))
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%d'))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    for barra in barras_don:
        h = barra.get_height()
        if h > 0:
            ax.text(barra.get_x() + barra.get_width()/2., h, f'{int(round(h))}',
                    ha='center', va='bottom', fontsize=9)
    for barra in barras_camp:
        h = barra.get_height()
        if h > 0:
            ax.text(barra.get_x() + barra.get_width()/2., h, f'{int(round(h))}',
                    ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    fig.savefig(chart_buffer, format='png', dpi=150)
    plt.close(fig)
    chart_buffer.seek(0)

    # Generar PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Logo (izquierda, más chico)
    import os
    logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo.png')
    pdf.image(logo_path, x=10, y=10, w=20)
    pdf.ln(20)

    # Título
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, sanitize_pdf('Reporte de Actividad'), new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 8, sanitize_pdf('Sistema de Gestion de Donaciones'), new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 8, f'Generado: {hoy.strftime("%d/%m/%Y %H:%M")}', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(10)

    # Estadísticas generales - cajitas de colores
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, sanitize_pdf('Estadísticas del mes'), new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    stats = [
        (sanitize_pdf('Total donaciones'), str(int(total_donaciones)), (239, 177, 129)),
        (sanitize_pdf('Total campañas'), str(int(total_campañas)), (108, 170, 176)),
        (sanitize_pdf('Campañas activas'), str(int(campañas_activas)), (129, 199, 132)),
        (sanitize_pdf('Campañas finalizadas'), str(int(campañas_finalizadas)), (255, 183, 77)),
        (sanitize_pdf('Usuarios nuevos'), str(int(usuarios_nuevos)), (129, 140, 248)),
    ]

    box_w = 34
    box_h = 22
    gap = 4
    row1 = stats[:3]
    row2 = stats[3:]

    # Fila 1: 3 cajas
    total_w1 = len(row1) * box_w + (len(row1) - 1) * gap
    start_x1 = (210 - total_w1) / 2
    y = pdf.get_y()
    for i, (label, value, color) in enumerate(row1):
        x = start_x1 + i * (box_w + gap)
        pdf.set_fill_color(*color)
        pdf.rect(x, y, box_w, box_h, 'F')
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_xy(x, y + 3)
        pdf.cell(box_w, 8, value, align='C')
        pdf.set_font('Helvetica', '', 7)
        pdf.set_xy(x, y + 12)
        pdf.cell(box_w, 8, label, align='C')

    # Fila 2: 2 cajas
    total_w2 = len(row2) * box_w + (len(row2) - 1) * gap
    start_x2 = (210 - total_w2) / 2
    y2 = y + box_h + 4
    for i, (label, value, color) in enumerate(row2):
        x = start_x2 + i * (box_w + gap)
        pdf.set_fill_color(*color)
        pdf.rect(x, y2, box_w, box_h, 'F')
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_xy(x, y2 + 3)
        pdf.cell(box_w, 8, value, align='C')
        pdf.set_font('Helvetica', '', 7)
        pdf.set_xy(x, y2 + 12)
        pdf.cell(box_w, 8, label, align='C')

    pdf.set_y(y2 + box_h + 6)

    # Actividad semanal (gráfico)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, sanitize_pdf(f'Actividad semanal - {label_semana}'), new_x='LMARGIN', new_y='NEXT')
    pdf.image(chart_buffer, x=15, w=180)
    pdf.ln(8)

    # Ranking top 10
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Top 10 donantes del mes', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)

    if ranking:
        col_w = [10, 45, 70, 30]
        headers = ['#', 'Nombre', 'Email', 'Donaciones']

        # Cabecera
        pdf.set_fill_color(108, 170, 176)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 10)
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 9, h, border=0, align='C', fill=True)
        pdf.ln()

        # Filas
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 9)
        for idx, (nombre, email, total) in enumerate(ranking, 1):
            if idx % 2 == 0:
                pdf.set_fill_color(230, 240, 240)
                fill = True
            else:
                pdf.set_fill_color(255, 255, 255)
                fill = True
            pdf.cell(col_w[0], 8, str(idx), border=0, align='C', fill=fill)
            pdf.cell(col_w[1], 8, sanitize_pdf(nombre)[:22], border=0, align='L', fill=fill)
            pdf.cell(col_w[2], 8, sanitize_pdf(email)[:35], border=0, align='L', fill=fill)
            pdf.cell(col_w[3], 8, str(int(total)), border=0, align='C', fill=fill)
            pdf.ln()
    else:
        pdf.set_font('Helvetica', '', 11)
        pdf.cell(0, 8, sanitize_pdf('No hay donaciones registradas en el periodo.'), new_x='LMARGIN', new_y='NEXT')

    # Guardar en memoria
    pdf_buffer = BytesIO()
    pdf_bytes = pdf.output()
    pdf_buffer.write(pdf_bytes)
    pdf_buffer.seek(0)

    filename = f'reporte_actividad_{hoy.strftime("%Y%m%d_%H%M")}.pdf'
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)