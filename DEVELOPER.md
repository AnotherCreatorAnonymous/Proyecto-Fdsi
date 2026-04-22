# 📖 Guía para el Desarrollador — SecureAsset-V1

> **Para:** Cualquier desarrollador que clone este repositorio y desee entender
> cómo está construido, qué decisiones de diseño se tomaron y cómo extenderlo.

---

> [!WARNING]
> **Este documento debe mantenerse actualizado.**
> Cada vez que modifiques `app.py`, `Dockerfile` o `requirements.txt`, revisa
> las secciones correspondientes aquí y refleja los cambios. Un documento
> desactualizado es más perjudicial que no tener documentación.
> Añade una entrada al [Historial de cambios](#-historial-de-cambios) con fecha,
> autor y descripción de cada modificación relevante.

---

## Tabla de Contenidos

1. [Visión general del proyecto](#1-visión-general-del-proyecto)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Estructura de archivos](#3-estructura-de-archivos)
4. [Cómo funciona la aplicación](#4-cómo-funciona-la-aplicación)
   - 4.1 [Arranque y configuración inicial](#41-arranque-y-configuración-inicial)
   - 4.2 [Almacenamiento de datos](#42-almacenamiento-de-datos)
   - 4.3 [Validación de entradas](#43-validación-de-entradas)
   - 4.4 [Flujo de una petición completa](#44-flujo-de-una-petición-completa)
5. [Endpoints de la API](#5-endpoints-de-la-api)
6. [Controles de seguridad explicados](#6-controles-de-seguridad-explicados)
7. [La plantilla HTML (frontend)](#7-la-plantilla-html-frontend)
8. [Dockerfile explicado línea a línea](#8-dockerfile-explicado-línea-a-línea)
9. [Cómo ejecutar el proyecto](#9-cómo-ejecutar-el-proyecto)
   - 9.1 [Con Docker (recomendado)](#91-con-docker-recomendado)
   - 9.2 [Sin Docker (desarrollo local)](#92-sin-docker-desarrollo-local)
10. [Cómo extender el proyecto](#10-cómo-extender-el-proyecto)
11. [Decisiones de diseño y sus razones](#11-decisiones-de-diseño-y-sus-razones)
12. [Limitaciones conocidas](#12-limitaciones-conocidas)
13. [Historial de cambios](#-historial-de-cambios)

---

## 1. Visión general del proyecto

**SecureAsset-V1** es una aplicación web de página única (SPA-like) construida
con Python y Flask. Permite registrar y visualizar un inventario básico de
activos de TI (dispositivos de red, servidores, workstations, etc.).

Fue diseñada como **Prueba de Concepto (PoC)** para un laboratorio universitario
de *Fundamentos de Seguridad de la Información*, con el objetivo de ser objeto
de **auditoría de código** y **modelado de amenazas STRIDE**.

El código intencionalmente:
- **Documenta cada control de seguridad** con etiquetas `[SC-N]`.
- **Plantea preguntas abiertas** en comentarios para estimular el análisis crítico.
- **Expone riesgos residuales** de forma transparente.

---

## 2. Stack tecnológico

| Componente | Tecnología | Versión | Razón de elección |
|---|---|---|---|
| Lenguaje | Python | 3.11 | Estable, soporte LTS, amplio ecosistema |
| Framework web | Flask | 3.0.3 | Minimalista, fácil de auditar, sin magia oculta |
| Escape de HTML | MarkupSafe | 2.1.5 | Dependencia de Flask; escape seguro y eficiente |
| Contenerización | Docker | — | Despliegue reproducible sin dependencias en el host |
| Imagen base | python:3.11-slim | — | Imagen oficial mínima; reduce superficie de ataque |

**No se usa ninguna base de datos**. Los datos viven en memoria RAM durante la
ejecución (ver [sección 4.2](#42-almacenamiento-de-datos)).

---

## 3. Estructura de archivos

```
secureasset-v1/
│
├── app.py              ← Toda la lógica de la aplicación (único archivo Python)
├── requirements.txt    ← Dependencias Python (flask + markupsafe)
├── Dockerfile          ← Imagen Docker con controles de seguridad documentados
├── .dockerignore       ← Archivos excluidos al construir la imagen Docker
├── .gitignore          ← Archivos excluidos del repositorio Git
├── README.md           ← Presentación pública del proyecto + modelo STRIDE
└── DEVELOPER.md        ← Este archivo: documentación técnica interna ← ESTÁS AQUÍ
```

> [!NOTE]
> El proyecto es intencionalmente un **único archivo** (`app.py`) para facilitar
> la auditoría completa del código sin saltar entre múltiples módulos.

---

## 4. Cómo funciona la aplicación

### 4.1 Arranque y configuración inicial

```
app.py se ejecuta
      │
      ├─ Importa Flask, re, uuid, datetime, markupsafe
      ├─ Crea la instancia Flask: app = Flask(__name__)
      ├─ Define constantes globales:
      │     assets = []              ← almacén en memoria
      │     VALID_NAME_PATTERN       ← regex para nombres
      │     VALID_IP_PATTERN         ← regex para IPv4
      │     ALLOWED_DEVICE_TYPES     ← lista blanca de tipos
      │     MAX_ASSETS = 200         ← límite anti-DoS
      ├─ Define la cadena TEMPLATE (HTML completo de la UI)
      ├─ Registra las rutas (/, /assets, /assets/api, /health)
      └─ Inicia el servidor en 0.0.0.0:5000
```

El punto de entrada es el bloque `if __name__ == "__main__"` al final del
archivo. Cuando se ejecuta directamente con `python app.py`, Flask levanta su
servidor de desarrollo en el **puerto 5000**, accesible desde cualquier
interfaz de red del host (`0.0.0.0`).

### 4.2 Almacenamiento de datos

```python
assets = []  # Lista global en memoria
```

Cada activo registrado es un diccionario Python con esta estructura:

```python
{
    "id":        "550e8400-e29b-41d4-a716-446655440000",  # UUID v4 único
    "nombre":    "WEB-SERVER-01",
    "ip":        "192.168.1.10",
    "tipo":      "servidor",
    "timestamp": "2026-04-21 20:30:00"                   # Formato ISO local
}
```

**Implicaciones importantes:**
- ⚠ Los datos **no sobreviven a un reinicio** del contenedor o proceso.
- ⚠ En un entorno multi-proceso o multi-hilo, esta lista **no es thread-safe**.
  Flask en desarrollo usa un solo hilo, pero en producción con Gunicorn/uWSGI
  cada worker tendría su propia copia de `assets`.

### 4.3 Validación de entradas

La función `validate_asset()` es el punto central de defensa contra entradas
maliciosas. Se ejecuta **en el servidor** antes de aceptar cualquier dato:

```python
def validate_asset(nombre, ip, tipo) -> str | None:
```

| Campo | Regla de validación | Regex / Lista blanca |
|---|---|---|
| `nombre` | Letras, números, espacios, guiones, puntos. Máx. 64 caracteres | `^[\w\s\-\.]{1,64}$` |
| `ip` | IPv4 válida (0-255 en cada octeto) | Regex de IPv4 completo |
| `tipo` | Solo valores de un conjunto fijo | `{"servidor", "workstation", "router", "switch", "impresora", "otro"}` |

Si algún campo falla, la función devuelve un mensaje de error (`str`).
Si todo es válido, devuelve `None`. La ruta `POST /assets` verifica este
retorno antes de guardar:

```python
error = validate_asset(nombre, ip, tipo)
if error:
    return render_template_string(TEMPLATE, assets=assets, error=error), 400
```

### 4.4 Flujo de una petición completa

```
Usuario llena el formulario y presiona "+ Registrar"
│
▼
Navegador envía HTTP POST /assets
  Content-Type: application/x-www-form-urlencoded
  Body: nombre=WEB-SERVER-01&ip=192.168.1.10&tipo=servidor
│
▼
Flask recibe la petición → ruta create_asset()
  │
  ├─ [SC-4] ¿Se alcanzó MAX_ASSETS? → Si sí: 429 Too Many Requests
  │
  ├─ Extrae campos con request.form.get() y aplica .strip()
  │
  ├─ [SC-2] validate_asset() valida los tres campos
  │     └─ Si falla: renderiza la página con mensaje de error (HTTP 400)
  │
  ├─ Crea el dict del activo con UUID y timestamp
  │
  ├─ assets.append(asset)
  │
  └─ Renderiza la página actualizada (HTTP 201)
        │
        └─ [SC-3] Jinja2 escapa TODAS las variables {{ }} antes de insertarlas en HTML
              │
              └─ [SC-7] after_request() añade headers de seguridad a la respuesta
```

---

## 5. Endpoints de la API

| Método | Ruta | Descripción | Respuesta |
|---|---|---|---|
| `GET` | `/` | Página principal con formulario e inventario | HTML |
| `POST` | `/assets` | Registra un nuevo activo | HTML (201 éxito / 400 validación / 429 límite) |
| `GET` | `/assets/api` | Lista todos los activos en formato JSON | JSON |
| `GET` | `/health` | Health-check para Docker/orquestadores | JSON `{"status": "ok"}` |

### Ejemplo de respuesta `/assets/api`

```json
{
  "total": 2,
  "assets": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "nombre": "WEB-SERVER-01",
      "ip": "192.168.1.10",
      "tipo": "servidor",
      "timestamp": "2026-04-21 20:30:00"
    }
  ]
}
```

> [!WARNING]
> El endpoint `/assets/api` **no requiere autenticación**. Cualquier cliente
> que tenga acceso de red al puerto 5000 puede leer todo el inventario.
> Esto es un riesgo residual documentado (ver README.md — Modelo STRIDE).

---

## 6. Controles de seguridad explicados

Las etiquetas `[SC-N]` en el código corresponden a esta tabla. Cada control
incluye el **"por qué"** detrás de la decisión de implementación.

### [SC-1] Almacenamiento en memoria

**Ubicación:** `app.py`, línea 25 — `assets = []`

**Por qué:** Elimina la superficie de ataque de una base de datos. No hay
credenciales de DB que robar, no hay archivos de base de datos que extraer,
no hay SQL que inyectar. La contrapartida es la no-persistencia.

---

### [SC-2] Validación de entradas con regex

**Ubicación:** `app.py`, líneas 33-44 y función `validate_asset()`

**Por qué:** El principio de *Never Trust User Input*. Aunque el formulario HTML
tiene restricciones (`maxlength`, `<select>`), un atacante puede enviar
peticiones HTTP directamente con `curl` o Burp Suite, saltándose el navegador.
La validación en el servidor es la única fuente de verdad.

```python
# Ejemplo de lo que el regex PERMITE:
"WEB-SERVER-01"    ✅
"Mi Router.Central" ✅

# Ejemplo de lo que el regex BLOQUEA:
"<script>alert(1)</script>"  ❌  (contiene < >)
"server; rm -rf /"           ❌  (contiene ;)
```

---

### [SC-3] Escape de salida con Jinja2/MarkupSafe

**Ubicación:** `app.py`, toda la cadena `TEMPLATE`

**Por qué:** Jinja2 (motor de plantillas de Flask) escapa automáticamente
cualquier variable `{{ variable }}` antes de insertarla en el HTML. Esto
convierte caracteres peligrosos como `<`, `>`, `"`, `'` en sus entidades HTML
equivalentes (`&lt;`, `&gt;`, etc.), neutralizando XSS incluso si SC-2 fallara.

```
Input del usuario:  <script>alert('XSS')</script>
                          │
                    Jinja2 escapa
                          │
Output en HTML:     &lt;script&gt;alert('XSS')&lt;/script&gt;
                    → El navegador lo muestra como texto, no lo ejecuta
```

> [!TIP]
> SC-2 y SC-3 son **controles en capas** (defensa en profundidad). Si uno falla,
> el otro sigue protegiendo. Este es el principio de *Defense in Depth*.

---

### [SC-4] Límite máximo de activos

**Ubicación:** `app.py`, líneas 44 y 361-363

**Por qué:** Sin un límite, un atacante podría enviar miles de peticiones
automáticas, llenando la RAM del servidor hasta causar un crash (DoS).
El límite de 200 retorna HTTP 429 (Too Many Requests) antes de guardar.

---

### [SC-5] Content-Security-Policy

**Ubicación:** `app.py` — `TEMPLATE`, meta tag en `<head>`

**Por qué:** CSP le dice al navegador qué orígenes son confiables para cargar
scripts, estilos e imágenes. La política actual (`default-src 'self'`) solo
permite recursos del mismo origen, bloqueando la carga de scripts externos.

**Limitación:** CSP en `<meta>` es **menos efectiva** que en header HTTP porque:
1. El HTML debe descargarse y parsearse antes de que la CSP entre en vigor.
2. Algunos navegadores antiguos ignoran la CSP en meta tags.
3. No protege contra inyección en el propio documento antes del tag.

---

### [SC-6] Validación maxlength en cliente

**Ubicación:** `app.py` — `TEMPLATE`, atributos `maxlength` de los `<input>`

**Por qué:** Primera línea de defensa para mejorar la UX (el usuario ve el
límite inmediatamente). **No es suficiente por sí sola** porque cualquier
herramienta HTTP puede ignorar los atributos HTML del formulario.

---

### [SC-7] Headers HTTP de seguridad

**Ubicación:** `app.py`, función `add_security_headers()` (decorador `@after_request`)

| Header | Valor | Protege contra |
|---|---|---|
| `X-Frame-Options` | `DENY` | Clickjacking (el sitio no puede cargarse en un `<iframe>`) |
| `X-Content-Type-Options` | `nosniff` | MIME sniffing (el navegador respeta el Content-Type declarado) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Fuga de URL en el header Referer |
| `Server` | `SecureAsset/1.0` | Ofuscación: oculta que es Flask/Werkzeug |

---

### [SC-8] Imagen Docker base slim

**Ubicación:** `Dockerfile`, línea `FROM python:3.11-slim`

**Por qué:** La imagen `slim` es una variante oficial de Python que excluye
herramientas del sistema no necesarias (compiladores, shells adicionales,
utilidades de red). Menos binarios = menos herramientas disponibles para un
atacante que comprometa el contenedor.

---

### [SC-9] Contenedor ejecuta como usuario non-root

**Ubicación:** `Dockerfile` — `RUN useradd ... appuser` y `USER appuser`

**Por qué:** Por defecto, los contenedores Docker corren como `root`. Si un
atacante explota una vulnerabilidad en la app, obtendría acceso root dentro
del contenedor. Con `USER appuser`, el proceso tiene privilegios mínimos,
dificultando la escalada y el escape del contenedor.

---

### [SC-10] Health-check Docker nativo

**Ubicación:** `Dockerfile` — instrucción `HEALTHCHECK`

**Por qué:** Docker (y orquestadores como Kubernetes) usan el health-check
para saber si el contenedor está funcionando. Si el check falla N veces,
el contenedor se marca como `unhealthy` y puede reiniciarse automáticamente.
Mejora la **disponibilidad** del servicio.

---

## 7. La plantilla HTML (frontend)

El frontend completo vive en la constante `TEMPLATE` dentro de `app.py`
(líneas ~51-317). Esta es una cadena Python multilínea que contiene:

```
TEMPLATE
├── <head>
│     ├── CSP meta tag [SC-5]
│     └── CSS inline completo (no depende de CDNs externos)
│           ├── Variables CSS (:root) — sistema de diseño con tokens de color
│           ├── Layout con CSS Grid para el formulario
│           └── Estilos responsivos para móvil (@media)
└── <body>
      ├── <header> — título y badge del laboratorio
      ├── .card — formulario de registro [SC-6]
      └── .card — tabla de inventario
            └── {% for asset in assets %} — loop Jinja2 [SC-3]
```

**¿Por qué no archivos `.html` separados?**
Se usó `render_template_string()` en lugar de archivos de plantilla separados
para mantener el proyecto en un único archivo auditable sin necesidad de un
directorio `templates/`.

---

## 8. Dockerfile explicado línea a línea

```dockerfile
FROM python:3.11-slim
# [SC-8] Imagen oficial mínima: incluye solo Python y sus dependencias esenciales.

RUN useradd --create-home --shell /bin/bash appuser
# [SC-9] Crea un usuario sin privilegios. El proceso de la app correrá como este usuario.

WORKDIR /app
# Establece el directorio de trabajo dentro del contenedor.

COPY requirements.txt .
# Copia solo requirements.txt primero — optimización de caché de Docker.
# Si requirements.txt no cambia, Docker reutiliza la capa de pip install.

RUN pip install --no-cache-dir -r requirements.txt
# Instala dependencias sin guardar caché de pip (reduce el tamaño de la imagen).

COPY app.py .
# Copia el código de la aplicación DESPUÉS de las dependencias (mejor caching).

USER appuser
# [SC-9] Cambia al usuario no-root antes de ejecutar cualquier proceso.

EXPOSE 5000
# Documenta el puerto (no lo abre en el host; eso lo hace -p en docker run).

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1
# [SC-10] Verifica cada 30s que la app responde. Tras 3 fallos → unhealthy.

CMD ["python", "app.py"]
# Comando por defecto al iniciar el contenedor.
```

---

## 9. Cómo ejecutar el proyecto

### 9.1 Con Docker (recomendado)

```bash
# Construir la imagen (solo la primera vez o cuando cambie el código)
docker build -t secureasset-v1 .

# Ejecutar el contenedor en segundo plano
docker run -d -p 5000:5000 --name secureasset secureasset-v1

# Ver logs en tiempo real
docker logs -f secureasset

# Detener y eliminar el contenedor
docker stop secureasset
docker rm secureasset
```

Luego abrir: **http://localhost:5000**

### 9.2 Sin Docker (desarrollo local)

```bash
# 1. Crear entorno virtual (recomendado para aislar dependencias)
python -m venv venv

# 2. Activar el entorno virtual
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
python app.py
```

Luego abrir: **http://localhost:5000**

---

## 10. Cómo extender el proyecto

Si quieres agregar funcionalidades, aquí están los puntos de extensión
más comunes y los pasos para cada uno.

### Agregar un nuevo campo al activo (ej. "Responsable")

1. En el `TEMPLATE`, agregar un `<input>` con `name="responsable"` en el
   formulario y una columna nueva en el `<table>`.
2. En `validate_asset()`, agregar la validación del nuevo campo.
3. En la ruta `POST /assets`, extraer el campo con `request.form.get("responsable", "")`.
4. Añadir el campo al diccionario del activo.
5. **Actualizar este documento** — sección 4.2 y la tabla de endpoint.

### Agregar persistencia con SQLite

1. Agregar `Flask-SQLAlchemy` a `requirements.txt`.
2. Reemplazar la lista `assets = []` por un modelo SQLAlchemy.
3. **Asegurarse de usar consultas parametrizadas** (ORM lo hace por defecto)
   para prevenir SQL Injection.
4. **Actualizar SC-1** en el código y en este documento.

### Agregar autenticación básica

1. Agregar `Flask-Login` o `Flask-HTTPAuth` a `requirements.txt`.
2. Proteger las rutas `POST /assets` y `GET /assets/api` con un decorador.
3. **Actualizar la tabla STRIDE** en `README.md` — la amenaza de Spoofing
   pasaría de riesgo Alto a Medio/Bajo.
4. Documentar el nuevo control como `[SC-11]`.

---

## 11. Decisiones de diseño y sus razones

| Decisión | Alternativa considerada | Razón de la elección |
|---|---|---|
| Un solo archivo `app.py` | Estructura modular con blueprints | Facilita la auditoría completa del código de un vistazo |
| `render_template_string` | Archivos `.html` en `/templates` | Elimina dependencia de directorio externo; todo en un archivo |
| Almacenamiento en memoria | SQLite, Redis | Cero dependencias externas; enfoca el análisis en la lógica de la app |
| Imagen `python:3.11-slim` | `python:3.11-alpine` | Alpine requiere compilar algunas dependencias; slim tiene mejor compatibilidad |
| `debug=False` en producción | `debug=True` para ver errores | `debug=True` expone el Werkzeug Interactive Debugger (RCE si está público) |

---

## 12. Limitaciones conocidas

| Limitación | Impacto | Posible solución |
|---|---|---|
| Sin autenticación en ningún endpoint | Cualquier usuario puede leer y escribir activos | Flask-Login, API keys, OAuth |
| Sin logging / auditoría | No hay registro de quién registró qué (no repudio) | Integrar Python `logging` o un SIEM |
| Sin rate limiting por IP | DoS posible aunque lento (SC-4 mitiga pero no elimina) | Flask-Limiter, nginx rate limit |
| Datos no persisten al reiniciar | Pérdida total del inventario | SQLite, PostgreSQL, Redis |
| CSP en meta tag (no header HTTP) | Protección de CSP reducida | Mover CSP a `add_security_headers()` |
| Sin HTTPS | Tráfico en texto plano (credenciales futuras expuestas) | Nginx reverse proxy con TLS, Certbot |
| `Server` header ofuscado, no eliminado | Información residual de servidor | Eliminar el header completamente |

---

## 🕓 Historial de cambios

> [!IMPORTANT]
> **Agrega una entrada aquí cada vez que hagas un cambio relevante al proyecto.**
> Formato: `| Fecha | Autor | Descripción |`

| Fecha | Autor | Descripción |
|---|---|---|
| 2026-04-21 | Carlos (initial) | Creación inicial del proyecto: `app.py`, `Dockerfile`, `requirements.txt`, `README.md`, `DEVELOPER.md` |

---

*Documento generado para SecureAsset-V1 — Fundamentos de Seguridad de la Información.*
