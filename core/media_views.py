"""
Vista para servir archivos media en producción
"""
import os
from django.http import FileResponse, Http404
from django.conf import settings


def serve_media(request, path):
    """
    Sirve archivos media en producción
    """
    # Construir ruta completa
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # Verificar que existe y no es un directorio
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        raise Http404("File not found")
    
    # Verificar que está dentro de MEDIA_ROOT (seguridad)
    if not os.path.abspath(file_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise Http404("Invalid path")
    
    # Servir el archivo
    return FileResponse(open(file_path, 'rb'))
