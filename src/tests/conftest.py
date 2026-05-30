"""Fixtures compartidas para todos los tests."""
import pytest
from app import create_app
from app.models.usuario import Usuario
from app.models.comunidad import Comunidad
from app.models.vivienda import Vivienda
from app.models.acceso import AccesoVivienda
from app.models.bateria import Bateria
from app.models.cierre import CierreMensual
from app.models.incidencia import Incidencia
from app.models.notificacion import Notificacion
from app.helpers import oid_to_safe


@pytest.fixture()
def app():
    """Crea la app Flask en modo test con Redis DB 15 (aislada)."""
    import os
    os.environ['REDIS_DB'] = '15'
    os.environ['REDIS_HOST'] = 'localhost'
    application = create_app('development')
    application.config['TESTING'] = True
    application.config['WTF_CSRF_ENABLED'] = False

    # Limpiar DB 15 antes de cada test
    import redis as r
    rc = r.Redis(host=application.config['REDIS_HOST'],
                 port=application.config['REDIS_PORT'],
                 db=15)
    rc.flushdb()

    yield application

    rc.flushdb()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def srp(app):
    return app.sirope


@pytest.fixture()
def superadmin(app, srp):
    """Crea y devuelve un usuario superadmin."""
    u = Usuario('Admin Test', 'admin@test.com', 'admin1234', 'superadmin')
    srp.save(u)
    return u


@pytest.fixture()
def usuario(app, srp):
    """Crea y devuelve un usuario normal."""
    u = Usuario('User Test', 'user@test.com', 'user12345', 'normal')
    srp.save(u)
    return u


@pytest.fixture()
def comunidad(app, srp):
    """Crea y devuelve una comunidad."""
    c = Comunidad(
        nombre='Comunidad Test',
        ubicacion='Vigo',
        fecha_constitucion='2024-01-01',
        estado='activa',
        descripcion='Comunidad de prueba'
    )
    srp.save(c)
    return c


@pytest.fixture()
def vivienda(app, srp, comunidad):
    """Crea y devuelve una vivienda en la comunidad de test."""
    v = Vivienda(
        comunidad_oid=comunidad.__oid__,
        identificador='Piso 1A',
        direccion_completa='Calle Test 1',
        cups='ES0001',
        potencia_contratada_kw=3.45,
        coeficiente_reparto=1.0,
        fecha_alta='2024-01-01',
    )
    srp.save(v)
    return v


@pytest.fixture()
def acceso(app, srp, usuario, vivienda):
    """Crea un acceso del usuario normal a la vivienda."""
    a = AccesoVivienda(
        usuario_oid=usuario.__oid__,
        vivienda_oid=vivienda.__oid__,
        rol_en_vivienda='titular',
    )
    srp.save(a)
    return a


@pytest.fixture()
def bateria(app, srp, comunidad):
    """Crea una batería en la comunidad de test."""
    b = Bateria(
        comunidad_oid=comunidad.__oid__,
        capacidad_nominal_kwh=20.0,
        capacidad_util_actual_kwh=18.0,
        ciclos_acumulados=100,
        fecha_instalacion='2024-01-01',
        fabricante='TestBrand',
        modelo='TestModel',
        estado='operativa',
    )
    srp.save(b)
    return b


@pytest.fixture()
def cierre(app, srp, vivienda):
    """Crea un cierre mensual de test."""
    c = CierreMensual(
        vivienda_oid=vivienda.__oid__,
        mes='2024-10',
        consumo_total_kwh=300.0,
        autoconsumo_directo_kwh=80.0,
        energia_de_bateria_kwh=40.0,
        vertido_a_red_kwh=10.0,
        ahorro_eur=25.0,
        factura_escenario_base_eur=66.0,
        factura_escenario_real_eur=41.0,
        porcentaje_ahorro_global=5.0,
        coeficiente_reparto_aplicado=1.0,
    )
    srp.save(c)
    return c


@pytest.fixture()
def incidencia(app, srp, vivienda, comunidad, usuario):
    """Crea una incidencia de test."""
    i = Incidencia(
        vivienda_oid=vivienda.__oid__,
        comunidad_oid=comunidad.__oid__,
        usuario_oid=usuario.__oid__,
        titulo='Fuga de agua',
        descripcion='Hay una fuga en el baño',
        tipo='averia',
    )
    srp.save(i)
    return i


@pytest.fixture()
def notificacion(app, srp, usuario):
    """Crea una notificación de test."""
    n = Notificacion(
        usuario_oid=usuario.__oid__,
        tipo='general',
        titulo='Notif Test',
        mensaje='Mensaje de prueba',
    )
    srp.save(n)
    return n


# ── Helpers de login ──────────────────────────────────────────────

def login_as(client, email, password):
    """Inicia sesión con las credenciales dadas."""
    return client.post('/login', data={
        'email': email,
        'password': password,
    }, follow_redirects=True)


def login_superadmin(client, superadmin):
    return login_as(client, 'admin@test.com', 'admin1234')


def login_usuario(client, usuario):
    return login_as(client, 'user@test.com', 'user12345')
