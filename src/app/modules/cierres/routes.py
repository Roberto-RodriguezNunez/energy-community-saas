"""CRUD de CierresMensuales."""
from flask import render_template, redirect, url_for, request, abort, jsonify
from flask_login import login_required, current_user
import json

from app.extensions import db
from app.modules.cierres import cierres_bp
from app.modules.cierres.forms import CierreForm
from app.models.cierre import CierreMensual
from app.models.vivienda import Vivienda
from app.models.acceso import AccesoVivienda
from app.helpers import (oid_from_safe, oid_to_safe, flash_exito, flash_error,
                          is_xhr, usuario_tiene_acceso, crear_notificacion)
from app.decorators import superadmin_required


def _comprobar_acceso_o_superadmin(viv_oid):
    if current_user.es_superadmin:
        return
    if not usuario_tiene_acceso(current_user.id, viv_oid):
        abort(403)


@cierres_bp.route('/vivienda/<vivienda_safe_oid>/')
@login_required
def lista(vivienda_safe_oid):
    try:
        viv_oid = oid_from_safe(vivienda_safe_oid)
    except Exception:
        abort(404)
    viv = db.session.get(Vivienda, viv_oid)
    if not viv:
        abort(404)
    _comprobar_acceso_o_superadmin(viv_oid)

    mes_filtro = request.args.get('mes', '')
    query = CierreMensual.query.filter_by(vivienda_oid=viv_oid)
    if mes_filtro:
        query = query.filter(CierreMensual.mes.contains(mes_filtro))
    cierres = query.order_by(CierreMensual.mes.desc()).all()
    from app.models.comunidad import Comunidad
    com = db.session.get(Comunidad, viv.comunidad_oid)

    return render_template('cierres/lista.html',
                           cierres=cierres, viv=viv,
                           vivienda_safe_oid=vivienda_safe_oid,
                           com=com, mes_filtro=mes_filtro,
                           es_admin=current_user.es_superadmin)


@cierres_bp.route('/vivienda/<vivienda_safe_oid>/nuevo', methods=['GET', 'POST'])
@login_required
@superadmin_required
def nuevo(vivienda_safe_oid):
    from app.models.comunidad import Comunidad
    try:
        viv_oid = oid_from_safe(vivienda_safe_oid)
    except Exception:
        abort(404)
    viv = db.session.get(Vivienda, viv_oid)
    if not viv:
        abort(404)

    form = CierreForm()
    com = db.session.get(Comunidad, viv.comunidad_oid)

    if form.validate_on_submit():
        mes = form.mes.data
        existe = CierreMensual.query.filter_by(
            vivienda_oid=viv_oid, mes=mes
        ).first()
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
        db.session.add(cierre)
        db.session.commit()

        accesos = AccesoVivienda.query.filter_by(vivienda_oid=viv_oid).all()
        for a in accesos:
            if a.rol_en_vivienda in ('titular', 'convivente'):
                crear_notificacion(
                    a.usuario_oid, 'cierre_disponible',
                    f'Cierre de {mes} disponible',
                    f'El cierre energético de {mes} de tu vivienda ya está disponible. Ahorro: {cierre.ahorro_eur:.2f} €',
                    entidad_oid=cierre.id, entidad_tipo='CierreMensual'
                )

        flash_exito(f'Cierre de {mes} creado correctamente.')
        return redirect(url_for('cierres.lista', vivienda_safe_oid=vivienda_safe_oid))
    return render_template('cierres/form.html', form=form, viv=viv,
                           com=com, vivienda_safe_oid=vivienda_safe_oid)


@cierres_bp.route('/<safe_oid>')
@login_required
def detalle(safe_oid):
    from app.models.comunidad import Comunidad
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        abort(404)
    cierre = db.session.get(CierreMensual, oid)
    if not cierre:
        abort(404)

    viv_oid = cierre.vivienda_oid
    viv = db.session.get(Vivienda, viv_oid)
    if not viv:
        abort(404)
    _comprobar_acceso_o_superadmin(viv_oid)

    vivienda_safe_oid = oid_to_safe(viv_oid)
    com = db.session.get(Comunidad, viv.comunidad_oid)

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
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        if is_xhr():
            return jsonify({'success': False, 'error': 'OID inválida'}), 404
        abort(404)
    cierre = db.session.get(CierreMensual, oid)
    if not cierre:
        if is_xhr():
            return jsonify({'success': False, 'error': 'No encontrado'}), 404
        abort(404)

    vivienda_safe_oid = oid_to_safe(cierre.vivienda_oid)
    mes = cierre.mes
    db.session.delete(cierre)
    db.session.commit()
    flash_exito(f'Cierre de {mes} eliminado.')
    if is_xhr():
        return jsonify({'success': True})
    return redirect(url_for('cierres.lista', vivienda_safe_oid=vivienda_safe_oid))
