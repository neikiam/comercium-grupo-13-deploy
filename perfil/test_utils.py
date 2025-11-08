"""
Tests para utilidades del módulo perfil.
"""
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from perfil.models import Profile
from perfil.utils import get_user_avatar_url

User = get_user_model()


class AvatarUtilsTest(TestCase):
    """Tests para utilidades de avatares."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.profile = Profile.objects.get(user=self.user)
    
    def test_get_user_avatar_url_without_avatar(self):
        """Test de URL de avatar cuando no hay imagen."""
        url = get_user_avatar_url(self.user)
        
        self.assertIn('ui-avatars.com', url)
        self.assertIn('testuser', url)
        self.assertIn('size=200', url)
    
    def test_get_user_avatar_url_with_custom_size(self):
        """Test de URL de avatar con tamaño personalizado."""
        url = get_user_avatar_url(self.user, size=50)
        
        self.assertIn('size=50', url)
    
    def test_get_user_avatar_url_with_avatar(self):
        """Test de URL de avatar cuando hay imagen."""
        # Crear imagen de prueba
        image = Image.new('RGB', (100, 100), color='red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        image_file = SimpleUploadedFile(
            name='avatar.jpg',
            content=image_io.read(),
            content_type='image/jpeg'
        )
        
        self.profile.avatar = image_file
        self.profile.save()
        
        # Refrescar usuario para obtener el profile actualizado
        self.user.refresh_from_db()
        
        url = get_user_avatar_url(self.user)
        
        self.assertIn('/avatars/', url)
        self.assertNotIn('ui-avatars.com', url)
    
    def test_get_user_avatar_url_none_user(self):
        """Test de URL de avatar con usuario None."""
        url = get_user_avatar_url(None)
        
        self.assertIn('ui-avatars.com', url)
        self.assertIn('Anon', url)
