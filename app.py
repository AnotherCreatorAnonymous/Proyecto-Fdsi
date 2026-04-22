"""
SecureAsset-V1: Sistema de Gestión de Activos de TI
Prueba de Concepto para Laboratorio de Auditoría de Seguridad
Fundamentos de Seguridad de la Información — Ingeniería de Sistemas

PROPÓSITO: Este código implementa controles de seguridad explícitamente
documentados. El objetivo del ejercicio es que el auditor identifique,
evalúe y proponga mejoras a cada control.
"""

from flask import Flask, request, jsonify, render_template_string, abort
from markupsafe import escape  # SECURITY CONTROL [SC-3]: Escape de salida HTML
import re
import uuid
from datetime import datetime

app = Flask(__name__)

# ===========================================================================
# SECURITY CONTROL [SC-1]: Almacenamiento en memoria (sin persistencia)
# AMENAZA MITIGADA: Exposición de datos por acceso directo a base de datos.
# RIESGO RESIDUAL: Los datos se pierden al reiniciar. En producción se
# requeriría una DB con cifrado en reposo y controles de acceso.
# ===========================================================================
assets = []

# ===========================================================================
# SECURITY CONTROL [SC-2]: Validación de entradas con expresiones regulares
# AMENAZA MITIGADA: Inyección de datos maliciosos, XSS almacenado.
# PREGUNTA DE AUDITORÍA: ¿Son estos patrones suficientemente estrictos?
#                        ¿Qué casos borde podrían escapar la validación?
# ===========================================================================
VALID_NAME_PATTERN   = re.compile(r'^[\w\s\-\.]{1,64}$')
VALID_IP_PATTERN     = re.compile(
    r'^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$'
)
ALLOWED_DEVICE_TYPES = {"servidor", "workstation", "router", "switch", "impresora", "otro"}

# ===========================================================================
# SECURITY CONTROL [SC-4]: Límite de activos registrados
# AMENAZA MITIGADA: Denegación de Servicio por agotamiento de memoria (DoS).
# PREGUNTA DE AUDITORÍA: ¿Es 200 un límite adecuado para este contexto?
# ===========================================================================
MAX_ASSETS = 200

# ---------------------------------------------------------------------------
# Plantilla HTML — Jinja2 aplica auto-escape por defecto sobre variables {{ }}
# SECURITY CONTROL [SC-3] en acción: las variables se escapan antes de
# insertarse en el DOM, previniendo XSS reflejado y almacenado.
# ---------------------------------------------------------------------------
TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- SECURITY CONTROL [SC-5]: Content-Security-Policy declarada en meta
         AMENAZA MITIGADA: Ejecución de scripts inline no autorizados.
         PREGUNTA DE AUDITORÍA: ¿Es más efectiva la CSP en header HTTP o aquí?
         ¿Qué limitaciones tiene declararla en un meta tag? -->
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';">
    <title>SecureAsset-V1 | Gestión de Activos de TI</title>
    <style>
        :root {
            --bg:       #0f1117;
            --surface:  #1a1d27;
            --border:   #2d3148;
            --accent:   #6c63ff;
            --accent2:  #00d4aa;
            --danger:   #ff4d6d;
            --text:     #e2e8f0;
            --muted:    #8892a4;
            --radius:   10px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Segoe UI', system-ui, sans-serif;
            min-height: 100vh;
            padding: 2rem 1rem;
        }
        header {
            text-align: center;
            margin-bottom: 2.5rem;
        }
        header h1 {
            font-size: 2rem;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        header p { color: var(--muted); margin-top: .4rem; font-size: .9rem; }
        .badge {
            display: inline-block;
            background: rgba(108,99,255,.15);
            border: 1px solid var(--accent);
            color: var(--accent);
            padding: .2rem .7rem;
            border-radius: 999px;
            font-size: .75rem;
            margin-top: .6rem;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .card h2 {
            font-size: 1rem;
            color: var(--accent2);
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: .05em;
        }
        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr auto;
            gap: .8rem;
            align-items: end;
        }
        label { font-size: .8rem; color: var(--muted); display: block; margin-bottom: .3rem; }
        input, select {
            width: 100%;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text);
            padding: .55rem .8rem;
            font-size: .9rem;
            transition: border-color .2s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: var(--accent);
        }
        button {
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            color: #fff;
            border: none;
            border-radius: 6px;
            padding: .6rem 1.4rem;
            cursor: pointer;
            font-weight: 600;
            font-size: .9rem;
            transition: opacity .2s, transform .1s;
            white-space: nowrap;
        }
        button:hover { opacity: .88; transform: translateY(-1px); }
        .error-msg {
            background: rgba(255,77,109,.12);
            border: 1px solid var(--danger);
            color: var(--danger);
            border-radius: 6px;
            padding: .6rem 1rem;
            margin-top: .8rem;
            font-size: .85rem;
        }
        table { width: 100%; border-collapse: collapse; font-size: .88rem; }
        thead th {
            text-align: left;
            color: var(--muted);
            font-size: .75rem;
            text-transform: uppercase;
            letter-spacing: .05em;
            padding: .5rem .8rem;
            border-bottom: 1px solid var(--border);
        }
        tbody tr { transition: background .15s; }
        tbody tr:hover { background: rgba(108,99,255,.06); }
        td {
            padding: .65rem .8rem;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }
        .pill {
            display: inline-block;
            padding: .15rem .6rem;
            border-radius: 999px;
            font-size: .75rem;
            font-weight: 600;
        }
        .pill-servidor   { background: rgba(108,99,255,.2); color: #a29bfe; }
        .pill-workstation{ background: rgba(0,212,170,.15); color: #00d4aa; }
        .pill-router     { background: rgba(253,203,110,.15); color: #f9ca24; }
        .pill-switch     { background: rgba(116,185,255,.15); color: #74b9ff; }
        .pill-impresora  { background: rgba(255,118,117,.15); color: #ff7675; }
        .pill-otro       { background: rgba(178,190,195,.15); color: #b2bec3; }
        .empty-state {
            text-align: center;
            padding: 2rem;
            color: var(--muted);
            font-size: .9rem;
        }
        .sc-tag {
            font-size: .7rem;
            color: var(--accent2);
            font-family: monospace;
            opacity: .7;
        }
        footer {
            text-align: center;
            margin-top: 3rem;
            color: var(--muted);
            font-size: .8rem;
        }
        @media (max-width: 640px) {
            .form-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>🔒 SecureAsset-V1</h1>
        <p>Sistema de Gestión de Activos de TI &mdash; Prueba de Concepto</p>
        <span class="badge">Laboratorio de Auditoría · Ingeniería de Sistemas</span>
    </header>

    <!-- Formulario de registro de activos -->
    <div class="card">
        <h2>Registrar Nuevo Activo</h2>
        <form id="assetForm" method="POST" action="/assets">
            <!-- SECURITY CONTROL [SC-6]: Los campos tienen maxlength para
                 reforzar el límite en cliente. El servidor valida independientemente.
                 PREGUNTA DE AUDITORÍA: ¿Por qué no es suficiente solo validar en cliente? -->
            <div class="form-grid">
                <div>
                    <label for="nombre">Nombre del dispositivo</label>
                    <input type="text" id="nombre" name="nombre"
                           placeholder="ej. WEB-SERVER-01"
                           maxlength="64" required>
                </div>
                <div>
                    <label for="ip">Dirección IP</label>
                    <input type="text" id="ip" name="ip"
                           placeholder="ej. 192.168.1.10"
                           maxlength="15" required>
                </div>
                <div>
                    <label for="tipo">Tipo de dispositivo</label>
                    <select id="tipo" name="tipo" required>
                        <option value="" disabled selected>Seleccionar...</option>
                        <option value="servidor">Servidor</option>
                        <option value="workstation">Workstation</option>
                        <option value="router">Router</option>
                        <option value="switch">Switch</option>
                        <option value="impresora">Impresora</option>
                        <option value="otro">Otro</option>
                    </select>
                </div>
                <div>
                    <button type="submit" id="btnRegistrar">+ Registrar</button>
                </div>
            </div>
            {% if error %}
            <!-- SC-3: 'error' está escapado por Jinja2 antes de renderizarse -->
            <div class="error-msg" role="alert">⚠ {{ error }}</div>
            {% endif %}
        </form>
    </div>

    <!-- Tabla de activos registrados -->
    <div class="card">
        <h2>Inventario de Activos
            <span class="sc-tag">· [SC-3] Salida escapada · [SC-2] Entradas validadas</span>
        </h2>
        {% if assets %}
        <table id="assetsTable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Nombre</th>
                    <th>Dirección IP</th>
                    <th>Tipo</th>
                    <th>Registrado</th>
                    <th>ID</th>
                </tr>
            </thead>
            <tbody>
            {% for asset in assets %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <!-- SC-3: Todas las variables del usuario se escapan automáticamente -->
                    <td><strong>{{ asset.nombre }}</strong></td>
                    <td><code>{{ asset.ip }}</code></td>
                    <td>
                        <span class="pill pill-{{ asset.tipo }}">
                            {{ asset.tipo | capitalize }}
                        </span>
                    </td>
                    <td>{{ asset.timestamp }}</td>
                    <td><code style="font-size:.7rem; color: var(--muted);">{{ asset.id[:8] }}…</code></td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state">
            📋 No hay activos registrados aún. ¡Agrega el primero!
        </div>
        {% endif %}
    </div>

    <footer>
        SecureAsset-V1 &mdash; PoC para auditoría estudiantil &mdash;
        Fundamentos de Seguridad de la Información
    </footer>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Función auxiliar de validación
# ---------------------------------------------------------------------------
def validate_asset(nombre: str, ip: str, tipo: str) -> str | None:
    """
    Valida los campos del activo. Retorna un mensaje de error si falla,
    o None si todos los campos son válidos.

    SECURITY CONTROL [SC-2] — Validación estricta en el servidor.
    El servidor NUNCA confía en los datos del cliente sin validarlos.
    """
    if not nombre or not VALID_NAME_PATTERN.match(nombre.strip()):
        return "Nombre inválido. Use letras, números, espacios, guiones o puntos (máx. 64 caracteres)."
    if not ip or not VALID_IP_PATTERN.match(ip.strip()):
        return "Dirección IP inválida. Ingrese una IPv4 válida (ej. 192.168.1.10)."
    if tipo not in ALLOWED_DEVICE_TYPES:
        return f"Tipo de dispositivo inválido. Opciones permitidas: {', '.join(sorted(ALLOWED_DEVICE_TYPES))}."
    return None


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Página principal — muestra el formulario y el inventario."""
    return render_template_string(TEMPLATE, assets=assets, error=None)


@app.route("/assets", methods=["POST"])
def create_asset():
    """
    Registra un nuevo activo de TI.

    Controles aplicados en esta ruta:
      [SC-2] Validación de entradas con regex y lista blanca de tipos.
      [SC-4] Límite máximo de activos para prevenir DoS por memoria.
      [SC-3] La salida se escapa en la plantilla Jinja2.
    """
    # SC-4: Verificar límite de capacidad
    if len(assets) >= MAX_ASSETS:
        error = f"Límite de {MAX_ASSETS} activos alcanzado. Contacte al administrador."
        return render_template_string(TEMPLATE, assets=assets, error=error), 429

    nombre = request.form.get("nombre", "").strip()
    ip     = request.form.get("ip", "").strip()
    tipo   = request.form.get("tipo", "").strip().lower()

    # SC-2: Validar todos los campos en el servidor
    error = validate_asset(nombre, ip, tipo)
    if error:
        return render_template_string(TEMPLATE, assets=assets, error=error), 400

    # Crear el registro del activo
    asset = {
        "id":        str(uuid.uuid4()),
        "nombre":    nombre,          # Almacenado limpio; escapado en salida por SC-3
        "ip":        ip,
        "tipo":      tipo,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    assets.append(asset)
    return render_template_string(TEMPLATE, assets=assets, error=None), 201


@app.route("/assets/api", methods=["GET"])
def list_assets_api():
    """
    Endpoint JSON para listar activos — útil para integración con otras herramientas.

    PREGUNTA DE AUDITORÍA: Este endpoint no requiere autenticación.
    ¿Qué información sensible podría exponer? ¿Qué control debería añadirse?
    """
    return jsonify({"total": len(assets), "assets": assets})


@app.route("/health", methods=["GET"])
def health():
    """Endpoint de health-check para Docker y orquestadores."""
    return jsonify({"status": "ok", "assets_count": len(assets)})


# ---------------------------------------------------------------------------
# Cabeceras de seguridad HTTP
# SECURITY CONTROL [SC-7]: Headers de seguridad en cada respuesta.
# AMENAZA MITIGADA: Clickjacking, MIME sniffing, información de servidor.
# PREGUNTA DE AUDITORÍA: ¿Qué headers adicionales recomendaría el equipo?
# ---------------------------------------------------------------------------
@app.after_request
def add_security_headers(response):
    response.headers["X-Frame-Options"]        = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    response.headers["Server"]                 = "SecureAsset/1.0"   # Ofusca tecnología
    return response


if __name__ == "__main__":
    # NOTA: debug=False en producción. El modo debug expone el Werkzeug debugger,
    # que permite ejecución remota de código (RCE) si está activo.
    app.run(host="0.0.0.0", port=5000, debug=False)
