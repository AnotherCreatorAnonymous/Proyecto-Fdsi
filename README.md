# 🔒 SecureAsset-V1

> **Prueba de Concepto** — Sistema de Gestión de Activos de TI  
> Laboratorio de Auditoría de Código y Modelado de Amenazas  
> Fundamentos de Seguridad de la Información · Ingeniería de Sistemas

---

## 📋 Descripción

**SecureAsset-V1** es una aplicación web minimalista construida con **Python 3 + Flask** que permite registrar y visualizar activos de TI (nombre, IP, tipo de dispositivo).

El propósito de esta PoC es ser el objeto de estudio de un ejercicio de **Auditoría de Código Seguro** y **Modelado de Amenazas STRIDE**. El código contiene controles de seguridad explícitamente documentados mediante etiquetas `[SC-N]`, los cuales el equipo auditor debe:

1. Identificar y comprender el control implementado.
2. Evaluar si el control es suficiente o puede mejorarse.
3. Identificar **vulnerabilidades residuales** o **controles ausentes**.
4. Proponer contramedidas adicionales.

---

## 🚀 Ejecución con Docker

### Requisitos previos
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y en ejecución.
- Git (para clonar el repositorio).

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/<tu-usuario>/secureasset-v1.git
cd secureasset-v1

# 2. Construir la imagen Docker
docker build -t secureasset-v1 .

# 3. Ejecutar el contenedor
docker run -d -p 5000:5000 --name secureasset secureasset-v1

# 4. Abrir en el navegador
# http://localhost:5000
```

### Detener y eliminar el contenedor

```bash
docker stop secureasset
docker rm secureasset
```

---

## 🏗️ Estructura del Proyecto

```
secureasset-v1/
├── app.py            # Aplicación Flask principal
├── requirements.txt  # Dependencias Python
├── Dockerfile        # Imagen Docker con controles documentados
├── .dockerignore     # Archivos excluidos de la imagen
└── README.md         # Este archivo
```

---

## 🛡️ Controles de Seguridad Implementados

Los controles están etiquetados en el código fuente como `[SC-N]` para facilitar su rastreo durante la auditoría.

| ID   | Control                              | Amenaza STRIDE mitigada            | Ubicación          |
|------|--------------------------------------|------------------------------------|--------------------|
| SC-1 | Almacenamiento en memoria (no disco) | Information Disclosure             | `app.py` — storage |
| SC-2 | Validación de entradas con regex     | Tampering, XSS almacenado          | `app.py` — validate_asset() |
| SC-3 | Escape de salida con Jinja2          | XSS reflejado y almacenado         | `app.py` — TEMPLATE |
| SC-4 | Límite máximo de activos (200)       | Denial of Service (memoria)        | `app.py` — MAX_ASSETS |
| SC-5 | Content-Security-Policy (meta tag)  | XSS, inyección de scripts          | `app.py` — TEMPLATE |
| SC-6 | Validación `maxlength` en cliente    | Entrada excesiva (primera línea)   | `app.py` — TEMPLATE |
| SC-7 | Headers HTTP de seguridad            | Clickjacking, MIME sniffing        | `app.py` — after_request |
| SC-8 | Imagen base Docker slim              | Superficie de ataque del contenedor| `Dockerfile`       |
| SC-9 | Contenedor ejecuta como non-root     | Escalada de privilegios            | `Dockerfile`       |
| SC-10| Health-check Docker nativo           | Disponibilidad / resiliencia       | `Dockerfile`       |

---

## 🎯 Modelo de Amenazas STRIDE

### Diagrama de flujo de datos

```
[Usuario (Navegador)]
       │  HTTP POST /assets  (nombre, ip, tipo)
       ▼
[Flask App — app.py]
   ├── validate_asset()      → SC-2 (regex, lista blanca)
   ├── render_template_string → SC-3 (Jinja2 auto-escape)
   ├── after_request()       → SC-7 (security headers)
   └── assets[] (memoria)    → SC-1, SC-4
       │
       ▼
[Cliente recibe HTML seguro]
```

### Análisis de amenazas

| Categoría STRIDE | Amenaza Identificada                              | Control Mitigante | Riesgo Residual |
|------------------|---------------------------------------------------|-------------------|-----------------|
| **S**poofing     | Usuario no autenticado puede registrar activos    | ❌ Ninguno        | 🔴 Alto         |
| **T**ampering    | Manipulación de datos vía requests directos       | SC-2              | 🟡 Medio        |
| **R**epudiation  | No hay logging de quién registró cada activo      | ❌ Ninguno        | 🔴 Alto         |
| **I**nformation Disclosure | API `/assets/api` sin autenticación    | ❌ Ninguno        | 🔴 Alto         |
| **D**enial of Service | Flood de registros (hasta límite SC-4)       | SC-4              | 🟡 Medio        |
| **E**levation of Privilege | Contenedor sin root (SC-9)            | SC-9              | 🟢 Bajo         |

### Preguntas de auditoría abiertas (para el equipo)

1. **SC-2**: ¿El regex `[\w\s\-\.]{1,64}` podría permitir algún caracter inesperado? ¿Qué herramienta usarían para fuzzearlo?
2. **SC-5**: ¿Por qué la CSP declarada en `<meta>` es menos efectiva que en un header HTTP `Content-Security-Policy`?
3. **Autenticación ausente**: ¿Qué mecanismo recomendarían agregar para cumplir el principio de menor privilegio?
4. **Logging ausente**: ¿Qué información mínima debe registrarse para no violar el principio de no repudio?
5. **SC-4**: ¿Es el límite de 200 activos suficiente para prevenir DoS? ¿Qué otra capa de control podría añadirse (ej. rate limiting por IP)?
6. **Transport**: La app corre en HTTP. ¿Qué riesgos introduce la ausencia de TLS?

---

## 🔧 Ejecución Local (sin Docker)

```bash
# Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python app.py
```

Abrir `http://localhost:5000` en el navegador.

---

## 📄 Licencia

MIT — Uso exclusivamente educativo.
