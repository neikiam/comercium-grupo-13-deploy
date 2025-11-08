"""
Tests para la capa de servicios del módulo mercado.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Cart, CartItem, Product
from .services import CartService, ProductService

User = get_user_model()


class CartServiceTest(TestCase):
    """Tests para CartService."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.product = Product.objects.create(
            seller=self.user,
            title='Producto Test',
            description='Descripción test',
            price=Decimal('100.00'),
            stock=10,
            active=True
        )
    
    def test_get_or_create_cart(self):
        """Test de obtención o creación de carrito."""
        cart, created = CartService.get_or_create_cart(self.user)
        self.assertTrue(created)
        self.assertEqual(cart.user, self.user)
        cart2, created2 = CartService.get_or_create_cart(self.user)
        self.assertFalse(created2)
        self.assertEqual(cart.id, cart2.id)
    
    def test_add_item_success(self):
        """Test de añadir producto al carrito exitosamente."""
        success, message = CartService.add_item(self.user, self.product, quantity=2)
        self.assertTrue(success)
        self.assertIn("agregado", message.lower())
        
        cart = Cart.objects.get(user=self.user)
        item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(item.quantity, 2)
    
    def test_add_item_insufficient_stock(self):
        """Test de añadir producto con stock insuficiente."""
        success, message = CartService.add_item(self.user, self.product, quantity=20)
        self.assertFalse(success)
        self.assertIn("disponibles", message.lower())
    
    def test_add_item_inactive_product(self):
        """Test de añadir producto inactivo."""
        self.product.active = False
        self.product.save()
        
        success, message = CartService.add_item(self.user, self.product)
        self.assertFalse(success)
        self.assertIn("disponible", message.lower())
    
    def test_increase_quantity_success(self):
        """Test de incrementar cantidad exitosamente."""
        CartService.add_item(self.user, self.product, quantity=1)
        
        success, message = CartService.increase_quantity(self.user, self.product.id)
        self.assertTrue(success)
        
        cart = Cart.objects.get(user=self.user)
        item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(item.quantity, 2)
    
    def test_increase_quantity_exceeds_stock(self):
        """Test de incrementar cantidad excediendo stock."""
        CartService.add_item(self.user, self.product, quantity=10)
        
        success, message = CartService.increase_quantity(self.user, self.product.id)
        self.assertFalse(success)
        self.assertIn("stock", message.lower())
    
    def test_decrease_quantity(self):
        """Test de decrementar cantidad."""
        CartService.add_item(self.user, self.product, quantity=3)
        
        CartService.decrease_quantity(self.user, self.product.id)
        
        cart = Cart.objects.get(user=self.user)
        item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(item.quantity, 2)
    
    def test_decrease_quantity_removes_item(self):
        """Test de decrementar cantidad en 1 elimina el item."""
        CartService.add_item(self.user, self.product, quantity=1)
        
        CartService.decrease_quantity(self.user, self.product.id)
        
        cart = Cart.objects.get(user=self.user)
        exists = CartItem.objects.filter(cart=cart, product=self.product).exists()
        self.assertFalse(exists)
    
    def test_remove_item(self):
        """Test de eliminar producto del carrito."""
        CartService.add_item(self.user, self.product, quantity=5)
        
        success, message = CartService.remove_item(self.user, self.product.id)
        self.assertTrue(success)
        
        cart = Cart.objects.get(user=self.user)
        exists = CartItem.objects.filter(cart=cart, product=self.product).exists()
        self.assertFalse(exists)
    
    def test_validate_cart_for_checkout_empty(self):
        """Test de validación de carrito vacío."""
        cart, _ = CartService.get_or_create_cart(self.user)
        
        is_valid, error = CartService.validate_cart_for_checkout(cart)
        self.assertFalse(is_valid)
        self.assertIn("vacío", error.lower())
    
    def test_validate_cart_for_checkout_success(self):
        """Test de validación de carrito exitosa."""
        CartService.add_item(self.user, self.product, quantity=2)
        cart = Cart.objects.get(user=self.user)
        
        is_valid, error = CartService.validate_cart_for_checkout(cart)
        self.assertTrue(is_valid)
        self.assertIsNone(error)


class ProductServiceTest(TestCase):
    """Tests para ProductService."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.user = User.objects.create_user(username='seller', password='pass123')
    
    def test_delete_product(self):
        """Test de eliminación de producto."""
        product = Product.objects.create(
            seller=self.user,
            title='Producto a eliminar',
            description='Test',
            price=Decimal('50.00'),
            stock=5
        )
        product_id = product.id
        
        ProductService.delete_product(product)
        
        exists = Product.objects.filter(id=product_id).exists()
        self.assertFalse(exists)
