import enum
from datetime import datetime
from app.extensions import db

class Rol(db.Model):
    __tablename__ = 'rol'
    id_rol       = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(50), nullable=False, unique=True)
    fechaAltaRol = db.Column(db.DateTime, default=datetime.utcnow)
    fechaBajaRol = db.Column(db.DateTime, nullable=True)
    usuarios = db.relationship('Usuario', backref='rol')

    def __repr__(self):
        return f'<Rol {self.nombre}>'

class Usuario(db.Model):
    __tablename__ = 'usuario'
    codUsuario          = db.Column(db.Integer, primary_key=True)
    nombre              = db.Column(db.String(50),  nullable=False)
    email               = db.Column(db.String(100), nullable=False, unique=True)
    telefono            = db.Column(db.String(14),  nullable=False)
    ubicacion           = db.Column(db.String(100), nullable=True)
    contrasena          = db.Column(db.String(200), nullable=False)
    fechaAltaUsuario    = db.Column(db.DateTime, default=datetime.utcnow)
    fechaBajaUsuario    = db.Column(db.DateTime, nullable=True)
    cantDonaciones      = db.Column(db.Integer, default=0)
    codigoVerif         = db.Column(db.String(6),  nullable=True)
    foto_perfil         = db.Column(db.String(200), nullable=True)
    puedeCrearCampanias = db.Column(db.Boolean, default=False, nullable=False)
    id_rol = db.Column(db.Integer, db.ForeignKey('rol.id_rol'), nullable=False)
    peticiones = db.relationship('Peticion', backref='usuario', lazy=True)

    def __repr__(self):
        return f'<Usuario {self.email}>'

    def es_admin(self):
        return self.rol is not None and self.rol.nombre == 'Admin'

    def es_usuario(self):
        return self.rol is not None and self.rol.nombre == 'Usuario'

class Categoria(db.Model):
    __tablename__ = 'categoria'
    codCategoria       = db.Column(db.Integer, primary_key=True)
    nombreCategoria    = db.Column(db.String(20), nullable=False, unique=True)
    fechaAltaCategoria = db.Column(db.DateTime, default=datetime.utcnow)
    fechaBajaCategoria = db.Column(db.DateTime, nullable=True)
    publicaciones = db.relationship('Publicacion', backref='categoria')

class Publicacion(db.Model):
    __tablename__ = 'publicacion'
    nroPublicacion          = db.Column(db.Integer, primary_key=True)
    titulo                  = db.Column(db.String(50),  nullable=False)
    descripcionPublicacion  = db.Column(db.String(100), nullable=True)
    ubicacion               = db.Column(db.String(100), nullable=False)
    fotos                   = db.Column(db.String(255), nullable=True)
    fechaEmisionPublicacion = db.Column(db.DateTime, default=datetime.utcnow)
    fechaFinPublicacion     = db.Column(db.DateTime, nullable=True)
    categoriaOtro           = db.Column(db.String(50), nullable=True)
    codCategoria = db.Column(db.Integer, db.ForeignKey('categoria.codCategoria'), nullable=False)
    codUsuario   = db.Column(db.Integer, db.ForeignKey('usuario.codUsuario'),   nullable=False)
    codEstadoPublicacion = db.Column(db.Integer, db.ForeignKey('estado_publicacion.codEstadoPublicacion'), nullable=True)
    nroDireccion         = db.Column(db.Integer, db.ForeignKey('direccion.nroDireccion'), nullable=True)
    genero   = db.Column(db.String(10), nullable=True)
    talle    = db.Column(db.String(10), nullable=True)
    color    = db.Column(db.String(30), nullable=True)
    material = db.Column(db.String(30), nullable=True)
    fechaVencimiento = db.Column(db.DateTime, nullable=True)
    receta           = db.Column(db.Boolean,  nullable=True)
    marca = db.Column(db.String(20), nullable=True)

class EstadoPublicacion(db.Model):
    __tablename__ = 'estado_publicacion'
    codEstadoPublicacion  = db.Column(db.Integer, primary_key=True)
    nombreEP              = db.Column(db.String(20), nullable=False, unique=True)
    fechaAltaPublicacion  = db.Column(db.DateTime, default=datetime.utcnow)
    fechaBajaPublicacion  = db.Column(db.DateTime, nullable=True)
    publicaciones = db.relationship('Publicacion', backref='estado')

class Direccion(db.Model):
    __tablename__ = 'direccion'
    nroDireccion      = db.Column(db.Integer, primary_key=True)
    nombreCalle       = db.Column(db.String(100), nullable=False)
    nroDeCasa         = db.Column(db.Integer, nullable=True)
    codigoPostal      = db.Column(db.Integer, nullable=True)
    fechaAltaDireccion = db.Column(db.DateTime, default=datetime.utcnow)
    fechaBajaDireccion = db.Column(db.DateTime, nullable=True)

class EstadoPeticion(enum.Enum):
    PENDIENTE = 'Pendiente'
    RECHAZADA = 'Rechazada'
    ACEPTADA  = 'Aceptada'

class Peticion(db.Model):
    __tablename__ = 'peticiones'
    id            = db.Column(db.Integer, primary_key=True)
    nroPeticion   = db.Column(db.Integer, unique=True, nullable=False)
    razonPeticion = db.Column(db.String(200), nullable=False)
    fechaEmitida  = db.Column(db.DateTime, nullable=False)
    cuitoCuil     = db.Column(db.String(20), nullable=False)
    estado        = db.Column(db.Enum(EstadoPeticion), default=EstadoPeticion.PENDIENTE, nullable=False)
    usuario_id    = db.Column(db.Integer, db.ForeignKey('usuario.codUsuario'), nullable=False)

    def __repr__(self):
        return f'<Peticion {self.nroPeticion} - {self.estado}>'