# ===========================================================================
# Dockerfile — SecureAsset-V1
# Imagen base: python:3.11-slim (imagen oficial mínima, menor superficie de ataque)
# SECURITY CONTROL [SC-8]: Imagen base slim reduce binarios innecesarios.
# PREGUNTA DE AUDITORÍA: ¿Qué ventajas de seguridad tiene usar una imagen
#                        distroless o alpine frente a slim?
# ===========================================================================

FROM python:3.11-slim

# ===========================================================================
# SECURITY CONTROL [SC-9]: Ejecutar la app como usuario no-root.
# AMENAZA MITIGADA: Escalada de privilegios dentro del contenedor.
# Sin este control, un atacante que comprometa la app tendría acceso root
# dentro del contenedor, facilitando escapes o movimientos laterales.
# ===========================================================================
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copiar dependencias primero (optimización de caché de capas)
COPY requirements.txt .

# Instalar dependencias sin caché para reducir tamaño de imagen
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY app.py .

# Cambiar al usuario no-root antes de ejecutar
USER appuser

# Puerto expuesto (documentación; no abre el puerto en el host por sí solo)
EXPOSE 5000

# ===========================================================================
# SECURITY CONTROL [SC-10]: Health-check nativo de Docker.
# Permite que orquestadores (Docker Compose, Kubernetes) detecten si la
# app está disponible y la reinicien si falla.
# ===========================================================================
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Comando de inicio
CMD ["python", "app.py"]
