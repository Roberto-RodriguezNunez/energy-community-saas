"""Modelo de Batería de una comunidad energética."""
from datetime import date


class Bateria:
    """Batería compartida de una comunidad energética.

    Cada comunidad puede tener como máximo una batería.
    Registra el estado operativo y la degradación de capacidad.
    """

    ESTADOS = ('operativa', 'mantenimiento', 'averiada', 'retirada')

    def __init__(self, comunidad_oid, capacidad_nominal_kwh,
                 capacidad_util_actual_kwh=None, ciclos_acumulados=0,
                 fecha_instalacion=None, fabricante='', modelo='',
                 estado='operativa'):
        self.comunidad_oid = str(comunidad_oid)
        self.capacidad_nominal_kwh = float(capacidad_nominal_kwh)
        self.capacidad_util_actual_kwh = (
            float(capacidad_util_actual_kwh)
            if capacidad_util_actual_kwh is not None
            else float(capacidad_nominal_kwh)
        )
        self.ciclos_acumulados = int(ciclos_acumulados)
        self.fecha_instalacion = fecha_instalacion or date.today().isoformat()
        self.fabricante = fabricante
        self.modelo = modelo
        self.estado = estado

    @property
    def es_operativa(self) -> bool:
        return self.estado == 'operativa'

    @property
    def porcentaje_degradacion(self) -> float:
        """Porcentaje de degradación respecto a la capacidad nominal."""
        if self.capacidad_nominal_kwh == 0:
            return 0.0
        return round(
            (1 - self.capacidad_util_actual_kwh / self.capacidad_nominal_kwh) * 100, 1
        )

    def __repr__(self):
        return f'<Bateria {self.fabricante} {self.modelo} {self.capacidad_nominal_kwh}kWh>'
