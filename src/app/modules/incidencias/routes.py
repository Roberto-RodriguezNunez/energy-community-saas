"""Gestión de Incidencias."""
from datetime import date
from flask import render_template, redirect, url_for, request, abort, jsonify, current_app
from flask_login import login_required, current_user
from sirope import OID

from app.modules.incidencias import incidencias_bp
from app.modules.incidencias.forms import IncidenciaForm, RespuestaForm
from app.models.incidencia import Incidencia
from app.models.acceso import AccesoVivienda
from app.models.vivienda import Vivienda
from app.helpers import oid_from_safe, oid_to_safe, flash_exito, flash_error, is_xhr
from app.decorators import superadmin_required


# ---------------------------------------------------------------------------
# Lista de incidencias
# ---------------------------------------------------------------------------

@incidencias_bp.route('/')
@login_required
def lista():
    srp = current_app.sirope
    usr_str = str(current_user.__oid__)

    if current_user.es_superadmin:
        incidencias = list(srp.load_all(Incidencia))
    else:
        # Admin de comunidad: ve las incidencias de sus comunidades + las suyas
        accesos_admin = [
            a for a in srp.load_all(AccesoVivienda)
            if str(a.usuario_oid) == usr_str and getattr(a, 'es_admin_comunidad', False)
        ]
        viviendas_admin = {a.vivienda_oid for a in accesos_admin}
        incidencias = [
            i for i in srp.load_all(Incidencia)
            if str(i.usuario_oid) == usr_str or str(i.vivienda_oid) in viviendas_admin
        ]

    # Enriquecer con datos de vivienda para la tabla
    detalle = []
    for inc in incidencias:
        try:
            viv = srp.load(OID.from_text(inc.vivienda_oid))
        except Exception:
            viv = None
        detalle.append({
            'inc': inc,
            'safe_oid': oid_to_safe(inc.__oid__),
            'viv': viv,
        })

    # Ordenar: abiertas primero, luego por fecha descendente
    orden_estado = {'abierta': 0, 'en_proceso': 1, 'cerrada': 2}
    detalle.sort(key=lambda d: (
        orden_estado.get(d['inc'].estado, 9),
        d['inc'].fecha_creacion or ''
    ), reverse=False)

    return render_template('incidencias/lista.html', detalle=detalle)


# ---------------------------------------------------------------------------
# Nueva incidencia
# ---------------------------------------------------------------------------

@incidencias_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva():
    srp = current_app.sirope

    if current_user.es_superadmin:
        flash_error('Los superadmin no pueden crear incidencias.')
        return redirect(url_for('incidencias.lista'))

    usr_str = str(current_user.__oid__)

    # Viviendas a las que tiene acceso el usuario
    accesos = list(srp.filter(
        AccesoVivienda,
        lambda a, _u=usr_str: str(a.usuario_oid) == _u
    ))

    viviendas = []
    for a in accesos:
        try:
            viv = srp.load(OID.from_text(a.vivienda_oid))
            if viv:
                viviendas.append(viv)
        except Exception:
            pass

    if not viviendas:
        flash_error('No tienes ninguna vivienda asignada. Contacta con el administrador.')
        return redirect(url_for('incidencias.lista'))

    form = IncidenciaForm()

    # Construir opciones de vivienda para el template
    viviendas_opciones = [
        (oid_to_safe(v.__oid__), v.identificador)
        for v in viviendas
    ]

    if form.validate_on_submit():
        # Determinar vivienda seleccionada
        vivienda_safe = request.form.get('vivienda_safe_oid')
        if not vivienda_safe and len(viviendas) == 1:
            vivienda_safe = oid_to_safe(viviendas[0].__oid__)

        if not vivienda_safe:
            flash_error('Debes seleccionar una vivienda.')
            return render_template('incidencias/form.html', form=form,
                                   viviendas_opciones=viviendas_opciones,
                                   preseleccionada=viviendas[0] if len(viviendas) == 1 else None)
        try:
            viv_oid = oid_from_safe(vivienda_safe)
        except Exception:
            flash_error('Vivienda no válida.')
            return render_template('incidencias/form.html', form=form,
                                   viviendas_opciones=viviendas_opciones,
                                   preseleccionada=viviendas[0] if len(viviendas) == 1 else None)

        viv = srp.load(viv_oid)
        if not viv:
            abort(404)

        inc = Incidencia(
            vivienda_oid=viv_oid,
            comunidad_oid=viv.comunidad_oid,
            usuario_oid=current_user.__oid__,
            titulo=form.titulo.data.strip(),
            descripcion=form.descripcion.data.strip(),
            tipo=form.tipo.data,
        )
        srp.save(inc)
        flash_exito('Incidencia enviada correctamente.')
        return redirect(url_for('incidencias.lista'))

    preseleccionada = viviendas[0] if len(viviendas) == 1 else None
    return render_template('incidencias/form.html', form=form,
                           viviendas_opciones=viviendas_opciones,
                           preseleccionada=preseleccionada)


# ---------------------------------------------------------------------------
# Detalle de incidencia
# ---------------------------------------------------------------------------

@incidencias_bp.route('/<safe_oid>')
@login_required
def detalle(safe_oid):
    srp = current_app.sirope
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        abort(404)
    inc = srp.load(oid)
    if not inc:
        abort(404)

    # Permiso: superadmin ve todo; admin ve las de su comunidad; usuario las suyas
    if not current_user.es_superadmin:
        usr_str = str(current_user.__oid__)
        es_propia = str(inc.usuario_oid) == usr_str
        es_admin_viv = srp.find_first(
            AccesoVivienda,
            lambda a, _u=usr_str, _v=inc.vivienda_oid: (
                str(a.usuario_oid) == _u and str(a.vivienda_oid) == _v and getattr(a, 'es_admin_comunidad', False)
            )
        )
        if not es_propia and not es_admin_viv:
            abort(403)

    try:
        viv = srp.load(OID.from_text(inc.vivienda_oid))
    except Exception:
        viv = None

    form_respuesta = RespuestaForm(prefix='resp')
    if inc.estado:
        form_respuesta.estado.data = inc.estado

    return render_template('incidencias/detalle.html',
                           inc=inc,
                           safe_oid=safe_oid,
                           viv=viv,
                           form_respuesta=form_respuesta)


# ---------------------------------------------------------------------------
# Responder incidencia (solo admin/superadmin)
# ---------------------------------------------------------------------------

def _puede_gestionar(srp, inc) -> bool:
    """True si el usuario actual puede responder/gestionar esta incidencia."""
    if current_user.es_superadmin:
        return True
    usr_str = str(current_user.__oid__)
    return bool(srp.find_first(
        AccesoVivienda,
        lambda a, _u=usr_str, _v=inc.vivienda_oid: (
            str(a.usuario_oid) == _u and str(a.vivienda_oid) == _v and getattr(a, 'es_admin_comunidad', False)
        )
    ))


@incidencias_bp.route('/<safe_oid>/responder', methods=['POST'])
@login_required
def responder(safe_oid):
    srp = current_app.sirope
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        abort(404)
    inc = srp.load(oid)
    if not inc:
        abort(404)
    if not _puede_gestionar(srp, inc):
        abort(403)

    form_respuesta = RespuestaForm(prefix='resp')
    if form_respuesta.validate_on_submit():
        inc.respuesta_admin = form_respuesta.respuesta.data.strip()
        inc.estado = form_respuesta.estado.data
        if inc.estado == 'cerrada' and not inc.fecha_cierre:
            inc.fecha_cierre = date.today().isoformat()
        elif inc.estado != 'cerrada':
            inc.fecha_cierre = None
        srp.save(inc)
        flash_exito('Respuesta guardada correctamente.')
    else:
        flash_error('Revisa los campos del formulario de respuesta.')

    return redirect(url_for('incidencias.detalle', safe_oid=safe_oid))


# ---------------------------------------------------------------------------
# Eliminar incidencia (solo superadmin)
# ---------------------------------------------------------------------------

@incidencias_bp.route('/<safe_oid>/eliminar', methods=['POST'])
@login_required
@superadmin_required
def eliminar(safe_oid):
    srp = current_app.sirope
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        if is_xhr():
            return jsonify({'success': False, 'error': 'OID inválida'}), 404
        abort(404)

    inc = srp.load(oid)
    if not inc:
        if is_xhr():
            return jsonify({'success': False, 'error': 'No encontrado'}), 404
        abort(404)

    srp.delete(oid)
    flash_exito('Incidencia eliminada.')

    if is_xhr():
        return jsonify({'success': True})
    return redirect(url_for('incidencias.lista'))
