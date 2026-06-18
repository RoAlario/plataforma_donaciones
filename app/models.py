from app.extensions import db
from datetime import datetime

class Rol(db.Model):
    __tablename__ = 'rol'

    id_rol  = db.Column(db.Integer, primary_key=True)
    nombre  = db.Column(db.String(50), nullable=False, unique=True)
    fechaAltaRol  = db.Column(db.DateTime, default=datetime.utcnow)
    fechaBajaRol  = db.Column(db.DateTime, nullable=True)

    # relación inversa
    usuarios = db.relationship('Usuario', backref='rol')

    def __repr__(self):
        return f'<Rol {self.nombre}>'


class Usuario(db.Model):
    __tablename__ = 'usuario'

    codUsuario       = db.Column(db.Integer, primary_key=True)
    nombre           = db.Column(db.String(50),  nullable=False)
    email            = db.Column(db.String(100), nullable=False, unique=True)
    telefono         = db.Column(db.String(14),  nullable=False)
    ubicacion        = db.Column(db.String(100), nullable=True)
    contrasena       = db.Column(db.String(200), nullable=False)
    fechaAltaUsuario = db.Column(db.DateTime, default=datetime.utcnow)
    fechaBajaUsuario = db.Column(db.DateTime, nullable=True)
    cantDonaciones   = db.Column(db.Integer, default=0)
    codigoVerif      = db.Column(db.String(6),  nullable=True)
    foto_perfil = db.Column(db.String(200), nullable=True)

    # ── Atributo campañas (False por defecto) ──────────────────────────────
    puedeCrearCampanias = db.Column(db.Boolean, default=False, nullable=False)

    # ── Clave foránea al rol ───────────────────────────────────────────────
    id_rol = db.Column(db.Integer, db.ForeignKey('rol.id_rol'), nullable=False)

    def __repr__(self):
        return f'<Usuario {self.email}>'

    # ── Helpers útiles ─────────────────────────────────────────────────────
    def es_admin(self):
        return self.rol.nombre == 'Admin'

    def es_usuario(self):
        return self.rol.nombre == 'Usuario'
    
class Categoria(db.Model):
    __tablename__ = 'categoria'
    codCategoria       = db.Column(db.Integer, primary_key=True)
    nombreCategoria    = db.Column(db.String(20), nullable=False, unique=True)
    fechaAltaCategoria = db.Column(db.DateTime, default=datetime.utcnow)
    fechaBajaCategoria = db.Column(db.DateTime, nullable=True)
    publicaciones      = db.relationship('Publicacion', backref='categoria')

class Publicacion(db.Model):
    __tablename__ = 'publicacion'
    nroPublicacion          = db.Column(db.Integer, primary_key=True)
    titulo                  = db.Column(db.String(50), nullable=False)
    descripcionPublicacion  = db.Column(db.String(100), nullable=True)
    ubicacion               = db.Column(db.String(100), nullable=False)
    fotos                   = db.Column(db.String(255), nullable=True)
    fechaEmisionPublicacion = db.Column(db.DateTime, default=datetime.utcnow)
    fechaFinPublicacion     = db.Column(db.DateTime, nullable=True)
    categoriaOtro           = db.Column(db.String(50), nullable=True)
    codCategoria            = db.Column(db.Integer, db.ForeignKey('categoria.codCategoria'), nullable=False)
    codUsuario              = db.Column(db.Integer, db.ForeignKey('usuario.codUsuario'), nullable=False)

    # Atributos de Ropa
    genero   = db.Column(db.String(10), nullable=True)
    talle    = db.Column(db.String(2),  nullable=True)
    color    = db.Column(db.String(10), nullable=True)
    material = db.Column(db.String(10), nullable=True)

    # Atributos de Medicamento
    fechaVencimiento = db.Column(db.DateTime, nullable=True)
    receta           = db.Column(db.Boolean, nullable=True)

    # Atributos de Electrónico
    marca = db.Column(db.String(20), nullable=True)

    # Atributos de Alimento
    fechaVencimientoAlimento = db.Column(db.DateTime, nullable=True)