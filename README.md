# EnergyComm

Plataforma SaaS multi-tenant para la gestión de comunidades energéticas. Proyecto académico de la asignatura **Aplicaciones Web (ALS)**, Universidade de Vigo, curso 2025/2026.

## Stack tecnológico

- **Backend**: Python 3.11+, Flask 3.0.3
- **Plantillas**: Jinja2
- **Persistencia**: Sirope 0.3.1 sobre Redis 7
- **Autenticación**: Flask-Login 0.6.3
- **Formularios**: Flask-WTF 1.2.1 / WTForms 3.1.2
- **Frontend**: Pico CSS 2 (CDN, dark theme), Chart.js 4 (CDN)

## Arrancar con Docker

```bash
cd src
docker compose up --build
```

La app estará disponible en `http://localhost:5000`.

Para cargar datos de ejemplo:

```bash
docker compose exec web python seed.py
```

## Arrancar en local (sin Docker)

```bash
cd src
pip install -r requirements.txt
# Asegúrate de tener Redis corriendo en localhost:6379
cp .env.example .env  # editar si es necesario
python run.py
python seed.py        # en otra terminal (o después de arrancar)
```

## Credenciales del seed

| Email | Contraseña | Rol |
|---|---|---|
| roberto@energycomm.es | roberto1234 | Superadmin |
| carmen@vecinos.es | carmen1234 | Admin comunidad (Vigo) |
| ana@vecinos.es | ana1234 | Admin comunidad (Vigo + Santiago) |
| juan@vecinos.es | juan1234 | Usuario normal |

## Estructura de carpetas

```
src/
├── run.py                    # Punto de entrada
├── config.py                 # Configuración por entorno
├── seed.py                   # Datos de ejemplo
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── app/
    ├── __init__.py           # App factory
    ├── helpers.py            # Utilidades: OIDs, cascadas, permisos
    ├── decorators.py         # @superadmin_required, etc.
    ├── models/               # 7 modelos de datos
    ├── modules/              # 9 blueprints Flask
    ├── static/               # CSS y JS
    └── templates/            # Plantillas Jinja2
doc/
├── info.txt
├── MEMORIA.md
└── diagrama_er.png
```

## Autor

Rodríguez Núñez, Roberto — ALS 2025/2026
