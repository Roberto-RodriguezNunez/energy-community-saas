"""Gestión de usuarios — solo superadmin."""
from flask import render_template, redirect, url_for, request, abort, jsonify, current_app
from flask_login import login_required, current_user
from sirope import OID
from datetime import date

from app.modules.usuarios import usuarios_bp
from app.models.usuario import Usuario
from app.models.vivienda import Vivienda
from app.models.comunidad import Comunidad
from app.models.acceso import AccesoVivienda
from app.helpers import (oid_from_safe, oid_to_safe, flash_exito, flash_error,
                          is_xhr, puede_borrar_usuario)
from app.decorators import superadmin_required


@usuarios_bp.route('/')
@login_required
@superadmin_required
def lista():
    srp = current_app.sirope
    q = request.args.get('q', '').lower()
    usuarios = list(srp.load_all(Usuario))
    if q:
        usuarios = [u for u in usuarios if q in getattr(u, 'nombre', '').lower()
                    or q in getattr(u, 'email', '').lower()]
    return render_template('usuarios/lista.html', usuarios=usuarios, q=q)


@usuarios_bp.route('/<safe_oid>')
@login_required
@superadmin_required
def detalle(safe_oid):
    srp = current_app.sirope
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        abort(404)
    usuario = srp.load(oid)
    if not usuario:
        abort(404)

    usr_str = str(oid)
    accesos = [a for a in srp.load_all(AccesoVivienda) if str(a.usuario_oid) == usr_str]
    accesos_detalle = []
    for a in accesos:
        try:
            viv = srp.load(OID.from_text(a.vivienda_oid))
            com = srp.load(OID.from_text(viv.comunidad_oid)) if viv else None
            accesos_detalle.append({
                'acceso': a,
                'vivienda': viv,
                'comunidad': com,
                'acceso_safe_oid': oid_to_safe(a.__oid__),
            })
        except Exception:
            pass

    # Viviendas disponibles para asignar (sin acceso ya)
    viv_ya_asignadas = {a.vivienda_oid for a in accesos}
    viviendas_disponibles = [
        v for v in srp.load_all(Vivienda)
        if str(v.__oid__) not in viv_ya_asignadas
    ]

    # Comunidades disponibles para crear vivienda nueva
    comunidades = list(srp.load_all(Comunidad))

    return render_template('usuarios/detalle.html',
                           usuario=usuario,
                           safe_oid=safe_oid,
                           accesos_detalle=accesos_detalle,
                           viviendas_disponibles=viviendas_disponibles,
                           comunidades=comunidades)


@usuarios_bp.route('/<safe_oid>/asignar-vivienda', methods=['POST'])
@login_required
@superadmin_required
def asignar_vivienda(safe_oid):
    """Asigna el usuario a una vivienda desde su ficha."""
    srp = current_app.sirope
    try:
        usr_oid = oid_from_safe(safe_oid)
    except Exception:
        abort(404)
    usuario = srp.load(usr_oid)
    if not usuario:
        abort(404)

    vivienda_safe_oid = request.form.get('vivienda_safe_oid', '')
    rol = request.form.get('rol_en_vivienda', 'titular')

    if not vivienda_safe_oid:
        flash_error('Selecciona una vivienda.')
        return redirect(url_for('usuarios.detalle', safe_oid=safe_oid))

    try:
        viv_oid = oid_from_safe(vivienda_safe_oid)
    except Exception:
        abort(404)

    viv = srp.load(viv_oid)
    if not viv:
        abort(404)

    # Comprobar que no existe ya
    usr_str = str(usr_oid)
    viv_str = str(viv_oid)
    existe = srp.find_first(
        AccesoVivienda,
        lambda a, _u=usr_str, _v=viv_str: str(a.usuario_oid) == _u and str(a.vivienda_oid) == _v
    )
    if existe:
        flash_error(f'{usuario.nombre} ya tiene acceso a esa vivienda.')
        return redirect(url_for('usuarios.detalle', safe_oid=safe_oid))

    acceso = AccesoVivienda(
        usuario_oid=usr_oid,
        vivienda_oid=viv_oid,
        rol_en_vivienda=rol,
        fecha_incorporacion=date.today().isoformat()
    )
    srp.save(acceso)
    flash_exito(f'{usuario.nombre} asignado a {viv.identificador} como {rol}.')
    return redirect(url_for('usuarios.detalle', safe_oid=safe_oid))


@usuarios_bp.route('/<safe_oid>/eliminar', methods=['POST'])
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
    usuario = srp.load(oid)
    if not usuario:
        if is_xhr():
            return jsonify({'success': False, 'error': 'No encontrado'}), 404
        abort(404)

    if str(oid) == str(current_user.__oid__):
        flash_error('No puedes eliminar tu propia cuenta.')
        if is_xhr():
            return jsonify({'success': False, 'error': 'No puedes eliminar tu propia cuenta.'})
        return redirect(url_for('usuarios.lista'))

    puede, motivo = puede_borrar_usuario(srp, oid)
    if not puede:
        flash_error(f'No se puede eliminar: {motivo}')
        if is_xhr():
            return jsonify({'success': False, 'error': motivo})
        return redirect(url_for('usuarios.lista'))

    usr_str = str(oid)
    for a in list(srp.load_all(AccesoVivienda)):
        if str(a.usuario_oid) == usr_str:
            srp.delete(a.__oid__)

    nombre = usuario.nombre
    srp.delete(oid)
    flash_exito(f'Usuario "{nombre}" eliminado.')
    if is_xhr():
        return jsonify({'success': True, 'redirect': url_for('usuarios.lista')})
    return redirect(url_for('usuarios.lista'))
