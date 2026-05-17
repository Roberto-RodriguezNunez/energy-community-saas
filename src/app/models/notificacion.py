"""Modelo de Notificación para usuarios de la plataforma."""
from datetime import datetime


class Notificacion:
    """Notificación enviada a un usuario.

    Puede estar relacionada con una entidad concreta (batería, cierre, etc.).
    El usuario puede marcarla como leída.
    """

    TIPOS = ('cierre_disponible', 'cambio_coeficiente', 'bateria_mantenimiento',
             'incidencia', 'general')

    def __init__(self, usuario_oid, tipo, titulo, mensaje,
                 entidad_relacionada_oid=None, entidad_relacionada_tipo=None):
        self.usuario_oid = str(usuario_oid)
        self.fecha = datetime.now().isoformat()
        self.tipo = tipo
        self.titulo = titulo
        self.mensaje = mensaje
        self.entidad_relacionada_oid = (
            str(entidad_relacionada_oid) if entidad_relacionada_oid else None
        )
        self.entidad_relacionada_tipo = entidad_relacionada_tipo
        self.leida = False

    def marcar_leida(self):
        self.leida = True

    def __repr__(self):
        return f'<Notificacion {self.tipo} u={self.usuario_oid} leida={self.leida}>'
