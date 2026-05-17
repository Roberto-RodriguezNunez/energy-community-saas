"""Modelo de CierreMensual de una vivienda."""
from datetime import datetime


class CierreMensual:
    """Cierre energético mensual de una vivienda.

    Contiene los datos de consumo, generación y ahorro de un mes concreto.
    Es la salida del agente RL del TFG; en esta versión se introduce manualmente.
    El par (vivienda_oid, mes) debe ser único.
    """

    def __init__(self, vivienda_oid, mes, consumo_total_kwh=0.0,
                 autoconsumo_directo_kwh=0.0, energia_de_bateria_kwh=0.0,
                 vertido_a_red_kwh=0.0, ahorro_eur=0.0,
                 factura_escenario_base_eur=0.0, factura_escenario_real_eur=0.0,
                 porcentaje_ahorro_global=0.0, coeficiente_reparto_aplicado=0.0):
        self.vivienda_oid = str(vivienda_oid)
        self.mes = mes  # formato 'YYYY-MM'
        self.consumo_total_kwh = float(consumo_total_kwh)
        self.autoconsumo_directo_kwh = float(autoconsumo_directo_kwh)
        self.energia_de_bateria_kwh = float(energia_de_bateria_kwh)
        self.vertido_a_red_kwh = float(vertido_a_red_kwh)
        self.ahorro_eur = float(ahorro_eur)
        self.factura_escenario_base_eur = float(factura_escenario_base_eur)
        self.factura_escenario_real_eur = float(factura_escenario_real_eur)
        self.porcentaje_ahorro_global = float(porcentaje_ahorro_global)
        self.coeficiente_reparto_aplicado = float(coeficiente_reparto_aplicado)
        self.fecha_creacion = datetime.now().isoformat()

    @property
    def energia_de_red_kwh(self) -> float:
        """Energía consumida de la red eléctrica (resto tras autoconsumo y batería)."""
        return max(0.0, self.consumo_total_kwh
                   - self.autoconsumo_directo_kwh
                   - self.energia_de_bateria_kwh)

    def __repr__(self):
        return f'<CierreMensual {self.mes} v={self.vivienda_oid}>'
