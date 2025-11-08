#!/usr/bin/env bash
# exit on error
set -o errexit

# instalar dependencias
pip install -r requirements.txt

# migraciones
python manage.py migrate --noinput

# collectstatic
python manage.py collectstatic --no-input

# (opcional)
# python manage.py createsuperuser --noinput || true
