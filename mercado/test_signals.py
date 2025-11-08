"""
Tests para las señales del módulo mercado.
"""
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .models import Cart, CartItem, Product

User = get_user_model()


class ProductSignalsTest(TestCase):
    """Tests para señales relacionadas con Product."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
    
    def test_cleanup_cartitems_on_product_delete(self):
        """Test de limpieza de CartItems cuando se elimina un Product."""
        # Crear producto y añadirlo al carrito
        product = Product.objects.create(
            seller=self.user,
            title='Producto Test',
            description='Test',
            price=Decimal('100.00'),
            stock=10
        )
        
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, product=product, quantity=2)
        cart_item_id = cart_item.id
        
        # Eliminar producto
        product.delete()
        
        # Verificar que CartItem fue eliminado
        exists = CartItem.objects.filter(id=cart_item_id).exists()
        self.assertFalse(exists)
    
    def test_cleanup_product_image_on_delete(self):
        """Test de limpieza de imagen cuando se elimina un Product."""
        # Crear una imagen de prueba
        image = Image.new('RGB', (100, 100), color='blue')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        image_file = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_io.read(),
            content_type='image/jpeg'
        )
        
        # Crear producto con imagen
        product = Product.objects.create(
            seller=self.user,
            title='Producto con Imagen',
            description='Test',
            price=Decimal('50.00'),
            stock=5,
            image=image_file
        )
        
        image_path = product.image.path
        
        # Verificar que la imagen existe
        import os
        self.assertTrue(os.path.exists(image_path))
        
        # Eliminar producto
        product.delete()
        
        # Verificar que la imagen fue eliminada
        self.assertFalse(os.path.exists(image_path))
