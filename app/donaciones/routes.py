from app.models import Publicacion, Categoria, Usuario, EstadoPublicacion, Direccion
from app.extensions import db
from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, flash

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

    donaciones_realizadas = Publicacion.query.filter_by(codUsuario=donante.codUsuario).count()

    return render_template('donaciones/detalle.html',
        p=publicacion,
        donante=donante,
        usuario=usuario,
        donaciones_realizadas=donaciones_realizadas,
        tiempo=tiempo_transcurrido(publicacion.fechaEmisionPublicacion)
    )