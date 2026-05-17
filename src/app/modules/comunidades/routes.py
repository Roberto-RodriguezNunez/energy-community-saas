"""CRUD de Comunidades."""
import json
from collections import defaultdict
from flask import render_template, redirect, url_for, request, abort, jsonify, current_app
from flask_login import login_required, current_user

from app.modules.comunidades import comunidades_bp
from app.modules.comunidades.forms import ComunidadForm
from app.models.comunidad import Comunidad
from app.models.vivienda import Vivienda
from app.models.bateria import Bateria
from app.models.acceso import AccesoVivienda
from app.models.cierre import CierreMensual
from app.helpers import oid_from_safe, flash_exito, flash_error, is_xhr, cascade_delete_comunidad
from app.decorators import superadmin_required
from datetime import date


@comunidades_bp.route('/')
@login_required
@superadmin_required
def lista():
    srp = current_app.sirope
    q = request.args.get('q', '').lower()
    estado_filtro = request.args.get('estado', '')
    comunidades = list(srp.load_all(Comunidad))
    if q:
        comunidades = [c for c in comunidades if q in c.nombre.lower() or q in c.ubicacion.lower()]
    if estado_filtro:
        comunidades = [c for c in comunidades if c.estado == estado_filtro]
    return render_template('comunidades/lista.html', comunidades=comunidades,
                           q=q, estado_filtro=estado_filtro)


@comunidades_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
@superadmin_required
def nueva():
    srp = current_app.sirope
    form = ComunidadForm()
    if form.validate_on_submit():
        existe = srp.find_first(Comunidad, lambda c: c.nombre.lower() == form.nombre.data.lower())
        if existe:
            flash_error('Ya existe una comunidad con ese nombre.')
            return render_template('comunidades/form.html', form=form, titulo='Nueva comunidad')
        com = Comunidad(
            nombre=form.nombre.data,
            ubicacion=form.ubicacion.data,
            fecha_constitucion=form.fecha_constitucion.data.isoformat(),
            estado=form.estado.data,
            descripcion=form.descripcion.data
        )
        srp.save(com)
        flash_exito(f'Comunidad "{com.nombre}" creada.')
        return redirect(url_for('comunidades.lista'))
    return render_template('comunidades/form.html', form=form, titulo='Nueva comunidad')


@comunidades_bp.route('/<safe_oid>')
@login_required
def detalle(safe_oid):
    srp = current_app.sirope
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        abort(404)
    com = srp.load(oid)
    if not com:
        abort(404)

    # Superadmin ve todo; usuario normal solo si tiene acceso a alguna vivienda aquí
    if not current_user.es_superadmin:
        com_str = str(oid)
        viviendas_com = {
            str(v.__oid__)
            for v in srp.load_all(Vivienda)
            if str(v.comunidad_oid) == com_str
        }
        acceso = srp.find_first(
            AccesoVivienda,
            lambda a: str(a.usuario_oid) == str(current_user.__oid__)
                      and str(a.vivienda_oid) in viviendas_com
        )
        if not acceso:
            abort(403)

    com_str = str(oid)
    viviendas = [v for v in srp.load_all(Vivienda) if str(v.comunidad_oid) == com_str]
    bateria = srp.find_first(Bateria, lambda b: str(b.comunidad_oid) == com_str)

    # Gráfica agregada de la comunidad (suma de todos los cierres de sus viviendas)
    viv_oids = {str(v.__oid__) for v in viviendas}
    cierres_com = [c for c in srp.load_all(CierreMensual) if str(c.vivienda_oid) in viv_oids]

    por_mes = defaultdict(lambda: {'ahorro': 0.0, 'base': 0.0, 'real': 0.0})
    for c in cierres_com:
        por_mes[c.mes]['ahorro'] += c.ahorro_eur
        por_mes[c.mes]['base']   += c.factura_escenario_base_eur
        por_mes[c.mes]['real']   += c.factura_escenario_real_eur

    meses = sorted(por_mes.keys())[-6:]
    if meses:
        chart_comunidad = json.dumps({
            'labels': meses,
            'ahorro': [round(por_mes[m]['ahorro'], 2) for m in meses],
            'base':   [round(por_mes[m]['base'],   2) for m in meses],
            'real':   [round(por_mes[m]['real'],   2) for m in meses],
        })
        ahorro_total_com = round(sum(d['ahorro'] for d in por_mes.values()), 2)
    else:
        chart_comunidad  = None
        ahorro_total_com = 0.0

    return render_template('comunidades/detalle.html',
                           com=com, safe_oid=safe_oid,
                           viviendas=viviendas, bateria=bateria,
                           es_admin=current_user.es_superadmin,
                           chart_comunidad=chart_comunidad,
                           ahorro_total_com=ahorro_total_com)


@comunidades_bp.route('/<safe_oid>/editar', methods=['GET', 'POST'])
@login_required
@superadmin_required
def editar(safe_oid):
    srp = current_app.sirope
    try:
        oid = oid_from_safe(safe_oid)
    except Exception:
        abort(404)
    com = srp.load(oid)
    if not com:
        abort(404)

    form = ComunidadForm(obj=com)
    if request.method == 'GET':
        try:
            form.fecha_constitucion.data = date.fromisoformat(com.fecha_constitucion)
        except Exception:
            pass

    if form.validate_on_submit():
        duplicada = srp.find_first(
            Comunidad,
            lambda c: c.nombre.lower() == form.nombre.data.lower()
                      and str(c.__oid__) != str(oid)
        )
        if duplicada:
            flash_error('Ya existe otra comunidad con ese nombre.')
            return render_template('comunidades/form.html', form=form,
                                   titulo='Editar comunidad', com=com, safe_oid=safe_oid)
        com.nombre = form.nombre.data
        com.ubicacion = form.ubicacion.data
        com.fecha_constitucion = form.fecha_constitucion.data.isoformat()
        com.estado = form.estado.data
        com.descripcion = form.descripcion.data
        srp.save(com)
        flash_exito(f'Comunidad "{com.nombre}" actualizada.')
        return redirect(url_for('comunidades.detalle', safe_oid=safe_oid))
    return render_template('comunidades/form.html', form=form,
                           titulo='Editar comunidad', com=com, safe_oid=safe_oid)


@comunidades_bp.route('/<safe_oid>/eliminar', methods=['POST'])
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
    com = srp.load(oid)
    if not com:
        if is_xhr():
            return jsonify({'success': False, 'error': 'No encontrada'}), 404
        abort(404)

    nombre = com.nombre
    cascade_delete_comunidad(srp, oid)
    flash_exito(f'Comunidad "{nombre}" y todos sus datos han sido eliminados.')
    if is_xhr():
        return jsonify({'success': True, 'redirect': url_for('comunidades.lista')})
    return redirect(url_for('comunidades.lista'))
