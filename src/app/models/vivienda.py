"""Modelo de Vivienda dentro de una comunidad energética."""
from datetime import date


class Vivienda:
    """Representa una vivienda asociada a una comunidad energética.

    Almacena datos técnicos del punto de suministro y, opcionalmente,
    la instalación fotovoltaica propia.
    """

    ORIENTACIONES = ('sur', 'este', 'oeste', 'norte', 'mixta')

    def __init__(self, comunidad_oid, identificador, direccion_completa='',
                 cups='', potencia_contratada_kw=0.0, coeficiente_reparto=0.0,
                 fecha_alta=None, tiene_paneles=False,
                 potencia_pico_paneles_kwp=None, numero_paneles=None,
                 fecha_instalacion_paneles=None, orientacion_paneles=None):
        # FK a Comunidad guardada como string
        self.comunidad_oid = str(comunidad_oid)
        self.identificador = identificador
        self.direccion_completa = direccion_completa
        self.cups = cups
        self.potencia_contratada_kw = float(potencia_contratada_kw)
        self.coeficiente_reparto = float(coeficiente_reparto)
        self.fecha_alta = fecha_alta or date.today().isoformat()
        self.tiene_paneles = bool(tiene_paneles)
        # Campos de paneles: solo relevantes si tiene_paneles=True
        self.potencia_pico_paneles_kwp = (
            float(potencia_pico_paneles_kwp) if potencia_pico_paneles_kwp is not None else None
        )
        self.numero_paneles = int(numero_paneles) if numero_paneles is not None else None
        self.fecha_instalacion_paneles = fecha_instalacion_paneles
        self.orientacion_paneles = orientacion_paneles

    def __repr__(self):
        return f'<Vivienda {self.identificador}>'
