"""Modelo de Incidencia para usuarios de la plataforma."""
from datetime import date


class Incidencia:
    """Incidencia creada por un usuario sobre su vivienda.

    Puede ser una avería, consulta u otro tipo de comunicación.
    El administrador de la comunidad o el superadmin pueden responder y cerrarla.
    """

    TIPOS = ('averia', 'consulta', 'otro')
    ESTADOS = ('abierta', 'en_proceso', 'cerrada')

    def __init__(self, vivienda_oid, comunidad_oid, usuario_oid,
                 titulo, descripcion, tipo='consulta'):
        self.vivienda_oid    = str(vivienda_oid)
        self.comunidad_oid   = str(comunidad_oid)
        self.usuario_oid     = str(usuario_oid)
        self.titulo          = titulo
        self.descripcion     = descripcion
        self.tipo            = tipo   # 'averia', 'consulta', 'otro'
        self.estado          = 'abierta'  # 'abierta', 'en_proceso', 'cerrada'
        self.fecha_creacion  = date.today().isoformat()
        self.fecha_cierre    = None
        self.respuesta_admin = None

    def __repr__(self):
        return f'<Incidencia {self.tipo} estado={self.estado} u={self.usuario_oid}>'
