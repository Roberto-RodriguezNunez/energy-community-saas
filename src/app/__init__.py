"""Factory de la aplicación EnergyComm."""
import sirope
import redis
from flask import Flask, render_template
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name=None):
    """Crea y configura la aplicación Flask."""
    app = Flask(__name__)

    from config import get_config
    app.config.from_object(get_config(config_name))

    # Inicializar Sirope (persistencia sobre Redis)
    redis_client = redis.Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        db=app.config['REDIS_DB'],
        password=app.config.get('REDIS_PASSWORD'),
    )
    app.sirope = sirope.Sirope(redis_obj=redis_client)

    # Extensiones
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    # Funciones disponibles globalmente en todos los templates
    from app.helpers import oid_to_safe
    from markupsafe import Markup
    from flask_wtf.csrf import generate_csrf

    app.jinja_env.globals['oid_to_safe'] = oid_to_safe

    def csrf_token_hidden():
        return Markup(f'<input type="hidden" name="csrf_token" value="{generate_csrf()}">')

    app.jinja_env.globals['csrf_token_hidden'] = csrf_token_hidden

    # Loader de usuario para Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.usuario import Usuario
        from app.helpers import oid_from_safe
        try:
            oid = oid_from_safe(user_id)
            return app.sirope.load(oid)
        except Exception:
            return None

    # Context processor: globals disponibles en todos los templates
    @app.context_processor
    def inject_globals():
        def contador_no_leidas():
            if not current_user.is_authenticated:
                return 0
            from app.models.notificacion import Notificacion
            usr_str = str(current_user.__oid__)
            return sum(
                1 for n in app.sirope.load_all(Notificacion)
                if str(n.usuario_oid) == usr_str and not n.leida
            )

        def mi_comunidad_nav():
            """Retorna lista de {safe_oid, nombre} de las comunidades del usuario, o []."""
            if not current_user.is_authenticated or current_user.es_superadmin:
                return []
            from app.models.acceso import AccesoVivienda
            from app.models.vivienda import Vivienda
            from app.helpers import oid_to_safe
            from sirope import OID
            try:
                usr_str = str(current_user.__oid__)
                accesos = [a for a in app.sirope.load_all(AccesoVivienda)
                           if str(a.usuario_oid) == usr_str]
                vistas = {}
                for a in accesos:
                    try:
                        viv = app.sirope.load(OID.from_text(a.vivienda_oid))
                        if not viv:
                            continue
                        com_str = str(viv.comunidad_oid)
                        if com_str in vistas:
                            continue
                        com = app.sirope.load(OID.from_text(com_str))
                        if com:
                            vistas[com_str] = {
                                'safe_oid': oid_to_safe(com.__oid__),
                                'nombre': com.nombre,
                            }
                    except Exception:
                        continue
                return list(vistas.values())
            except Exception:
                return []

        return {
            'contador_no_leidas': contador_no_leidas,
            'mi_comunidad_nav': mi_comunidad_nav,
        }

    # Registro de blueprints
    from app.modules.auth import auth_bp
    from app.modules.main import main_bp
    from app.modules.comunidades import comunidades_bp
    from app.modules.viviendas import viviendas_bp
    from app.modules.usuarios import usuarios_bp
    from app.modules.accesos import accesos_bp
    from app.modules.baterias import baterias_bp
    from app.modules.cierres import cierres_bp
    from app.modules.notificaciones import notificaciones_bp
    from app.modules.incidencias import incidencias_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(comunidades_bp, url_prefix='/comunidades')
    app.register_blueprint(viviendas_bp, url_prefix='/viviendas')
    app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
    app.register_blueprint(accesos_bp, url_prefix='/accesos')
    app.register_blueprint(baterias_bp, url_prefix='/baterias')
    app.register_blueprint(cierres_bp, url_prefix='/cierres')
    app.register_blueprint(notificaciones_bp, url_prefix='/notificaciones')
    app.register_blueprint(incidencias_bp)

    # Manejadores de error personalizados
    @app.errorhandler(401)
    def no_autorizado(e):
        return render_template('errors/401.html'), 401

    @app.errorhandler(403)
    def prohibido(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def no_encontrado(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def error_interno(e):
        return render_template('errors/500.html'), 500

    return app
