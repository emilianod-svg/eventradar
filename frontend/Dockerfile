# syntax=docker/dockerfile:1

# --- Etapa de build ---
FROM node:24-alpine AS builder

WORKDIR /build
COPY package.json package-lock.json* ./
# `npm ci` requiere package-lock.json; si todavía no existe (no se pudo
# generar en este entorno sin acceso a npm registry), cae a `npm install`.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .
# VITE_API_URL se resuelve en build-time. Se pasa como build-arg para no
# hornear un valor productivo por defecto.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# --- Etapa final: Nginx sirviendo estáticos ---
FROM nginx:1.27-alpine AS runtime

RUN addgroup -g 1000 eventradar && adduser -D -u 1000 -G eventradar eventradar \
    && rm -rf /usr/share/nginx/html/* \
    && chown -R eventradar:eventradar /var/cache/nginx /var/run /usr/share/nginx/html \
    && touch /var/run/nginx.pid && chown eventradar:eventradar /var/run/nginx.pid

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER eventradar

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
