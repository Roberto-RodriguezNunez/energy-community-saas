"""Configuración de la aplicación EnergyComm."""
import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    WTF_CSRF_ENABLED = True
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']

    # Render pasa REDIS_URL como redis://host:port — parsearlo si existe
    _redis_url = os.environ.get('REDIS_URL', '')
    if _redis_url:
        import urllib.parse as _up
        _p = _up.urlparse(_redis_url)
        REDIS_HOST = _p.hostname or 'localhost'
        REDIS_PORT = _p.port or 6379
        REDIS_DB   = int((_p.path or '/0').lstrip('/') or 0)
        REDIS_PASSWORD = _p.password
    else:
        REDIS_HOST     = os.environ.get('REDIS_HOST', 'localhost')
        REDIS_PORT     = int(os.environ.get('REDIS_PORT', 6379))
        REDIS_DB       = int(os.environ.get('REDIS_DB', 0))
        REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


_configs = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}


def get_config(nombre=None):
    nombre = nombre or os.environ.get('FLASK_ENV', 'development')
    return _configs.get(nombre, DevelopmentConfig)
