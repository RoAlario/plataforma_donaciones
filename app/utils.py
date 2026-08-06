import random
from datetime import datetime, timezone, timedelta

def generar_codigo_transaccion():
    nums = [random.randint(100, 999) for _ in range(3)]
    return f'{nums[0]}-{nums[1]}-{nums[2]}'

def tiempo_transcurrido(fecha):
    diff = datetime.now(timezone.utc).replace(tzinfo=None) - fecha
    minutos = diff.seconds // 60
    horas = diff.seconds // 3600
    dias = diff.days
    if dias > 0:
        return f'Hace {dias} dia{"s" if dias > 1 else ""}'
    elif horas > 0:
        return f'Hace {horas} hora{"s" if horas > 1 else ""}'
    elif minutos > 0:
        return f'Hace {minutos} minuto{"s" if minutos > 1 else ""}'
    return 'Hace un momento'
