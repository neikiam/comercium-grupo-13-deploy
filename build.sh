#!/usr/bin/env bash
# exit on error
set -o errexit

# Limpiar cache de Python
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# instalar dependencias
pip install -r requirements.txt

# migraciones
python manage.py migrate --noinput

# configurar sitio para allauth/OAuth
python manage.py setup_site

# collectstatic
python manage.py collectstatic --no-input

# (opcional)
# python manage.py createsuperuser --noinput || true
