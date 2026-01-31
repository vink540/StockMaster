#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py setup
```

## **Solución 3: Revisar los logs de Render** 📋

En el dashboard de Render, ve a **"Logs"** (esto es gratis) y busca errores cuando intentas hacer login. Los errores más comunes son:

1. **Error de CSRF**: Falta `CSRF_TRUSTED_ORIGINS`
2. **Error de base de datos**: No se corrieron las migraciones
3. **Error de sesiones**: Problema con SESSION_ENGINE

## **Solución 4: Variables de entorno**

En Render Dashboard → **Environment**, asegúrate de tener:
```
DATABASE_URL=postgresql://... (esto lo genera Render automáticamente)
SECRET_KEY=tu-clave-secreta-super-larga
DEBUG=False
ALLOWED_HOSTS=tu-app.onrender.com