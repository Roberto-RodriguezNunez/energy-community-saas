#!/bin/sh
# Esperar a que Redis esté listo (por si acaso)
echo "⏳ Esperando Redis..."
until python3 -c "import redis; redis.Redis(host='redis', port=6379).ping()" 2>/dev/null; do
  sleep 1
done
echo "✅ Redis listo."

# Cargar seed si la BD está vacía (idempotente)
python3 seed.py

# Arrancar Flask
exec python3 run.py
