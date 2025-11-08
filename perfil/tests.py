from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from mercado.models import Product

User = get_user_model()


class ModeratorProductDeletionTests(TestCase):
    """Tests para verificar que staff/superusuarios pueden eliminar cualquier producto."""
    
    def setUp(self):
        self.client = Client()
        # Crear usuarios
        self.regular_user = User.objects.create_user(username='regular', password='pass')
        self.staff_user = User.objects.create_user(username='staff', password='pass', is_staff=True)
        self.superuser = User.objects.create_user(username='super', password='pass', is_superuser=True)
        
        # Crear producto del usuario regular
        self.product = Product.objects.create(
            seller=self.regular_user,
            title='Test Product',
            description='Test description',
            price=100,
            stock=10,
            active=True
        )
    
    def test_regular_user_cannot_delete_others_product(self):
        """Usuario regular no puede eliminar productos ajenos."""
        other_user = User.objects.create_user(username='other', password='pass')
        self.client.login(username='other', password='pass')
        response = self.client.get(reverse('mercado:product-delete', args=[self.product.id]))
        self.assertEqual(response.status_code, 404)
    
    def test_staff_can_view_delete_confirmation(self):
        """Staff puede ver confirmación de eliminación de cualquier producto."""
        self.client.login(username='staff', password='pass')
        response = self.client.get(reverse('mercado:product-delete', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        self.assertTrue(response.context['is_moderator_action'])
    
    def test_superuser_can_view_delete_confirmation(self):
        """Superusuario puede ver confirmación de eliminación."""
        self.client.login(username='super', password='pass')
        response = self.client.get(reverse('mercado:product-delete', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        self.assertTrue(response.context['is_moderator_action'])
    
    def test_staff_can_delete_product(self):
        """Staff puede eliminar productos de otros usuarios."""
        self.client.login(username='staff', password='pass')
        response = self.client.post(reverse('mercado:product-delete', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())
    
    def test_superuser_can_delete_product(self):
        """Superusuario puede eliminar productos."""
        self.client.login(username='super', password='pass')
        response = self.client.post(reverse('mercado:product-delete', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())
    
    def test_owner_can_still_delete_own_product(self):
        """Dueño sigue pudiendo eliminar su propio producto."""
        self.client.login(username='regular', password='pass')
        response = self.client.post(reverse('mercado:product-delete', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())


class ModeratorUserBanTests(TestCase):
    """Tests para verificar que staff/superusuarios pueden banear usuarios."""
    
    def setUp(self):
        self.client = Client()
        self.regular_user = User.objects.create_user(username='regular', password='pass', email='regular@test.com')
        self.staff_user = User.objects.create_user(username='staff', password='pass', is_staff=True)
        self.superuser = User.objects.create_user(username='super', password='pass', is_superuser=True)
        self.other_superuser = User.objects.create_user(username='super2', password='pass', is_superuser=True)
        
        # Crear productos del usuario regular
        self.product1 = Product.objects.create(
            seller=self.regular_user,
            title='Product 1',
            description='Description',
            price=100,
            stock=5,
            active=True
        )
        self.product2 = Product.objects.create(
            seller=self.regular_user,
            title='Product 2',
            description='Description',
            price=200,
            stock=3,
            active=True
        )
    
    def test_regular_user_cannot_access_ban_page(self):
        """Usuario regular no puede acceder a página de baneo."""
        self.client.login(username='regular', password='pass')
        response = self.client.get(reverse('perfil:ban_user_confirm', args=[self.staff_user.id]))
        # Debería redirigir (user_passes_test falla)
        self.assertEqual(response.status_code, 302)
    
    def test_staff_can_view_ban_confirmation(self):
        """Staff puede ver página de confirmación de baneo."""
        self.client.login(username='staff', password='pass')
        response = self.client.get(reverse('perfil:ban_user_confirm', args=[self.regular_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'regular')
        self.assertEqual(response.context['product_count'], 2)
    
    def test_superuser_can_view_ban_confirmation(self):
        """Superusuario puede ver página de confirmación."""
        self.client.login(username='super', password='pass')
        response = self.client.get(reverse('perfil:ban_user_confirm', args=[self.regular_user.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_cannot_ban_self(self):
        """No se puede banear a uno mismo."""
        self.client.login(username='staff', password='pass')
        response = self.client.get(reverse('perfil:ban_user_confirm', args=[self.staff_user.id]))
        self.assertEqual(response.status_code, 302)
    
    def test_staff_cannot_ban_superuser(self):
        """Staff no puede banear a superusuario."""
        self.client.login(username='staff', password='pass')
        response = self.client.get(reverse('perfil:ban_user_confirm', args=[self.superuser.id]))
        self.assertEqual(response.status_code, 302)
    
    def test_superuser_can_ban_staff(self):
        """Superusuario puede banear a staff."""
        self.client.login(username='super', password='pass')
        response = self.client.post(reverse('perfil:ban_user', args=[self.staff_user.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(id=self.staff_user.id).exists())
    
    def test_ban_deletes_user_and_products(self):
        """Banear usuario elimina su cuenta y productos (CASCADE)."""
        self.client.login(username='staff', password='pass')
        user_id = self.regular_user.id
        
        # Verificar que existen antes
        self.assertTrue(User.objects.filter(id=user_id).exists())
        self.assertEqual(Product.objects.filter(seller=self.regular_user).count(), 2)
        
        # Banear
        response = self.client.post(reverse('perfil:ban_user', args=[user_id]))
        self.assertEqual(response.status_code, 302)
        
        # Verificar que se eliminaron
        self.assertFalse(User.objects.filter(id=user_id).exists())
        self.assertEqual(Product.objects.filter(seller_id=user_id).count(), 0)
    
    def test_cannot_ban_via_post_without_confirmation_page(self):
        """Verificar que el endpoint POST requiere permisos correctos."""
        self.client.login(username='regular', password='pass')
        response = self.client.post(reverse('perfil:ban_user', args=[self.staff_user.id]))
        # Debería redirigir (user_passes_test falla)
        self.assertEqual(response.status_code, 302)
        # El usuario staff sigue existiendo
        self.assertTrue(User.objects.filter(id=self.staff_user.id).exists())

