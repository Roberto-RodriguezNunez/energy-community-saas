"""Modelo de Usuario de la plataforma."""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Usuario(UserMixin):
    """Usuario de EnergyComm.

    Puede ser superadmin del SaaS o usuario normal.
    Flask-Login usa get_id() para serializar la sesión.
    """

    ROLES = ('superadmin', 'normal')

    def __init__(self, nombre, email, password, rol_global='normal'):
        self.nombre = nombre
        self.email = email.lower().strip()
        self.password_hash = generate_password_hash(password)
        self.rol_global = rol_global
        self.fecha_registro = datetime.now().isoformat()

    def verificar_password(self, password) -> bool:
        """Comprueba la contraseña en texto plano contra el hash almacenado."""
        return check_password_hash(self.password_hash, password)

    def set_password(self, nueva_password):
        """Actualiza el hash de contraseña."""
        self.password_hash = generate_password_hash(nueva_password)

    def get_id(self) -> str:
        """Flask-Login: devuelve identificador URL-safe para la sesión."""
        from app.helpers import oid_to_safe
        return oid_to_safe(self.__oid__)

    @property
    def es_superadmin(self) -> bool:
        return self.rol_global == 'superadmin'

    def __repr__(self):
        return f'<Usuario {self.email}>'
