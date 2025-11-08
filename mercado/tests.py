from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .forms import ProductForm
from .models import Cart, CartItem, Product

User = get_user_model()


class ProductModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='seller', password='pass')
        self.product = Product.objects.create(
            seller=self.user,
            title='Test Product',
            price=Decimal('100.00'),
            stock=5,
            active=True
        )

    def test_is_available_with_stock_and_active(self):
        self.assertTrue(self.product.is_available())

    def test_is_available_without_stock(self):
        self.product.stock = 0
        self.product.save()
        self.assertFalse(self.product.is_available())

    def test_is_available_inactive(self):
        self.product.active = False
        self.product.save()
        self.assertFalse(self.product.is_available())

    def test_is_available_no_stock_and_inactive(self):
        self.product.stock = 0
        self.product.active = False
        self.product.save()
        self.assertFalse(self.product.is_available())


class CartModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='pass')
        self.seller = User.objects.create_user(username='seller', password='pass')
        self.product1 = Product.objects.create(
            seller=self.seller,
            title='Product 1',
            price=Decimal('50.00'),
            stock=10
        )
        self.product2 = Product.objects.create(
            seller=self.seller,
            title='Product 2',
            price=Decimal('75.00'),
            stock=5
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_total_empty(self):
        self.assertEqual(self.cart.total(), 0)

    def test_cart_total_single_item(self):
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=2)
        self.assertEqual(self.cart.total(), Decimal('100.00'))

    def test_cart_total_multiple_items(self):
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=2)
        CartItem.objects.create(cart=self.cart, product=self.product2, quantity=1)
        self.assertEqual(self.cart.total(), Decimal('175.00'))

    def test_cartitem_subtotal(self):
        item = CartItem.objects.create(cart=self.cart, product=self.product1, quantity=3)
        self.assertEqual(item.subtotal(), Decimal('150.00'))


class ProductListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pass')
        self.product1 = Product.objects.create(
            seller=self.user,
            title='Apple iPhone',
            category='electronics',
            price=Decimal('999.00'),
            stock=10,
            active=True
        )
        self.product2 = Product.objects.create(
            seller=self.user,
            title='Samsung Galaxy',
            category='electronics',
            price=Decimal('799.00'),
            stock=5,
            active=True
        )
        self.inactive_product = Product.objects.create(
            seller=self.user,
            title='Inactive Product',
            price=Decimal('100.00'),
            stock=1,
            active=False
        )

    def test_product_list_shows_active_products(self):
        response = self.client.get(reverse('mercado:productlist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Apple iPhone')
        self.assertContains(response, 'Samsung Galaxy')
        self.assertNotContains(response, 'Inactive Product')

    def test_product_list_search_by_title(self):
        response = self.client.get(reverse('mercado:productlist') + '?q=iPhone')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Apple iPhone')
        self.assertNotContains(response, 'Samsung Galaxy')

    def test_product_list_filter_by_category(self):
        response = self.client.get(reverse('mercado:productlist') + '?category=electronics')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Apple iPhone')
        self.assertContains(response, 'Samsung Galaxy')

    def test_product_list_order_by_price_asc(self):
        response = self.client.get(reverse('mercado:productlist') + '?order=asc')
        self.assertEqual(response.status_code, 200)
        products = list(response.context['page_obj'])
        self.assertEqual(products[0].title, 'Samsung Galaxy')
        self.assertEqual(products[1].title, 'Apple iPhone')

    def test_product_list_pagination(self):
        for i in range(15):
            Product.objects.create(
                seller=self.user,
                title=f'Product {i}',
                price=Decimal('10.00'),
                stock=1,
                active=True
            )
        response = self.client.get(reverse('mercado:productlist'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['page_obj'].has_next())
        self.assertEqual(len(response.context['page_obj']), 12)


class ProductDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='seller', password='pass')
        self.product = Product.objects.create(
            seller=self.user,
            title='Test Product',
            price=Decimal('100.00'),
            stock=5,
            active=True
        )

    def test_product_detail_view(self):
        response = self.client.get(reverse('mercado:product-detail', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_product_detail_inactive_returns_404(self):
        self.product.active = False
        self.product.save()
        response = self.client.get(reverse('mercado:product-detail', args=[self.product.id]))
        self.assertEqual(response.status_code, 404)


class AddToCartViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='buyer', password='pass')
        self.seller = User.objects.create_user(username='seller', password='pass')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Test Product',
            price=Decimal('100.00'),
            stock=3,
            active=True
        )
        self.client.login(username='buyer', password='pass')

    def test_add_to_cart_creates_cart_and_item(self):
        response = self.client.post(reverse('mercado:add-to-cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        item = cart.items.first()
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.quantity, 1)

    def test_add_to_cart_increases_quantity(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        response = self.client.post(reverse('mercado:add-to-cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        item = cart.items.first()
        self.assertEqual(item.quantity, 2)

    def test_add_to_cart_exceeds_stock(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=3)
        response = self.client.post(reverse('mercado:add-to-cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        item = cart.items.first()
        self.assertEqual(item.quantity, 3)

    def test_add_to_cart_unavailable_product(self):
        self.product.active = False
        self.product.save()
        response = self.client.post(reverse('mercado:add-to-cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Cart.objects.filter(user=self.user).exists())

    def test_add_to_cart_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse('mercado:add-to-cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class CartViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='buyer', password='pass')
        self.seller = User.objects.create_user(username='seller', password='pass')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Test Product',
            price=Decimal('100.00'),
            stock=5
        )
        self.client.login(username='buyer', password='pass')

    def test_view_cart_creates_empty_cart(self):
        response = self.client.get(reverse('mercado:view-cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    def test_view_cart_shows_items(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        response = self.client.get(reverse('mercado:view-cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_cart_increase_quantity(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        response = self.client.post(reverse('mercado:cart-increase', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        item = cart.items.first()
        self.assertEqual(item.quantity, 3)

    def test_cart_increase_exceeds_stock(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=5)
        response = self.client.post(reverse('mercado:cart-increase', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        item = cart.items.first()
        self.assertEqual(item.quantity, 5)

    def test_cart_decrease_quantity(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=3)
        response = self.client.post(reverse('mercado:cart-decrease', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        item = cart.items.first()
        self.assertEqual(item.quantity, 2)

    def test_cart_decrease_removes_item_when_quantity_one(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        response = self.client.post(reverse('mercado:cart-decrease', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(cart.items.count(), 0)

    def test_cart_remove_item(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=5)
        response = self.client.post(reverse('mercado:cart-remove', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(cart.items.count(), 0)


class ProductFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='seller', password='pass')
        self.product = Product.objects.create(
            seller=self.user,
            title='Original Title',
            category='tecnologia',
            description='Original description',
            price=Decimal('100.00'),
            stock=5
        )

    def test_form_title_disabled_when_editing(self):
        """El campo título debe estar deshabilitado al editar"""
        form = ProductForm(instance=self.product)
        self.assertTrue(form.fields['title'].disabled)
        self.assertIn('readonly', form.fields['title'].widget.attrs)

    def test_form_title_enabled_when_creating(self):
        """El campo título debe estar habilitado al crear"""
        form = ProductForm()
        self.assertFalse(form.fields['title'].disabled)

    def test_edit_product_preserves_title(self):
        """El título no debe cambiar al editar un producto"""
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        # Crear una imagen de prueba
        image = Image.new('RGB', (100, 100), color='red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        image_file = SimpleUploadedFile("test.jpg", image_io.read(), content_type="image/jpeg")
        
        # Asignar imagen al producto original
        self.product.image = image_file
        self.product.save()
        
        self.client = Client()
        self.client.login(username='seller', password='pass')
        
        response = self.client.post(
            reverse('mercado:product-edit', args=[self.product.id]),
            {
                'title': 'Attempted New Title',  # Intento de cambiar el título
                'category': 'moda',
                'description': 'Updated description',
                'price': '150.00',
                'stock': '10',
            }
        )
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.title, 'Original Title')  # El título debe permanecer igual
        self.assertEqual(self.product.description, 'Updated description')  # Pero otros campos sí cambian
        self.assertEqual(self.product.price, Decimal('150.00'))
