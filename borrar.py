import sqlite3

# Conectar a la base de datos
conexion = sqlite3.connect('instance/plataforma.db')
cursor = conexion.cursor()

# Dar la orden de borrar
cursor.execute("DELETE FROM usuario WHERE email = 'utnfrm.10@gmail.com'")

# Guardar los cambios y cerrar
conexion.commit()
conexion.close()

print("Usuario borrado con éxito")