"""Modelo de Comunidad energética."""
from datetime import date


class Comunidad:
    """Representa una comunidad energética en la plataforma.

    Una comunidad agrupa viviendas que comparten infraestructura energética
    (batería, generación solar) y reparten ahorros según coeficientes.
    """

    ESTADOS = ('activa', 'suspendida')

    def __init__(self, nombre, ubicacion, fecha_constitucion=None,
                 estado='activa', descripcion=''):
        self.nombre = nombre
        self.ubicacion = ubicacion
        self.fecha_constitucion = fecha_constitucion or date.today().isoformat()
        self.estado = estado
        self.descripcion = descripcion

    @property
    def es_activa(self):
        return self.estado == 'activa'

    def __repr__(self):
        return f'<Comunidad {self.nombre}>'
