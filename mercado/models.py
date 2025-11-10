from django.conf import settings
from django.db import models
from django.utils import timezone


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('vehiculos', 'Vehículos'),
        ('inmuebles', 'Inmuebles'),
        ('supermercado', 'Supermercado'),
        ('tecnologia', 'Tecnología'),
        ('hogar_muebles', 'Hogar, Muebles y Jardín'),
        ('electrodomesticos', 'Electrodomésticos'),
        ('herramientas', 'Herramientas'),
        ('construccion', 'Construcción'),
        ('deportes_fitness', 'Deportes y Fitness'),
        ('accesorios_vehiculos', 'Accesorios para Vehículos'),
        ('moda', 'Moda'),
        ('belleza', 'Belleza y Cuidado Personal'),
        ('salud', 'Salud y Equipamiento Médico'),
        ('juguetes', 'Juguetes y Juegos'),
        ('bebes', 'Bebés'),
        ('mascotas', 'Animales y Mascotas'),
        ('libros', 'Libros, Revistas y Comics'),
        ('musica_peliculas', 'Música, Películas y Series'),
        ('instrumentos_musicales', 'Instrumentos Musicales'),
        ('consolas_videojuegos', 'Consolas y Videojuegos'),
        ('camaras_accesorios', 'Cámaras y Accesorios'),
        ('celulares_telefonia', 'Celulares y Telefonía'),
        ('computacion', 'Computación'),
        ('tablets_accesorios', 'Tablets y Accesorios'),
        ('televisores', 'Televisores'),
        ('audio', 'Audio'),
        ('componentes_electronicos', 'Componentes Electrónicos'),
        ('industrias_oficinas', 'Industrias y Oficinas'),
        ('agro', 'Agro'),
        ('arte_libreria', 'Arte, Librería y Mercería'),
        ('antiguedades', 'Antigüedades y Colecciones'),
        ('souvenirs', 'Souvenirs, Cotillón y Fiestas'),
        ('servicios', 'Servicios'),
        ('otros', 'Otros'),
    ]
    
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=200, choices=CATEGORY_CHOICES, blank=False, default="otros")
    description = models.TextField(blank=False, default="")
    marca = models.CharField(max_length=100, blank=True, default="Generico")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=1)
    image = models.ImageField(upload_to="product_images/", blank=True, null=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def is_available(self):
        return self.active and self.stock > 0

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['active', '-created_at']),
            models.Index(fields=['title']),
            models.Index(fields=['marca']),
            models.Index(fields=['active', 'stock']),
        ]
        ordering = ['-created_at']


class ProductImage(models.Model):
    """Imágenes adicionales para productos (además del thumbnail principal)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="product_images/additional/")
    order = models.PositiveIntegerField(default=0, help_text="Orden de aparición (0 = primera)")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Imagen {self.order + 1} de {self.product.title}"

    class Meta:
        ordering = ['order', 'uploaded_at']
        indexes = [
            models.Index(fields=['product', 'order']),
        ]


# Carrito
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now)

    def total(self):
        return sum(item.subtotal() for item in self.items.all())
    
    def is_stale(self, days=30):
        """Verifica si el carrito está abandonado (sin actualizaciones por X días)"""
        from datetime import timedelta

        from django.utils import timezone
        cutoff = timezone.now() - timedelta(days=days)
        return self.updated_at < cutoff

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        if not self.created_at:
            self.created_at = self.updated_at
        return super().save(*args, **kwargs)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    """Orden de compra generada tras un pago exitoso."""
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_PAID, "Pagado"),
        (STATUS_CANCELLED, "Cancelado"),
        (STATUS_REFUNDED, "Reembolsado"),
    ]
    
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="purchases")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Información de MercadoPago
    payment_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    preference_id = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(max_length=50, blank=True, null=True)
    payment_type = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Orden #{self.id} - {self.buyer} - ${self.total}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['status', '-created_at']),
        ]


class OrderItem(models.Model):
    """Items individuales de una orden."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sales")
    
    # Snapshot de datos del producto al momento de la compra
    product_title = models.CharField(max_length=200)
    product_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    
    def subtotal(self):
        return self.product_price * self.quantity
    
    def __str__(self):
        return f"{self.quantity}x {self.product_title}"
    
    class Meta:
        indexes = [
            models.Index(fields=['order', 'seller']),
            models.Index(fields=['seller', 'order']),
        ]
