"""Configuración de la aplicación EnergyComm."""
import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    WTF_CSRF_ENABLED = True
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']


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
