"""CRUD de CierresMensuales."""
from flask import render_template, redirect, url_for, request, abort, jsonify, current_app
from flask_login import login_required, current_user
from sirope import OID
import json

from app.modules.cierres import cierres_bp
from app.modules.cierres.forms import CierreForm
from app.models.cierre import CierreMensual
from app.models.vivienda import Vivienda
from app.models.acceso import AccesoVivienda
from app.helpers import (oid_from_safe, oid_to_safe, flash_exito, flash_error,
                          is_xhr, usuario_tiene_acceso, crear_notificacion)
from app.decorators import superadmin_required


def _comprobar_acceso_o_superadmin(srp, viv_oid):
    if current_user.es_superadmin:
        return
    if not usuario_tiene_acceso(srp, current_user.__oid__, viv_oid):
        abort(403)


@cierres_bp.route('/vivienda/<vivienda_safe_oid>/')
@login_required
def lista(vivienda_safe_oid):
    srp = current_app.sirope
    try:
        viv_oid = oid_from_safe(vivienda_safe_oid)
    except Exception:
        abort(404)
    viv = srp.load(viv_oid)
    if not viv:
        abort(404)
    _comprobar_acceso_o_superadmin(srp, viv_oid)

    viv_str = str(viv_oid)
    mes_filtro = request.args.get('mes', '')
    cierres = [c for c in srp.load_all(CierreMensual) if str(c.vivienda_oid) == viv_str]
    if mes_filtro:
        cierres = [c for c in cierres if mes_filtro in c.mes]
    cierres = sorted(cierres, key=lambda c: c.mes, reverse=True)
    com = srp.load(OID.from_text(viv.comunidad_oid))

    return render_template('cierres/lista.html',
                           cierres=cierres, viv=viv,
                           vivienda_safe_oid=vivienda_safe_oid,
                           com=com, mes_filtro=mes_filtro,
                           es_admin=current_user.es_superadmin)


@cierres_bp.route('/vivienda/<vivienda_safe_oid>/nuevo', methods=['GET', 'POST'])
@login_required
@superadmin_required
def nuevo(vivienda_safe_oid):
    srp = current_app.sirope
    try:
        viv_oid = oid_from_safe(vivienda_safe_oid)
    except Exception:
        abort(404)
    viv = srp.load(viv_oid)
    if not viv:
        abort(404)

    form = CierreForm()
    com = srp.load(OID.from_text(viv.comunidad_oid))

    if form.validate_on_submit():
        viv_str = str(viv_oid)
        mes = form.mes.data
        existe = srp.find_first(
            CierreMensual,
            lambda c, _v=viv_str, _m=mes: str(c.vivienda_oid) == _v and c.mes == _m
        )
        if existe:
            flash_error(f'Ya existe un cierre para {mes} en esta vivienda.')
            return render_template('cierres/form.html', form=form, viv=viv,
                                   com=com, vivienda_safe_oid=vivienda_safe_oid)
        cierre = CierreMensual(
            vivienda_oid=viv_oid, mes=mes,
            consumo_total_kwh=form.consumo_total_kwh.data,
            autoconsumo_directo_kwh=form.autoconsumo_directo_kwh.data,
            energia_de_bateria_kwh=form.energia_de_bateria_kwh.data,
            vertido_a_red_kwh=form.vertido_a_red_kwh.data,
            ahorro_eur=form.ahorro_eur.data,
            factura_escenario_base_eur=form.factura_escenario_base_eur.data,
            factura_escenario_real_eur=form.factura_escenario_real_eur.data,
            porcentaje_ahorro_global=form.porcentaje_ahorro_global.data,
            coeficiente_reparto_aplicado=form.coeficiente_reparto_aplicado.data
        )
        srp.save(cierre)

        for a in srp.load_all(AccesoVivienda):
            if str(a.vivienda_oid) == viv_str and a.rol_en_vivienda in ('titular', 'convivente'):
                crear_notificacion(
                    srp, a.usuario_oid, 'cierre_disponible',
                    f'Cierre de {mes} disponible',
                    f'El cierre energético de {mes} de tu vivienda ya está disponible. Ahorro: {cierre.ahorro_eur:.2f} €',
                    entidad_oid=cierre.__oid__, entidad_tipo='CierreMensual'
                )

        flash_exito(f'Cierre de {mes} creado correctamente.')
        return redirect(url_for('cierres.lista', vivienda_safe_oid=vivienda_safe_oid))
    return render_template('cierres/form.html', form=form, viv=viv,
                           com=com, vivienda_safe_oid=vivienda_safe_oid)


@cierres_bp.route('/<safe_oid>')
@login_required
def detalle(safe_oid):
    srp = current_app.sirope
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        abort(404)
    cierre = srp.load(oid)
    if not cierre:
        abort(404)

    viv_oid = OID.from_text(cierre.vivienda_oid)
    viv = srp.load(viv_oid)
    if not viv:
        abort(404)
    _comprobar_acceso_o_superadmin(srp, viv_oid)

    vivienda_safe_oid = oid_to_safe(viv_oid)
    com = srp.load(OID.from_text(viv.comunidad_oid))

    chart_energia = json.dumps({
        'labels': ['Autoconsumo directo', 'De batería', 'De red'],
        'datos': [
            cierre.autoconsumo_directo_kwh,
            cierre.energia_de_bateria_kwh,
            cierre.energia_de_red_kwh
        ]
    })

    return render_template('cierres/detalle.html',
                           cierre=cierre, safe_oid=safe_oid,
                           viv=viv, vivienda_safe_oid=vivienda_safe_oid,
                           com=com, es_admin=current_user.es_superadmin,
                           chart_energia=chart_energia)


@cierres_bp.route('/<safe_oid>/eliminar', methods=['POST'])
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
    cierre = srp.load(oid)
    if not cierre:
        if is_xhr():
            return jsonify({'success': False, 'error': 'No encontrado'}), 404
        abort(404)

    vivienda_safe_oid = oid_to_safe(OID.from_text(cierre.vivienda_oid))
    mes = cierre.mes
    srp.delete(oid)
    flash_exito(f'Cierre de {mes} eliminado.')
    if is_xhr():
        return jsonify({'success': True})
    return redirect(url_for('cierres.lista', vivienda_safe_oid=vivienda_safe_oid))
