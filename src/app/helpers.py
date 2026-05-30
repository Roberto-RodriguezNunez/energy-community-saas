"""
Utilidades centrales de EnergyComm.
Importado por todos los blueprints — mantener sin imports circulares.
"""
from flask import flash, request as _request


# ---------------------------------------------------------------------------
# OIDs URL-safe
# ---------------------------------------------------------------------------

def oid_to_safe(oid) -> str:
    """Convierte un OID de Sirope a string apto para rutas Flask.

    El formato nativo de Sirope es "namespace.Clase@numero", con puntos y @
    que no son seguros en URLs. Los sustituimos por marcadores únicos.
    """
    return str(oid).replace('.', '-dot-').replace('@', '-at-')


def oid_from_safe(safe: str):
    """Reconstruye un OID de Sirope desde un string URL-safe.

    Invierte la transformación de oid_to_safe y usa OID.from_text().
    Lanza ValueError si el formato es inválido.
    """
    from sirope import OID
    texto = safe.replace('-dot-', '.').replace('-at-', '@')
    return OID.from_text(texto)


# ---------------------------------------------------------------------------
# Detección de petición AJAX
# ---------------------------------------------------------------------------

def is_xhr(req=None) -> bool:
    """Devuelve True si la petición es XMLHttpRequest (AJAX)."""
    req = req or _request
    return req.headers.get('X-Requested-With') == 'XMLHttpRequest'


# ---------------------------------------------------------------------------
# Flash helpers
# ---------------------------------------------------------------------------

def flash_exito(mensaje: str):
    flash(mensaje, 'success')


def flash_error(mensaje: str):
    flash(mensaje, 'danger')


def flash_aviso(mensaje: str):
    flash(mensaje, 'warning')


def flash_info(mensaje: str):
    flash(mensaje, 'info')


# ---------------------------------------------------------------------------
# Comprobaciones de permisos
# ---------------------------------------------------------------------------

def usuario_tiene_acceso(srp, usuario_oid, vivienda_oid) -> bool:
    """Comprueba si el usuario tiene algún acceso a la vivienda."""
    from app.models.acceso import AccesoVivienda

    usr_str = str(usuario_oid)
    viv_str = str(vivienda_oid)
    acceso = srp.find_first(
        AccesoVivienda,
        lambda a: str(a.usuario_oid) == usr_str and str(a.vivienda_oid) == viv_str
    )
    return acceso is not None


# ---------------------------------------------------------------------------
# Recálculo de coeficientes de reparto
# ---------------------------------------------------------------------------

def recalcular_coeficientes(srp, comunidad_oid):
    """Recalcula los coeficientes de reparto de todas las viviendas de una
    comunidad, proporcionales a su potencia contratada.

    coef_i = potencia_i / suma_potencias
    """
    from app.models.vivienda import Vivienda

    from app.models.acceso import AccesoVivienda

    com_str = str(comunidad_oid)
    viviendas = [v for v in srp.load_all(Vivienda) if str(v.comunidad_oid) == com_str]
    if not viviendas:
        return
    suma = sum(v.potencia_contratada_kw for v in viviendas)
    if suma <= 0:
        return

    accesos = list(srp.load_all(AccesoVivienda))

    for v in viviendas:
        nuevo = round(v.potencia_contratada_kw / suma, 6)
        cambio = v.coeficiente_reparto != nuevo
        v.coeficiente_reparto = nuevo
        srp.save(v)

        if cambio:
            viv_str = str(v.__oid__)
            usuarios = {str(a.usuario_oid) for a in accesos if str(a.vivienda_oid) == viv_str}
            for usr_oid_str in usuarios:
                crear_notificacion(
                    srp, usr_oid_str, 'cambio_coeficiente',
                    f'Coeficiente actualizado — {v.identificador}',
                    f'Tu coeficiente de reparto en {v.identificador} ha cambiado a {nuevo:.4f}.',
                )


# ---------------------------------------------------------------------------
# Borrado en cascada
# ---------------------------------------------------------------------------

def cascade_delete_vivienda(srp, vivienda_oid):
    """Borra una vivienda y todos sus objetos dependientes.

    Cascada: AccesoVivienda → CierreMensual → Incidencia → Vivienda
    """
    from app.models.acceso import AccesoVivienda
    from app.models.cierre import CierreMensual
    from app.models.incidencia import Incidencia

    viv_str = str(vivienda_oid)

    for a in list(srp.load_all(AccesoVivienda)):
        if str(a.vivienda_oid) == viv_str:
            srp.delete(a.__oid__)

    for c in list(srp.load_all(CierreMensual)):
        if str(c.vivienda_oid) == viv_str:
            srp.delete(c.__oid__)

    for i in list(srp.load_all(Incidencia)):
        if str(i.vivienda_oid) == viv_str:
            srp.delete(i.__oid__)

    srp.delete(vivienda_oid)


def cascade_delete_comunidad(srp, comunidad_oid):
    """Borra una comunidad y todos sus objetos dependientes.

    Cascada: Viviendas (con su propia cascada) → Bateria → Notificaciones relacionadas → Comunidad
    """
    from app.models.vivienda import Vivienda
    from app.models.bateria import Bateria
    from app.models.notificacion import Notificacion

    com_str = str(comunidad_oid)

    # Borrar cada vivienda con su cascada
    for v in list(srp.load_all(Vivienda)):
        if str(v.comunidad_oid) == com_str:
            cascade_delete_vivienda(srp, v.__oid__)

    # Borrar batería
    for b in list(srp.load_all(Bateria)):
        if str(b.comunidad_oid) == com_str:
            srp.delete(b.__oid__)

    # Borrar notificaciones relacionadas con esta comunidad
    for n in list(srp.load_all(Notificacion)):
        if n.entidad_relacionada_oid and str(n.entidad_relacionada_oid) == com_str:
            srp.delete(n.__oid__)

    srp.delete(comunidad_oid)


def puede_borrar_usuario(srp, usuario_oid) -> tuple:
    """Comprueba si es seguro borrar un usuario.

    Devuelve (True, '') si se puede borrar.
    Devuelve (False, motivo) si hay algún bloqueo.

    Bloqueos:
    - Es el único titular de alguna vivienda.
    - Es el único admin de alguna comunidad.
    """
    from app.models.acceso import AccesoVivienda
    from app.models.vivienda import Vivienda
    from sirope import OID

    usr_str = str(usuario_oid)
    todos_accesos = list(srp.load_all(AccesoVivienda))
    accesos_usuario = [a for a in todos_accesos if str(a.usuario_oid) == usr_str]

    for acceso in accesos_usuario:
        if acceso.rol_en_vivienda == 'titular':
            otros_titulares = [
                a for a in todos_accesos
                if str(a.vivienda_oid) == acceso.vivienda_oid
                and a.rol_en_vivienda == 'titular'
                and str(a.usuario_oid) != usr_str
            ]
            if not otros_titulares:
                viv = srp.load(OID.from_text(acceso.vivienda_oid))
                nombre_viv = viv.identificador if viv else acceso.vivienda_oid
                return False, f'Es el único titular de la vivienda "{nombre_viv}"'

    return True, ''


# ---------------------------------------------------------------------------
# Creación de notificaciones
# ---------------------------------------------------------------------------

def crear_notificacion(srp, usuario_oid, tipo, titulo, mensaje,
                       entidad_oid=None, entidad_tipo=None):
    """Crea y guarda una notificación para un usuario."""
    from app.models.notificacion import Notificacion
    n = Notificacion(
        usuario_oid=str(usuario_oid),
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        entidad_relacionada_oid=str(entidad_oid) if entidad_oid else None,
        entidad_relacionada_tipo=entidad_tipo
    )
    srp.save(n)
    return n


def notificar_a_comunidad(srp, comunidad_oid, tipo, titulo, mensaje,
                           entidad_oid=None, entidad_tipo=None):
    """Envía una notificación a todos los usuarios con acceso a la comunidad."""
    from app.models.vivienda import Vivienda
    from app.models.acceso import AccesoVivienda

    com_str = str(comunidad_oid)
    viviendas_oids = {
        str(v.__oid__)
        for v in srp.load_all(Vivienda)
        if str(v.comunidad_oid) == com_str
    }
    # Usuarios únicos con acceso
    usuarios_notificados = set()
    for a in srp.load_all(AccesoVivienda):
        if str(a.vivienda_oid) in viviendas_oids:
            usr = a.usuario_oid
            if usr not in usuarios_notificados:
                usuarios_notificados.add(usr)
                crear_notificacion(srp, usr, tipo, titulo, mensaje,
                                   entidad_oid, entidad_tipo)
