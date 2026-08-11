# syntax=docker/dockerfile:1

# --- Etapa de build: instala dependencias en un venv aislado ---
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# Copiamos el paquete de la app porque el build backend (setuptools) lo
# necesita para resolver `[tool.setuptools.packages.find]`.
COPY app ./app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# --- Etapa final: imagen liviana de ejecución ---
FROM python:3.11-slim AS runtime

RUN groupadd --gid 1000 eventradar \
    && useradd --uid 1000 --gid eventradar --shell /bin/bash --create-home eventradar

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY app ./app
COPY aerich.ini ./
COPY migrations ./migrations

USER eventradar

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
