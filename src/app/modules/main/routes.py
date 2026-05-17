"""Rutas del panel principal (dashboard) según rol del usuario."""
import json
from collections import defaultdict
from flask import render_template, current_app
from flask_login import login_required, current_user

from app.modules.main import main_bp
from app.models.comunidad import Comunidad
from app.models.vivienda import Vivienda
from app.models.usuario import Usuario
from app.models.acceso import AccesoVivienda
from app.models.bateria import Bateria
from app.models.cierre import CierreMensual
from app.helpers import oid_to_safe


@main_bp.route('/')
def index():
    srp = current_app.sirope

    if not current_user.is_authenticated:
        return render_template('main/landing.html')

    if current_user.es_superadmin:
        comunidades = list(srp.load_all(Comunidad))
        todas_viviendas = list(srp.load_all(Vivienda))
        # Agrupar viviendas por comunidad
        viviendas_por_com = {}
        for v in todas_viviendas:
            key = str(v.comunidad_oid)
            viviendas_por_com.setdefault(key, []).append(v)
        return render_template('main/dashboard_superadmin.html',
                               comunidades=comunidades,
                               viviendas_por_com=viviendas_por_com,
                               total_viviendas=len(todas_viviendas),
                               total_usuarios=srp.num_objs(Usuario),
                               total_comunidades=len(comunidades))

    # ── Usuario normal ──────────────────────────────────────────────
    from sirope import OID
    usr_str = str(current_user.__oid__)

    accesos = [a for a in srp.load_all(AccesoVivienda) if str(a.usuario_oid) == usr_str]
    todos_cierres  = list(srp.load_all(CierreMensual))
    todas_baterias = list(srp.load_all(Bateria))

    # Cache de comunidades ya cargadas
    com_cache = {}

    viviendas_data = []
    ahorro_global  = 0.0

    for a in accesos:
        try:
            viv = srp.load(OID.from_text(a.vivienda_oid))
            if not viv:
                continue

            # Comunidad de esta vivienda
            com_str = str(viv.comunidad_oid)
            if com_str not in com_cache:
                try:
                    com = srp.load(OID.from_text(com_str))
                    com_cache[com_str] = com
                except Exception:
                    com_cache[com_str] = None
            com = com_cache[com_str]

            # Batería de la comunidad
            bat = next((b for b in todas_baterias if str(b.comunidad_oid) == com_str), None)
            bat_pct = None
            if bat:
                bat_pct = min(round(bat.capacidad_util_actual_kwh
                                    / bat.capacidad_nominal_kwh * 100), 100)

            # Cierres de esta vivienda
            viv_str = str(viv.__oid__)
            cierres = sorted(
                [c for c in todos_cierres if str(c.vivienda_oid) == viv_str],
                key=lambda c: c.mes
            )

            ahorro_total = round(sum(c.ahorro_eur for c in cierres), 2)
            ahorro_global += ahorro_total

            if cierres:
                ult = cierres[-1]
                ultimo_ahorro = round(ult.ahorro_eur, 2)
                ultimo_pct    = round(
                    (ult.ahorro_eur / ult.factura_escenario_base_eur * 100)
                    if ult.factura_escenario_base_eur else 0, 1)
                ultimo_mes = ult.mes
                # Gráfica ahorro mensual (últimos 6)
                ultimos = cierres[-6:]
                chart_ahorro = json.dumps({
                    'labels': [c.mes for c in ultimos],
                    'ahorro': [round(c.ahorro_eur, 2) for c in ultimos],
                    'base':   [round(c.factura_escenario_base_eur, 2) for c in ultimos],
                    'real':   [round(c.factura_escenario_real_eur, 2) for c in ultimos],
                })
            else:
                ultimo_ahorro = 0.0
                ultimo_pct    = 0.0
                ultimo_mes    = '—'
                chart_ahorro  = None

            viviendas_data.append({
                'viv':          viv,
                'acceso':       a,
                'safe_oid':     oid_to_safe(viv.__oid__),
                'com':          com,
                'com_safe_oid': oid_to_safe(com.__oid__) if com else None,
                'bat_pct':      bat_pct,
                'ahorro_total': ahorro_total,
                'ultimo_ahorro':ultimo_ahorro,
                'ultimo_pct':   ultimo_pct,
                'ultimo_mes':   ultimo_mes,
                'n_cierres':    len(cierres),
                'chart_ahorro': chart_ahorro,
            })
        except Exception:
            pass

    return render_template('main/dashboard_usuario.html',
                           viviendas_data=viviendas_data,
                           ahorro_global=round(ahorro_global, 2))
