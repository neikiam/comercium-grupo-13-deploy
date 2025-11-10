"""
Capa de servicios para mercado.
Encapsula la lógica de negocio del carrito y productos.
"""
import logging

from django.contrib import messages
from django.db import transaction

from .models import Cart, CartItem, Product, Order, OrderItem

logger = logging.getLogger(__name__)


class CartService:
    """Servicio para operaciones del carrito de compras."""
    
    @staticmethod
    def get_or_create_cart(user):
        """
        Obtiene o crea el carrito del usuario.
        
        Args:
            user: Usuario autenticado
        
        Returns:
            Tupla (cart, created)
        """
        return Cart.objects.prefetch_related('items__product__seller').get_or_create(user=user)
    
    @staticmethod
    @transaction.atomic
    def add_item(user, product, quantity=1):
        """
        Añade un producto al carrito.
        
        Args:
            user: Usuario autenticado
            product: Instancia de Product
            quantity: Cantidad a añadir (default: 1)
        
        Returns:
            Tupla (success: bool, message: str)
        """
        if not product.is_available():
            logger.warning(f"Intento de añadir producto inactivo {product.id} por usuario {user.id}")
            return False, "Este producto no está disponible."
        
        cart, _ = Cart.objects.get_or_create(user=user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        
        new_qty = quantity if created else item.quantity + quantity
        
        if new_qty > product.stock:
            if created:
                item.delete()
            logger.info(f"Stock insuficiente para producto {product.id}, usuario {user.id}")
            return False, f"Solo hay {product.stock} unidades disponibles."
        
        item.quantity = new_qty
        item.save()
        logger.info(f"Producto {product.id} añadido al carrito de usuario {user.id}")
        return True, "Producto agregado al carrito."
    
    @staticmethod
    @transaction.atomic
    def increase_quantity(user, product_id):
        """
        Incrementa la cantidad de un producto en el carrito.
        
        Args:
            user: Usuario autenticado
            product_id: ID del producto
        
        Returns:
            Tupla (success: bool, message: str)
        """
        cart, _ = Cart.objects.get_or_create(user=user)
        try:
            item = CartItem.objects.get(cart=cart, product_id=product_id)
        except CartItem.DoesNotExist:
            return False, "Producto no encontrado en el carrito."
        
        if item.quantity + 1 > item.product.stock:
            return False, "No hay suficiente stock para aumentar la cantidad."
        
        item.quantity += 1
        item.save()
        logger.info(f"Cantidad incrementada para producto {product_id}, usuario {user.id}")
        return True, "Cantidad actualizada."
    
    @staticmethod
    @transaction.atomic
    def decrease_quantity(user, product_id):
        """
        Decrementa la cantidad de un producto en el carrito.
        
        Args:
            user: Usuario autenticado
            product_id: ID del producto
        
        Returns:
            Tupla (success: bool, message: str)
        """
        cart, _ = Cart.objects.get_or_create(user=user)
        try:
            item = CartItem.objects.get(cart=cart, product_id=product_id)
        except CartItem.DoesNotExist:
            return False, "Producto no encontrado en el carrito."
        
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
            logger.info(f"Cantidad decrementada para producto {product_id}, usuario {user.id}")
            return True, "Cantidad actualizada."
        else:
            item.delete()
            logger.info(f"Producto {product_id} eliminado del carrito de usuario {user.id}")
            return True, "Producto eliminado del carrito."
    
    @staticmethod
    @transaction.atomic
    def remove_item(user, product_id):
        """
        Elimina un producto del carrito.
        
        Args:
            user: Usuario autenticado
            product_id: ID del producto
        
        Returns:
            Tupla (success: bool, message: str)
        """
        cart, _ = Cart.objects.get_or_create(user=user)
        deleted_count = CartItem.objects.filter(cart=cart, product_id=product_id).delete()[0]
        
        if deleted_count > 0:
            logger.info(f"Producto {product_id} eliminado del carrito de usuario {user.id}")
            return True, "Producto eliminado del carrito."
        return False, "Producto no encontrado en el carrito."
    
    @staticmethod
    def validate_cart_for_checkout(cart):
        """
        Valida que el carrito esté listo para checkout.
        
        Args:
            cart: Instancia de Cart
        
        Returns:
            Tupla (is_valid: bool, error_message: str or None)
        """
        if not cart.items.exists():
            return False, "Tu carrito está vacío."
        
        cart_items = cart.items.select_related('product').all()
        
        for item in cart_items:
            if not item.product.active:
                return False, f"El producto '{item.product.title}' ya no está disponible."
            
            if item.quantity > item.product.stock:
                return False, f"Stock insuficiente para '{item.product.title}'. Disponible: {item.product.stock}, solicitado: {item.quantity}."
            
            if not item.product.is_available():
                return False, f"El producto '{item.product.title}' no está disponible en este momento."
        
        return True, None


class ProductService:
    """Servicio para operaciones de productos."""
    
    @staticmethod
    def create_product(user, form_data):
        """
        Crea un nuevo producto.
        
        Args:
            user: Usuario autenticado (vendedor)
            form_data: Form validado de ProductForm
        
        Returns:
            Instancia de Product creado
        """
        product = form_data.save(commit=False)
        product.seller = user
        product.save()
        logger.info(f"Producto {product.id} creado por usuario {user.id}")
        return product
    
    @staticmethod
    def update_product(product, form_data, old_image=None):
        """
        Actualiza un producto existente.
        
        Args:
            product: Instancia de Product
            form_data: Form validado de ProductForm
            old_image: Imagen anterior (para eliminar si cambió)
        
        Returns:
            Instancia de Product actualizado
        """
        # Si hay nueva imagen y había una anterior, eliminar la antigua
        if old_image and form_data.cleaned_data.get('image') and old_image != form_data.cleaned_data['image']:
            try:
                old_image.delete(save=False)
                logger.info(f"Imagen antigua eliminada para producto {product.id}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar imagen antigua de producto {product.id}: {e}")
        
        updated_product = form_data.save()
        logger.info(f"Producto {product.id} actualizado por usuario {product.seller.id}")
        return updated_product
    
    @staticmethod
    def delete_product(product):
        """
        Elimina un producto (las señales manejan limpieza de imagen y cart items).
        
        Args:
            product: Instancia de Product
        """
        product_id = product.id
        seller_id = product.seller.id
        product.delete()
        logger.info(f"Producto {product_id} eliminado por usuario {seller_id}")


class OrderService:
    """Servicio para operaciones de órdenes de compra."""
    
    @staticmethod
    @transaction.atomic
    def create_order_from_cart(cart, payment_id=None, preference_id=None):
        """
        Crea una orden a partir del carrito actual.
        
        Args:
            cart: Instancia de Cart
            payment_id: ID del pago de MercadoPago (opcional)
            preference_id: ID de la preferencia de MercadoPago (opcional)
        
        Returns:
            Instancia de Order creada
        """
        from notifications.services import NotificationService
        
        cart_items = cart.items.select_related('product', 'product__seller').all()
        
        if not cart_items:
            raise ValueError("El carrito está vacío")
        
        # Crear la orden
        order = Order.objects.create(
            buyer=cart.user,
            total=cart.total(),
            status=Order.STATUS_PAID if payment_id else Order.STATUS_PENDING,
            payment_id=payment_id,
            preference_id=preference_id
        )
        
        # Crear items de la orden y reducir stock
        sellers_notified = set()
        
        for cart_item in cart_items:
            product = cart_item.product
            
            # Verificar stock antes de procesar
            if cart_item.quantity > product.stock:
                raise ValueError(f"Stock insuficiente para {product.title}")
            
            # Crear item de orden
            OrderItem.objects.create(
                order=order,
                product=product,
                seller=product.seller,
                product_title=product.title,
                product_price=product.price,
                quantity=cart_item.quantity
            )
            
            # Reducir stock
            product.stock -= cart_item.quantity
            product.save(update_fields=['stock'])
            
            # Notificar vendedor (una vez por vendedor)
            if product.seller.id not in sellers_notified:
                NotificationService.create_sale_notification(product.seller, order)
                sellers_notified.add(product.seller.id)
            
            # Notificaciones de stock
            if product.stock == 0:
                NotificationService.create_sold_out_notification(product)
            elif product.stock <= 5:
                NotificationService.create_low_stock_notification(product)
            
            logger.info(f"Stock reducido para producto {product.id}: {product.stock} restantes")
        
        # Vaciar el carrito
        cart.items.all().delete()
        logger.info(f"Orden {order.id} creada para usuario {cart.user.id} con {len(cart_items)} items")
        
        return order
    
    @staticmethod
    def get_user_purchases(user):
        """Obtiene las órdenes de compra de un usuario."""
        return Order.objects.filter(buyer=user).prefetch_related('items', 'items__product')
    
    @staticmethod
    def get_user_sales(user):
        """Obtiene las ventas de un usuario."""
        return OrderItem.objects.filter(seller=user).select_related('order', 'order__buyer', 'product').order_by('-order__created_at')
    
    @staticmethod
    @transaction.atomic
    def verify_and_process_payment(payment_id, access_token):
        """
        Verifica un pago con MercadoPago y procesa la orden si es válido.
        
        Args:
            payment_id: ID del pago en MercadoPago
            access_token: Access token de MercadoPago
        
        Returns:
            Tupla (success: bool, order: Order or None, message: str)
        """
        import mercadopago
        
        # Verificar si ya existe una orden con este payment_id
        existing_order = Order.objects.filter(payment_id=payment_id).first()
        if existing_order:
            logger.warning(f"Payment ID {payment_id} ya fue procesado (orden #{existing_order.id})")
            return True, existing_order, "Pago ya procesado"
        
        # Consultar el pago a MercadoPago
        sdk = mercadopago.SDK(access_token)
        
        try:
            payment_info = sdk.payment().get(payment_id)
            response = payment_info.get("response", {})
            
            if not response:
                logger.error(f"MercadoPago no devolvió información para payment_id {payment_id}")
                return False, None, "No se pudo verificar el pago"
            
            status = response.get("status")
            
            if status != "approved":
                logger.warning(f"Payment {payment_id} no está aprobado. Estado: {status}")
                return False, None, f"El pago no está aprobado (estado: {status})"
            
            # Extraer información del pago
            external_reference = response.get("external_reference")
            payment_type = response.get("payment_type_id")
            
            logger.info(f"Payment {payment_id} verificado exitosamente. Estado: {status}")
            
            return True, None, "Pago verificado exitosamente"
            
        except Exception as e:
            logger.exception(f"Error al verificar payment {payment_id}: {e}")
            return False, None, f"Error al verificar el pago: {str(e)}"

