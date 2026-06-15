import sqlite3

# Conectar a la base de datos
conexion = sqlite3.connect('instance/plataforma.db')
cursor = conexion.cursor()

# Actualizar el número de rol a 1
cursor.execute("UPDATE usuario SET id_rol = 1 WHERE email = 'utnfrm.10@gmail.com'")

# Guardar los cambios y cerrar
conexion.commit()
conexion.close()

print("El usuario ahora es admin")