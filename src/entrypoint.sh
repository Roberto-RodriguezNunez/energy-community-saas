#!/bin/sh

# En producción (Render) Redis es externo, no hace falta esperar
# En desarrollo (Docker) esperamos al contenedor de Redis
if [ -z "$REDIS_URL" ]; then
  echo "⏳ Esperando Redis local..."
  until python3 -c "import redis; redis.Redis(host='${REDIS_HOST:-redis}', port=${REDIS_PORT:-6379}).ping()" 2>/dev/null; do
    sleep 1
  done
  echo "✅ Redis listo."
fi

# Seed solo si la BD está vacía (idempotente)
python3 seed.py

# Producción: Gunicorn | Desarrollo: Flask dev server
if [ "$FLASK_ENV" = "production" ]; then
  exec gunicorn -w 2 -b 0.0.0.0:${PORT:-5000} --timeout 120 "app:create_app()"
else
  exec python3 run.py
fi
