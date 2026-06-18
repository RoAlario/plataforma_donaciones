from flask import Blueprint, render_template, request, session, redirect, url_for
from app.models import Publicacion, Categoria, Usuario
from app.extensions import db
from datetime import datetime

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