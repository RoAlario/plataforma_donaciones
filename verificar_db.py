from app import create_app
from app.models import Publicacion, Usuario

app = create_app()
with app.app_context():
    print("=== TODAS LAS PUBLICACIONES ===")
    pubs = Publicacion.query.all()
    for p in pubs:
        user = Usuario.query.get(p.codUsuario)
        print(f"Pub #{p.nroPublicacion} | titulo: {p.titulo} | codUsuario: {p.codUsuario} | email usuario: {user.email if user else 'NO ENCONTRADO'}")

    print("\n=== TODOS LOS USUARIOS ===")
    users = Usuario.query.all()
    for u in users:
        print(f"ID: {u.codUsuario} | nombre: {u.nombre} | email: {u.email}")