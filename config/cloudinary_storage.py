"""
Custom Cloudinary storage backend para archivos de media
"""
import cloudinary
import cloudinary.uploader
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from urllib.parse import urljoin


class CloudinaryMediaStorage(Storage):
    """
    Storage personalizado para subir archivos de media a Cloudinary
    """
    
    def _save(self, name, content):
        """
        Guarda el archivo en Cloudinary
        """
        # Determinar la carpeta según el tipo de archivo
        if 'avatars' in name:
            folder = 'avatars'
        elif 'product_images' in name:
            if 'additional' in name:
                folder = 'product_images/additional'
            else:
                folder = 'product_images'
        else:
            folder = 'media'
        
        # Subir a Cloudinary
        upload_result = cloudinary.uploader.upload(
            content,
            folder=folder,
            resource_type='auto'
        )
        
        # Retornar el public_id o la URL
        return upload_result.get('public_id', upload_result.get('secure_url'))
    
    def url(self, name):
        """
        Retorna la URL pública del archivo
        """
        if name.startswith('http'):
            # Ya es una URL completa
            return name
        
        # Generar URL desde Cloudinary
        try:
            return cloudinary.CloudinaryImage(name).build_url()
        except:
            # Si falla, intentar como URL directa
            return name
    
    def exists(self, name):
        """
        Cloudinary maneja duplicados automáticamente
        """
        return False
    
    def delete(self, name):
        """
        Elimina el archivo de Cloudinary
        """
        try:
            if not name.startswith('http'):
                cloudinary.uploader.destroy(name)
        except:
            pass
    
    def size(self, name):
        """
        Retorna el tamaño del archivo
        """
        return 0
