"""Rutas de Notificaciones."""
from flask import render_template, redirect, url_for, request, abort, jsonify, current_app
from flask_login import login_required, current_user

from app.modules.notificaciones import notificaciones_bp
from app.models.notificacion import Notificacion
from app.helpers import oid_from_safe, flash_exito, flash_error, is_xhr


@notificaciones_bp.route('/')
@login_required
def lista():
    srp = current_app.sirope
    usr_str = str(current_user.__oid__)
    notificaciones = sorted(
        [n for n in srp.load_all(Notificacion) if str(n.usuario_oid) == usr_str],
        key=lambda n: n.fecha, reverse=True
    )
    return render_template('notificaciones/lista.html', notificaciones=notificaciones)


@notificaciones_bp.route('/<safe_oid>/leer', methods=['POST'])
@login_required
def marcar_leida(safe_oid):
    srp = current_app.sirope
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        if is_xhr():
            return jsonify({'success': False, 'error': 'OID inválida'}), 404
        abort(404)
    notif = srp.load(oid)
    if not notif:
        if is_xhr():
            return jsonify({'success': False, 'error': 'No encontrada'}), 404
        abort(404)
    if str(notif.usuario_oid) != str(current_user.__oid__):
        abort(403)

    notif.marcar_leida()
    srp.save(notif)

    if is_xhr():
        return jsonify({'success': True})
    return redirect(url_for('notificaciones.lista'))


@notificaciones_bp.route('/leer-todas', methods=['POST'])
@login_required
def marcar_todas_leidas():
    srp = current_app.sirope
    usr_str = str(current_user.__oid__)
    for n in srp.load_all(Notificacion):
        if str(n.usuario_oid) == usr_str and not n.leida:
            n.marcar_leida()
            srp.save(n)
    flash_exito('Todas las notificaciones marcadas como leídas.')
    if is_xhr():
        return jsonify({'success': True})
    return redirect(url_for('notificaciones.lista'))


@notificaciones_bp.route('/<safe_oid>/eliminar', methods=['POST'])
@login_required
def eliminar(safe_oid):
    srp = current_app.sirope
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        if is_xhr():
            return jsonify({'success': False, 'error': 'OID inválida'}), 404
        abort(404)
    notif = srp.load(oid)
    if not notif:
        if is_xhr():
            return jsonify({'success': False, 'error': 'No encontrada'}), 404
        abort(404)
    if str(notif.usuario_oid) != str(current_user.__oid__) and not current_user.es_superadmin:
        abort(403)

    srp.delete(oid)
    flash_exito('Notificación eliminada.')
    if is_xhr():
        return jsonify({'success': True})
    return redirect(url_for('notificaciones.lista'))
