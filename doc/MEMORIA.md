# EnergyComm — Memoria Técnica

**Asignatura**: Aplicaciones Web (ALS)  
**Autor**: Rodríguez Núñez, Roberto — 53975479E  
**Profesor**: Baltasar García Pérez-Schofield  
**Curso**: 2025/2026 · Universidade de Vigo

---

## Índice

1. [Visión general](#1-visión-general)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Arquitectura](#3-arquitectura)
4. [Modelo de datos](#4-modelo-de-datos)
5. [Roles y permisos](#5-roles-y-permisos)
6. [Integridad referencial](#6-integridad-referencial)
7. [Rutas y endpoints](#7-rutas-y-endpoints)
8. [Interfaz de usuario](#8-interfaz-de-usuario)
9. [AJAX Progressive Enhancement](#9-ajax-progressive-enhancement)
10. [Diseño visual](#10-diseño-visual)
11. [Sistema de notificaciones](#11-sistema-de-notificaciones)
12. [Testing](#12-testing)
13. [Despliegue](#13-despliegue)
14. [Conexión con el TFG](#14-conexión-con-el-tfg)
15. [Estructura del proyecto](#15-estructura-del-proyecto)
16. [Diagramas](#16-diagramas)
17. [Criterios del enunciado — Tabla de cumplimiento](#17-criterios-del-enunciado--tabla-de-cumplimiento)

---

## 1. Visión general

EnergyComm es una plataforma SaaS de gestión de comunidades energéticas. Una comunidad energética es un grupo de viviendas que comparten una batería de almacenamiento y, opcionalmente, instalaciones fotovoltaicas individuales.

La aplicación permite a un superadministrador gestionar comunidades, viviendas, usuarios, baterías, cierres mensuales e incidencias. Los usuarios normales pueden consultar sus viviendas, ver sus cierres mensuales, crear incidencias y gestionar sus notificaciones.

El proyecto es la capa de gestión administrativa del TFG del autor, que implementa un agente de Reinforcement Learning para optimizar el flujo energético entre viviendas. El SaaS gestiona los datos de entrada del agente (viviendas, coeficientes de reparto, batería) y presenta los resultados (CierresMensuales) a través de una interfaz web multi-rol.

---

## 2. Stack tecnológico

| Tecnología | Versión | Rol |
|---|---|---|
| Python | 3.11+ | Lenguaje principal |
| Flask | 3.0.3 | Framework web (patrón Application Factory) |
| Jinja2 | (incluido en Flask) | Motor de plantillas HTML |
| Sirope | 0.3.1 | ORM sobre Redis (persistencia de objetos Python) |
| Redis | 7 | Base de datos (almacén clave-valor) |
| Flask-Login | 0.6.3 | Gestión de sesiones y autenticación |
| Flask-WTF | 1.2.1 | Protección CSRF y formularios |
| WTForms | 3.1.2 | Validación de formularios del lado servidor |
| Werkzeug | ≥ 3.0 | Hashing de contraseñas (PBKDF2) |
| Pico CSS | 2 (CDN) | Framework CSS base |
| Chart.js | 4 (CDN) | Gráficas interactivas (línea, barras, doughnut) |
| Docker | — | Contenerización (Dockerfile + docker-compose) |
| pytest | — | Framework de testing |

### Dependencias (`requirements.txt`)

```
Flask==3.0.3
Flask-Login==0.6.3
Flask-WTF==1.2.1
WTForms==3.1.2
sirope==0.3.1
redis>=5.0.4
python-dotenv==1.0.1
email-validator==2.1.1
Werkzeug>=3.0
```

---

## 3. Arquitectura

### 3.1. Patrón Application Factory

La aplicación se construye con el patrón *Application Factory* en `app/__init__.py`. La función `create_app(config_name)`:

1. Crea la instancia Flask y carga la configuración según el entorno.
2. Conecta con Redis y crea la instancia Sirope (`app.sirope`).
3. Inicializa Flask-Login y Flask-WTF CSRFProtect.
4. Registra funciones globales en Jinja2:
   - `oid_to_safe()` — convierte OIDs de Sirope a formato URL-safe.
   - `csrf_token_hidden()` — genera un campo hidden con el token CSRF.
5. Configura el `user_loader` de Flask-Login (deserializa el OID del usuario desde la sesión).
6. Añade un `context_processor` que inyecta en cada template:
   - `contador_no_leidas()` — cuenta las notificaciones no leídas del usuario actual.
   - `mi_comunidad_nav()` — lista de comunidades del usuario para el navbar.
7. Registra los 10 blueprints.
8. Configura manejadores de error personalizados (401, 403, 404, 500).

Ventajas del patrón: permite crear múltiples instancias con configuración diferente (tests vs producción), evita estado global y facilita la inyección de dependencias.

### 3.2. Blueprints modulares

Un blueprint por entidad o grupo funcional, siguiendo el criterio de un módulo por entidad:

| Blueprint | Prefijo URL | Responsabilidad |
|---|---|---|
| `auth` | `/` | Login, logout, registro, perfil, cambio de contraseña |
| `main` | `/` | Dashboard según rol (superadmin / usuario) |
| `comunidades` | `/comunidades` | CRUD de comunidades |
| `viviendas` | `/viviendas` | CRUD de viviendas |
| `usuarios` | `/usuarios` | Listado, detalle, asignación y borrado de usuarios |
| `accesos` | `/accesos` | CRUD de accesos (relación usuario-vivienda) |
| `baterias` | `/baterias` | CRUD de baterías y cambio de estado |
| `cierres` | `/cierres` | CRUD de cierres mensuales |
| `notificaciones` | `/notificaciones` | Listado, lectura, eliminación y envío de notificaciones |
| `incidencias` | `/incidencias` | CRUD de incidencias y respuestas |

Cada blueprint tiene su propio directorio con `__init__.py`, `routes.py` y, en su caso, `forms.py`.

### 3.3. OIDs URL-safe

Sirope genera OIDs con formato `namespace.Clase@número` (ej: `app.models.comunidad.Comunidad@3`). Los puntos y la arroba no son seguros en parámetros de ruta Flask. Se implementó una conversión bidireccional en `app/helpers.py`:

```python
def oid_to_safe(oid) -> str:
    return str(oid).replace('.', '-dot-').replace('@', '-at-')

def oid_from_safe(safe: str):
    from sirope import OID
    return OID.from_text(safe.replace('-dot-', '.').replace('-at-', '@'))
```

`oid_to_safe` se registra como global Jinja2, permitiendo su uso directo en templates: `{{ oid_to_safe(obj.__oid__) }}`.

---

## 4. Modelo de datos

### 4.1. Entidades (7)

| Entidad | Descripción | Atributos principales |
|---|---|---|
| **Usuario** | Persona registrada en la plataforma | `nombre`, `email`, `password_hash`, `rol_global`, `fecha_registro` |
| **Comunidad** | Agrupación de viviendas con infraestructura compartida | `nombre`, `ubicacion`, `fecha_constitucion`, `estado`, `descripcion` |
| **Vivienda** | Unidad habitacional dentro de una comunidad | `comunidad_oid`, `identificador`, `direccion_completa`, `cups`, `potencia_contratada_kw`, `coeficiente_reparto`, `tiene_paneles`, `potencia_pico_paneles_kwp`, `numero_paneles`, `orientacion_paneles` |
| **Bateria** | Batería de almacenamiento de una comunidad | `comunidad_oid`, `capacidad_nominal_kwh`, `capacidad_util_actual_kwh`, `ciclos_acumulados`, `fabricante`, `modelo`, `estado` |
| **CierreMensual** | Datos energéticos y económicos mensuales por vivienda | `vivienda_oid`, `mes`, `consumo_total_kwh`, `autoconsumo_directo_kwh`, `energia_de_bateria_kwh`, `vertido_a_red_kwh`, `ahorro_eur`, `factura_escenario_base_eur`, `factura_escenario_real_eur`, `coeficiente_reparto_aplicado` |
| **Incidencia** | Reporte de problema o consulta | `vivienda_oid`, `comunidad_oid`, `usuario_oid`, `titulo`, `descripcion`, `tipo`, `estado`, `respuesta_admin` |
| **Notificacion** | Mensaje del sistema para un usuario | `usuario_oid`, `tipo`, `titulo`, `mensaje`, `entidad_relacionada_oid`, `leida` |

### 4.2. Relaciones

| Relación | Cardinalidad | Descripción |
|---|---|---|
| Comunidad → Vivienda | 1:N | Una comunidad tiene muchas viviendas |
| Comunidad → Bateria | 1:0..1 | Una comunidad tiene como máximo una batería |
| Comunidad → Incidencia | 1:N | Una comunidad tiene muchas incidencias |
| **Usuario ↔ Vivienda** | **N:M** | **Relación mediante AccesoVivienda** (`usuario_oid`, `vivienda_oid`, `rol_en_vivienda`, `fecha_incorporacion`). Roles: `titular`, `convivente`, `solo_lectura` |
| Vivienda → CierreMensual | 1:N | Una vivienda tiene muchos cierres mensuales |
| Vivienda → Incidencia | 1:N | Una vivienda puede tener muchas incidencias |
| Usuario → Incidencia | 1:N | Un usuario puede crear muchas incidencias |
| Usuario → Notificacion | 1:N | Un usuario recibe muchas notificaciones |

### 4.3. Almacenamiento en Sirope

Sirope serializa objetos Python como JSON en Redis. No hay esquema fijo ni migraciones: las relaciones se mantienen como strings OID en los atributos de los objetos (ej: `vivienda.comunidad_oid = str(comunidad.__oid__)`). La integridad referencial es responsabilidad del código de la aplicación (ver sección 6).

### 4.4. Diagrama de clases

Ver `doc/ER_Als.png` — diagrama de clases UML con las 7 entidades, la relación asociativa AccesoVivienda, atributos y cardinalidades.

---

## 5. Roles y permisos

### 5.1. Roles globales

El sistema tiene dos roles globales, definidos en `Usuario.rol_global`:

| Rol | Descripción |
|---|---|
| **superadmin** | Administrador total de la plataforma. El primer usuario registrado obtiene este rol automáticamente. |
| **normal** | Usuario estándar con acceso limitado a sus propias viviendas y comunidades. |

### 5.2. Roles en vivienda

Dentro de cada vivienda, un usuario tiene un rol definido en `AccesoVivienda.rol_en_vivienda`:

| Rol | Permisos |
|---|---|
| `titular` | Propietario de la vivienda. No se puede borrar si es el único titular. |
| `convivente` | Residente con acceso de lectura/escritura. |
| `solo_lectura` | Acceso de consulta únicamente. |

### 5.3. Tabla de permisos

| Operación | Superadmin | Usuario normal |
|---|---|---|
| CRUD comunidades | ✅ | ❌ |
| Ver comunidades | ✅ (todas) | Solo las suyas |
| CRUD viviendas | ✅ | ❌ |
| CRUD accesos | ✅ | ❌ |
| CRUD batería | ✅ | ❌ |
| CRUD cierres mensuales | ✅ | ❌ |
| Ver cierres | ✅ | Solo sus viviendas |
| Crear incidencia | ✅ | ✅ (en sus viviendas) |
| Gestionar incidencias (responder, cambiar estado) | ✅ | ❌ |
| Enviar notificaciones | ✅ | ❌ |
| Ver/eliminar notificaciones | ✅ (todas) | Solo las suyas |
| Gestionar usuarios | ✅ | ❌ |
| Panel de administración | ✅ | ❌ (ve dashboard personal) |

### 5.4. Implementación de permisos

- `app/decorators.py`:
  - `@superadmin_required` — aborta 401 si no autenticado, 403 si no es superadmin.
  - `@acceso_vivienda_required(param)` — aborta 403 si el usuario no tiene AccesoVivienda a la vivienda indicada. El superadmin tiene acceso implícito.
- `app/helpers.py`:
  - `usuario_tiene_acceso(srp, usuario_oid, vivienda_oid)` — comprueba si existe un AccesoVivienda para ese par usuario-vivienda.

---

## 6. Integridad referencial

Al no existir claves foráneas nativas en Sirope/Redis, la integridad referencial se implementa manualmente en el código:

### 6.1. Borrados en cascada

| Borrar | Guardia previa | Cascada |
|---|---|---|
| **Comunidad** | Solo superadmin. Confirmación requerida. | Viviendas → (AccesosVivienda + CierresMensuales + Incidencias) → Batería → Notificaciones relacionadas |
| **Vivienda** | Solo superadmin | AccesosVivienda + CierresMensuales + Incidencias de esa vivienda |
| **Usuario** | Falla si es el único titular de alguna vivienda | Borra sus AccesosVivienda |
| **AccesoVivienda** | Falla si es el último titular de la vivienda | Borrado simple |
| **Batería** | Solo superadmin | Borrado simple (comunidad queda sin batería) |
| **CierreMensual** | Solo superadmin | Borrado simple |
| **Notificación** | Propietario o superadmin | Borrado simple |

### 6.2. Funciones de cascada (`app/helpers.py`)

- `cascade_delete_comunidad(srp, comunidad_oid)` — borra comunidad y todo su subárbol.
- `cascade_delete_vivienda(srp, vivienda_oid)` — borra vivienda con accesos, cierres e incidencias.
- `puede_borrar_usuario(srp, usuario_oid)` — devuelve `(True, '')` o `(False, motivo)`.

### 6.3. Recálculo automático de coeficientes

Cuando se añade, edita o elimina una vivienda de una comunidad, se recalculan automáticamente los coeficientes de reparto de todas las viviendas de esa comunidad:

```
coeficiente_i = potencia_contratada_i / suma_potencias_comunidad
```

La función `recalcular_coeficientes(srp, comunidad_oid)` en `app/helpers.py` realiza este cálculo. Si el coeficiente de alguna vivienda cambia, se genera automáticamente una notificación para todos los usuarios con acceso a esa vivienda.

---

## 7. Rutas y endpoints

### 7.1. Autenticación (`auth_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET, POST | `/login` | `login` | Formulario de inicio de sesión |
| GET | `/logout` | `logout` | Cierre de sesión |
| GET, POST | `/registro` | `registro` | Registro de nuevo usuario |
| GET, POST | `/perfil` | `perfil` | Edición del perfil |
| GET, POST | `/cambiar-password` | `cambiar_password` | Cambio de contraseña |

### 7.2. Dashboard (`main_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/` | `index` | Dashboard superadmin (estadísticas globales) o dashboard usuario (sus viviendas y comunidades) |

### 7.3. Comunidades (`comunidades_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/comunidades/` | `lista` | Listado con buscador |
| GET, POST | `/comunidades/nueva` | `nueva` | Crear comunidad |
| GET | `/comunidades/<oid>` | `detalle` | Detalle con viviendas y batería |
| GET, POST | `/comunidades/<oid>/editar` | `editar` | Editar comunidad |
| POST | `/comunidades/<oid>/eliminar` | `eliminar` | Borrado con cascada |

### 7.4. Viviendas (`viviendas_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/viviendas/` | `lista_global` | Listado global con buscador |
| GET | `/viviendas/comunidad/<oid>/` | `lista` | Viviendas de una comunidad |
| GET, POST | `/viviendas/comunidad/<oid>/nueva` | `nueva` | Crear vivienda en comunidad |
| GET | `/viviendas/<oid>` | `detalle` | Detalle con cierres y gráficas |
| GET, POST | `/viviendas/<oid>/editar` | `editar` | Editar vivienda |
| POST | `/viviendas/<oid>/eliminar` | `eliminar` | Borrado con cascada |

### 7.5. Usuarios (`usuarios_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/usuarios/` | `lista` | Listado con buscador y avatar |
| GET | `/usuarios/<oid>` | `detalle` | Detalle con accesos del usuario |
| POST | `/usuarios/<oid>/asignar-vivienda` | `asignar_vivienda` | Asignar vivienda al usuario |
| POST | `/usuarios/<oid>/eliminar` | `eliminar` | Borrar usuario (con guardias) |

### 7.6. Accesos (`accesos_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/accesos/vivienda/<oid>/` | `lista` | Accesos de una vivienda |
| GET, POST | `/accesos/vivienda/<oid>/nuevo` | `nuevo` | Crear acceso |
| GET, POST | `/accesos/<oid>/editar` | `editar` | Editar rol de acceso |
| POST | `/accesos/<oid>/eliminar` | `eliminar` | Borrar acceso (guardia titular) |

### 7.7. Baterías (`baterias_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/baterias/comunidad/<oid>/` | `detalle_comunidad` | Detalle de batería de comunidad |
| GET, POST | `/baterias/comunidad/<oid>/nueva` | `nueva` | Crear batería |
| GET, POST | `/baterias/<oid>/editar` | `editar` | Editar batería |
| POST | `/baterias/<oid>/cambiar-estado` | `cambiar_estado` | Cambiar estado (AJAX) |
| POST | `/baterias/<oid>/eliminar` | `eliminar` | Borrar batería |

### 7.8. Cierres mensuales (`cierres_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/cierres/vivienda/<oid>/` | `lista` | Listado de cierres de una vivienda |
| GET, POST | `/cierres/vivienda/<oid>/nuevo` | `nuevo` | Crear cierre mensual |
| GET | `/cierres/<oid>` | `detalle` | Detalle con gráficas de energía |
| POST | `/cierres/<oid>/eliminar` | `eliminar` | Borrar cierre |

### 7.9. Incidencias (`incidencias_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/incidencias/` | `lista` | Listado de incidencias |
| GET, POST | `/incidencias/nueva` | `nueva` | Crear incidencia |
| GET | `/incidencias/<oid>` | `detalle` | Detalle de incidencia |
| POST | `/incidencias/<oid>/responder` | `responder` | Responder/cambiar estado (superadmin) |
| POST | `/incidencias/<oid>/eliminar` | `eliminar` | Borrar incidencia |

### 7.10. Notificaciones (`notificaciones_bp`)

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/notificaciones/` | `lista` | Listado de notificaciones |
| POST | `/notificaciones/<oid>/leer` | `marcar_leida` | Marcar como leída (AJAX) |
| POST | `/notificaciones/leer-todas` | `marcar_todas_leidas` | Marcar todas como leídas (AJAX) |
| POST | `/notificaciones/<oid>/eliminar` | `eliminar` | Borrar notificación |
| GET, POST | `/notificaciones/nueva` | `nueva` | Enviar notificación (superadmin) |

**Total: 40 endpoints en 10 blueprints.**

---

## 8. Interfaz de usuario

### 8.1. Templates

34 plantillas Jinja2 organizadas por módulo:

| Módulo | Plantillas |
|---|---|
| Base | `base.html`, `_icons.html` |
| auth | `login.html`, `registro.html`, `perfil.html`, `cambiar_password.html` |
| main | `dashboard_superadmin.html`, `dashboard_usuario.html` |
| comunidades | `lista.html`, `form.html`, `detalle.html` |
| viviendas | `lista_global.html`, `lista.html`, `form.html`, `detalle.html` |
| baterias | `detalle.html`, `form.html` |
| cierres | `lista.html`, `form.html`, `detalle.html` |
| accesos | `lista.html`, `form.html` |
| usuarios | `lista.html`, `detalle.html` |
| incidencias | `lista.html`, `form.html`, `detalle.html` |
| notificaciones | `lista.html`, `form.html` |
| errores | `401.html`, `403.html`, `404.html`, `500.html` |

### 8.2. Elementos comunes

- **Navbar sticky** con glassmorphism (`backdrop-filter: blur(12px)`), logo, enlaces de navegación y badge de notificaciones no leídas.
- **Buscador** en todos los listados (campo de texto con botón "Buscar", filtrado en servidor).
- **Iconos de acción** consistentes: editar (lápiz), borrar (papelera), accesos (personas) — con tamaños SVG equilibrados.
- **Toggle switch** animado para el campo "¿Tiene paneles solares?" en el formulario de viviendas.
- **Flash messages** con borde izquierdo coloreado según tipo (success verde, danger rojo, warning ámbar).
- **Páginas de error** personalizadas (401, 403, 404, 500) con diseño coherente.

---

## 9. AJAX Progressive Enhancement

Todos los formularios de borrado y acciones rápidas funcionan en dos modos:

**Sin JavaScript**: POST estándar → el servidor responde con `flash()` + `redirect()`.  
**Con JavaScript**: `ajax.js` intercepta formularios con `data-ajax-action`, envía `fetch()` con la cabecera `X-Requested-With: XMLHttpRequest`, y el servidor devuelve JSON. El DOM se actualiza sin recargar la página.

### 9.1. Detección en servidor

```python
def is_xhr(req=None) -> bool:
    return req.headers.get('X-Requested-With') == 'XMLHttpRequest'
```

### 9.2. CSRF en AJAX

El token CSRF se lee del `<meta name="csrf-token">` del HTML y se incluye automáticamente en el `FormData` de cada petición AJAX. Configuración: `WTF_CSRF_HEADERS = ['X-CSRFToken']`.

### 9.3. Acciones AJAX implementadas

- Borrado de cualquier entidad (elimina el elemento del DOM sin recargar).
- Marcar notificación como leída (actualiza visual de la tarjeta y el badge del navbar).
- Marcar todas las notificaciones como leídas.
- Cambiar estado de batería.

### 9.4. Comportamiento del DOM

- `data-removable` — el elemento más cercano con este atributo se elimina del DOM tras un borrado exitoso.
- `data-ajax-notif="decrement"` — decrementa el contador del badge de notificaciones.
- `data-ajax-mark-all` — marca todas las tarjetas de notificación como leídas visualmente.

---

## 10. Diseño visual

- **Pico CSS 2** como framework base, con tema claro personalizado.
- **Paleta Trade Republic Light**: fondo `#f7f7f7`, superficies `#ffffff`, texto `#0a0a0a`, acento verde `#18a070`, rojo `#d93025`.
- **CSS custom** en `app/static/css/custom.css` con variables CSS para colores, sombras, radios y transiciones.
- **Chart.js 4** (`app/static/js/charts.js`) para gráficas interactivas:
  - `line-ahorro` — evolución del ahorro mensual (área).
  - `bar-compare` — comparación factura base vs factura real (barras agrupadas).
  - `doughnut-mix` — distribución de energía solar/batería/red (doughnut).
  - `bar-community` — ahorro por vivienda en la comunidad (barras horizontales).
  - `line-ahorro-com` — ahorro mensual a nivel de comunidad (línea).

---

## 11. Sistema de notificaciones

### 11.1. Tipos de notificación

| Tipo | Cuándo se genera |
|---|---|
| `cierre_disponible` | Al crear un cierre mensual para una vivienda |
| `cambio_coeficiente` | Al recalcular coeficientes si el valor cambia |
| `bateria_mantenimiento` | Al cambiar el estado de una batería |
| `incidencia` | Al crear o responder una incidencia |
| `general` | Enviada manualmente por el superadmin |

### 11.2. Notificaciones automáticas

- **Cambio de coeficiente**: cuando se añade, edita o elimina una vivienda, la función `recalcular_coeficientes()` compara el coeficiente anterior con el nuevo. Solo genera notificación si el valor realmente cambió.
- **Notificación a comunidad**: la función `notificar_a_comunidad()` envía una notificación a todos los usuarios con acceso a alguna vivienda de esa comunidad.

### 11.3. Envío manual (superadmin)

El superadmin puede enviar notificaciones a:
- Un usuario específico (seleccionable en un dropdown).
- Todos los usuarios del sistema (opción `__todos__`).

El formulario (`NotificacionForm`) valida título (2-120 caracteres) y mensaje (2-1000 caracteres).

### 11.4. Badge en navbar

Un context processor inyecta `contador_no_leidas()` en todos los templates, mostrando un badge numérico en el icono de campana del navbar que se actualiza vía AJAX al marcar notificaciones como leídas.

---

## 12. Testing

### 12.1. Configuración

Los tests usan pytest con una configuración de test dedicada que crea una instancia de Redis limpia (`REDIS_DB=15`) para cada test. Las fixtures en `conftest.py` proporcionan: `app`, `client`, `srp`, `superadmin`, `usuario`, `comunidad`, `vivienda`, `acceso`, `bateria`, `cierre`, `incidencia`, `notificacion`.

### 12.2. Cobertura

**170 tests** organizados en **43 clases** y **11 ficheros**:

| Fichero | Clases | Tests | Qué cubre |
|---|---|---|---|
| `test_auth.py` | 4 | 22 | Login, registro, perfil, cambio de contraseña |
| `test_comunidades.py` | 5 | 18 | CRUD comunidades, listado, detalle |
| `test_viviendas.py` | 5 | 21 | CRUD viviendas, listado, detalle |
| `test_baterias.py` | 1 | 10 | CRUD batería, cambio de estado |
| `test_cierres.py` | 4 | 16 | CRUD cierres, duplicado de mes, detalle |
| `test_accesos.py` | 3 | 6 | Listado, creación y borrado de accesos |
| `test_usuarios.py` | 4 | 13 | Listado, detalle, asignación, borrado |
| `test_incidencias.py` | 5 | 17 | CRUD incidencias, respuestas, permisos |
| `test_notificaciones.py` | 5 | 15 | Lectura, borrado, envío, permisos AJAX |
| `test_helpers.py` | 5 | 12 | OIDs, coeficientes, cascada, permisos |
| `test_main.py` | 2 | 6 | Dashboard, páginas de error |

### 12.3. Tipos de test

- **Tests de ruta**: verifican códigos HTTP (200, 302, 403), contenido de respuesta y redirecciones.
- **Tests de permisos**: comprueban que usuarios sin autorización reciben 403.
- **Tests AJAX**: envían cabecera `X-Requested-With: XMLHttpRequest` y verifican la respuesta JSON.
- **Tests de integridad**: verifican que los borrados en cascada eliminan correctamente los objetos dependientes.
- **Tests de lógica de negocio**: recálculo de coeficientes, guardias de borrado (último titular).

---

## 13. Despliegue

### 13.1. Docker

El proyecto incluye `Dockerfile` y `docker-compose.yml` para despliegue contenerizado:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck: ...

  web:
    build: .
    ports: ["5000:5000"]
    depends_on:
      redis: { condition: service_healthy }
    env_file: .env
    environment:
      REDIS_HOST: redis
```

### 13.2. Variables de entorno

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key` | Clave secreta de Flask |
| `REDIS_HOST` | `localhost` | Host de Redis |
| `REDIS_PORT` | `6379` | Puerto de Redis |
| `REDIS_DB` | `0` | Base de datos de Redis |
| `FLASK_ENV` | `development` | Entorno de Flask |

### 13.3. Primer uso

Al registrar el primer usuario, se le asigna automáticamente el rol `superadmin`:

```python
es_primero = srp.num_objs(Usuario) == 0
rol = 'superadmin' if es_primero else 'normal'
```

---

## 14. Conexión con el TFG

El módulo `CierreMensual` es el punto de integración entre el SaaS y el agente RL del TFG:

- **Entrada del agente**: datos de Vivienda (`potencia_contratada_kw`, `coeficiente_reparto`, paneles) y Bateria (`capacidad_nominal_kwh`, `ciclos_acumulados`).
- **Salida del agente**: los campos del cierre (`consumo_total_kwh`, `autoconsumo_directo_kwh`, `energia_de_bateria_kwh`, `vertido_a_red_kwh`, `ahorro_eur`, `factura_escenario_base_eur`, `factura_escenario_real_eur`).

En el SaaS académico estos datos se introducen manualmente. En el sistema completo del TFG, el agente generaría estos datos automáticamente.

---

## 15. Estructura del proyecto

```
src/
├── app/
│   ├── __init__.py                    # Application Factory
│   ├── decorators.py                  # @superadmin_required, @acceso_vivienda_required
│   ├── helpers.py                     # OIDs, cascadas, coeficientes, notificaciones
│   ├── models/
│   │   ├── usuario.py                 # Usuario (UserMixin)
│   │   ├── comunidad.py               # Comunidad
│   │   ├── vivienda.py                # Vivienda
│   │   ├── acceso.py                  # AccesoVivienda (relación N:M)
│   │   ├── bateria.py                 # Bateria
│   │   ├── cierre.py                  # CierreMensual
│   │   ├── incidencia.py              # Incidencia
│   │   └── notificacion.py            # Notificacion
│   ├── modules/
│   │   ├── auth/                      # Login, registro, perfil
│   │   ├── main/                      # Dashboard
│   │   ├── comunidades/               # CRUD comunidades
│   │   ├── viviendas/                 # CRUD viviendas
│   │   ├── usuarios/                  # Gestión de usuarios
│   │   ├── accesos/                   # CRUD accesos usuario-vivienda
│   │   ├── baterias/                  # CRUD baterías
│   │   ├── cierres/                   # CRUD cierres mensuales
│   │   ├── incidencias/               # CRUD incidencias
│   │   └── notificaciones/            # Notificaciones y envío
│   ├── static/
│   │   ├── css/custom.css             # Design system completo
│   │   └── js/
│   │       ├── ajax.js                # Progressive enhancement AJAX
│   │       └── charts.js              # Gráficas Chart.js 4
│   └── templates/                     # 34 plantillas Jinja2
├── tests/                             # 11 ficheros, 170 tests
├── config.py                          # Configuración por entorno
├── run.py                             # Punto de entrada
├── Dockerfile                         # Imagen Docker
├── docker-compose.yml                 # Orquestación Redis + Web
└── requirements.txt                   # Dependencias Python
```

---

## 16. Diagramas

- `doc/ER_Als.png` — Diagrama de clases UML: 7 entidades con atributos, AccesoVivienda como relación asociativa N:M entre Usuario y Vivienda, y 8 relaciones con cardinalidad.
- `doc/usecases_Als.png` — Diagrama de casos de uso UML: 2 actores (Superadmin y Usuario), 23 casos de uso organizados por color (compartidos, exclusivos superadmin, exclusivos usuario), 7 relaciones `<<include>>` y leyenda.

---

## 17. Criterios del enunciado — Tabla de cumplimiento

| Criterio | Implementación |
|---|---|
| Flask + Jinja2 | ✅ Flask 3.0.3, 34 templates Jinja2 |
| Sirope + Redis | ✅ Sirope 0.3.1, Redis 7 |
| Flask-Login | ✅ Autenticación completa con sesión segura |
| Flask-WTF | ✅ CSRF en todos los formularios (incluido AJAX) |
| Diseño modular | ✅ 10 blueprints, 7 modelos, 1 módulo por entidad |
| Pico CSS | ✅ Pico CSS 2 con design system custom |
| Sin recarga (AJAX) | ✅ `ajax.js` con progressive enhancement para borrados, notificaciones y cambio de estado |
| Robustez | ✅ Páginas de error 401/403/404/500, validación WTForms, guardias de borrado |
| Integridad referencial | ✅ Cascadas implementadas, guardia de último titular |
| Navegable sin volver atrás | ✅ Breadcrumbs y enlaces de navegación en todas las vistas |
| Primer usuario es superadmin | ✅ `auth.registro` comprueba `num_objs(Usuario) == 0` |
| Tests | ✅ 170 tests con pytest cubriendo los 10 módulos |
| Diagramas | ✅ Diagrama de clases y diagrama de casos de uso |
