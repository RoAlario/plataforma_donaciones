from extensions import db
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