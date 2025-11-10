import logging
import hmac
import hashlib

import mercadopago
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from PIL import Image

from .forms import ProductForm
from .models import Cart, CartItem, Product, ProductImage, Order, OrderItem
from .services import CartService, ProductService, OrderService
from perfil.models import Profile
from notifications.services import NotificationService

logger = logging.getLogger(__name__)

PRODUCTS_PER_PAGE = 12


def validate_additional_image(image_file):
    if image_file.size > 5 * 1024 * 1024:
        return False, "Una de las imágenes supera los 5MB."
    
    try:
        img = Image.open(image_file)
        img.verify()
        
        allowed_formats = ['JPEG', 'PNG', 'GIF', 'WEBP']
        if img.format not in allowed_formats:
            return False, f"Formato no permitido en una imagen. Use: {', '.join(allowed_formats)}"
        
        max_dimension = 10000
        if img.width > max_dimension or img.height > max_dimension:
            return False, f"Una imagen es demasiado grande (máx: {max_dimension}x{max_dimension}px)"
        
        image_file.seek(0)
        return True, None
    except Exception:
        return False, "Una de las imágenes no es válida o está corrupta."


def product_list(request):
    """
    Lista productos activos con filtrado, búsqueda, ordenamiento y paginación.

    Parámetros GET soportados:
      - category: puede repetirse para múltiples categorías
      - order: recent (default), oldest, price_asc, price_desc
      - q: texto de búsqueda
      - page: número de página
    """
    qs = Product.objects.filter(active=True).select_related('seller').prefetch_related('images')

    categories = request.GET.getlist('category')
    if categories:
        qs = qs.filter(category__in=categories)

    order = request.GET.get('order')
    query = request.GET.get('q')

    if query:
        qs = qs.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(marca__icontains=query) |
            Q(category__icontains=query)
        )

    # Ordenamiento: recent (default), oldest, price_asc, price_desc
    if order == "price_asc":
        qs = qs.order_by('price')
    elif order == "price_desc":
        qs = qs.order_by('-price')
    elif order == "oldest":
        qs = qs.order_by('created_at')
    else:
        qs = qs.order_by('-created_at')

    all_categories = Product.CATEGORY_CHOICES

    get_params = request.GET.copy()
    get_params.pop('page', None)
    base_qs = get_params.urlencode()

    paginator = Paginator(qs, PRODUCTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'product_list.html',
        {
            'page_obj': page_obj,
            'all_categories': all_categories,
            'base_qs': base_qs,
            'search_query': query or '',
            'selected_categories': categories,
            'order': order or 'recent',
        }
    )

def product_detail(request, pk: int):
    """
    Muestra el detalle de un producto específico.
    
    Args:
        request: HttpRequest
        pk: ID del producto
    
    Returns:
        HttpResponse con template de detalle de producto
    """
    product = get_object_or_404(
        Product.objects.prefetch_related('images'),
        pk=pk,
        active=True
    )
    return render(request, "product_detail.html", {"product": product})


@login_required
def product_create(request):
    """
    Permite a usuarios autenticados crear nuevos productos para vender.
    REQUIERE que el usuario tenga MercadoPago conectado en producción.
    
    Args:
        request: HttpRequest (POST con form data o GET para mostrar formulario)
    
    Returns:
        HttpResponse con formulario o redirect a lista de productos
    """
    # Verificar si MercadoPago está conectado (solo en producción)
    profile, created = Profile.objects.get_or_create(user=request.user)
    if not settings.DEBUG and not profile.has_mercadopago_connected:
        messages.error(
            request, 
            "Debes conectar tu cuenta de MercadoPago antes de publicar productos. "
            "Ve a tu perfil → Configurar MercadoPago."
        )
        return redirect("perfil:mercadopago_settings")
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = ProductService.create_product(request.user, form)
            
            additional_images = request.FILES.getlist('additional_images')
            if additional_images:
                for idx, img_file in enumerate(additional_images[:8]):
                    is_valid, error_msg = validate_additional_image(img_file)
                    if not is_valid:
                        messages.warning(request, f"Imagen adicional {idx+1}: {error_msg}")
                        continue
                    
                    ProductImage.objects.create(
                        product=product,
                        image=img_file,
                        order=idx
                    )
            
            messages.success(request, "Producto creado correctamente.")
            return redirect("mercado:productlist")
    else:
        form = ProductForm()
    
    context = {
        "form": form,
        "is_edit": False,
        "mp_connected": profile.has_mercadopago_connected,
        "is_debug": settings.DEBUG,
    }
    return render(request, "product_form.html", context)


@login_required
def product_edit(request, pk):
    """
    Permite editar un producto existente. Solo el vendedor propietario puede editar.
    
    Args:
        request: HttpRequest (POST con form data o GET para mostrar formulario)
        pk: ID del producto a editar
    
    Returns:
        HttpResponse con formulario o redirect a lista de productos
    """
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    old_image = product.image if product.image else None
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            ProductService.update_product(product, form, old_image)
            
            additional_images = request.FILES.getlist('additional_images')
            if additional_images:
                current_max_order = product.images.count()
                for idx, img_file in enumerate(additional_images[:8]):
                    is_valid, error_msg = validate_additional_image(img_file)
                    if not is_valid:
                        messages.warning(request, f"Imagen adicional {idx+1}: {error_msg}")
                        continue
                    
                    ProductImage.objects.create(
                        product=product,
                        image=img_file,
                        order=current_max_order + idx
                    )
            
            messages.success(request, "Producto actualizado correctamente.")
            return redirect("mercado:productlist")
    else:
        form = ProductForm(instance=product)
    
    # Pasar las imágenes existentes al template
    existing_images = product.images.all().order_by('order')
    return render(request, "product_form.html", {
        "form": form, 
        "is_edit": True,
        "product": product,
        "existing_images": existing_images
    })


@login_required
def product_delete(request, pk):
    """
    Elimina un producto. El vendedor propietario o staff/superusuarios pueden eliminarlo.
    
    Args:
        request: HttpRequest (POST para confirmar o GET para mostrar confirmación)
        pk: ID del producto a eliminar
    
    Returns:
        HttpResponse con confirmación o redirect tras eliminación
    """
    # Staff y superusuarios pueden eliminar cualquier producto
    if request.user.is_staff or request.user.is_superuser:
        product = get_object_or_404(Product, pk=pk)
        is_moderator_action = True
    else:
        # Usuarios regulares solo pueden eliminar sus propios productos
        product = get_object_or_404(Product, pk=pk, seller=request.user)
        is_moderator_action = False
    
    if request.method == "POST":
        seller_username = product.seller.username
        ProductService.delete_product(product)
        
        if is_moderator_action:
            logger.warning(f"Moderador {request.user.username} eliminó producto '{product.title}' de usuario {seller_username}")
            messages.success(request, f"Producto '{product.title}' eliminado correctamente (acción de moderador).")
        else:
            messages.success(request, "Producto eliminado correctamente.")
        
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("mercado:productlist")
    
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    return render(request, "product_confirm_delete.html", {
        "product": product, 
        "next_url": next_url,
        "is_moderator_action": is_moderator_action
    })


@login_required
@require_POST
def add_to_cart(request, product_id):
    """
    Añade un producto al carrito del usuario.
    
    Args:
        request: HttpRequest
        product_id: ID del producto a añadir
    
    Returns:
        Redirect a vista del carrito
    """
    product = get_object_or_404(Product, id=product_id)
    success, message = CartService.add_item(request.user, product)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect("mercado:view-cart")


@login_required
def view_cart(request):
    """
    Muestra el carrito de compras del usuario.
    
    Args:
        request: HttpRequest
    
    Returns:
        HttpResponse con template del carrito
    """
    cart, created = CartService.get_or_create_cart(request.user)
    context = {
        "cart": cart,
        "PUBLIC_KEY": getattr(settings, "MERCADOPAGO_PUBLIC_KEY", None),
    }
    return render(request, "cart.html", context)


@login_required
@require_POST
def cart_increase(request, product_id: int):
    """
    Incrementa la cantidad de un producto en el carrito.
    
    Args:
        request: HttpRequest
        product_id: ID del producto
    
    Returns:
        Redirect a vista del carrito
    """
    success, message = CartService.increase_quantity(request.user, product_id)
    
    if not success:
        messages.warning(request, message)
    
    return redirect("mercado:view-cart")


@login_required
@require_POST
def cart_decrease(request, product_id: int):
    """
    Decrementa la cantidad de un producto en el carrito.
    
    Args:
        request: HttpRequest
        product_id: ID del producto
    
    Returns:
        Redirect a vista del carrito
    """
    CartService.decrease_quantity(request.user, product_id)
    return redirect("mercado:view-cart")


@login_required
@require_POST
def cart_remove(request, product_id: int):
    """
    Elimina un producto del carrito.
    
    Args:
        request: HttpRequest
        product_id: ID del producto a eliminar
    
    Returns:
        Redirect a vista del carrito
    """
    CartService.remove_item(request.user, product_id)
    return redirect("mercado:view-cart")


@login_required
def create_preference_cart(request):
    """
    Crea una preferencia de pago para el carrito del usuario.
    En producción, usa MercadoPago Marketplace con split payments.
    En desarrollo, usa credenciales simples de prueba.
    """
    cart, created = CartService.get_or_create_cart(request.user)

    # Validar el carrito
    is_valid, error_message = CartService.validate_cart_for_checkout(cart)
    if not is_valid:
        logger.warning(f"Validación de carrito fallida para usuario {request.user.id}: {error_message}")
        return JsonResponse(
            {"error": "cart_validation_failed", "message": error_message},
            status=400,
        )
    
    cart_items = cart.items.select_related('product__seller__profile').all()
    
    if not settings.DEBUG:
        sellers_without_mp = []
        for item in cart_items:
            seller = item.product.seller
            seller_profile = getattr(seller, 'profile', None)
            if not seller_profile or not seller_profile.has_mercadopago_connected:
                sellers_without_mp.append(seller.username)
        
        if sellers_without_mp:
            sellers_str = ", ".join(sellers_without_mp)
            logger.error(f"Vendedores sin MercadoPago en carrito de usuario {request.user.id}: {sellers_str}")
            return JsonResponse(
                {"error": "seller_mp_missing", 
                 "message": f"Los siguientes vendedores no tienen MercadoPago conectado: {sellers_str}. No es posible procesar el pago."},
                status=400,
            )
    
    # Determinar si usamos marketplace o modo simple
    use_marketplace = not settings.DEBUG and settings.MERCADOPAGO_APP_ID
    
    if use_marketplace:
        return _create_marketplace_preference(request, cart, cart_items)
    else:
        return _create_simple_preference(request, cart, cart_items)


def _create_simple_preference(request, cart, cart_items):
    """Crea preferencia simple para desarrollo (sin split payments)."""
    access_token = getattr(settings, "MERCADOPAGO_ACCESS_TOKEN", None)
    if not access_token:
        logger.error("MERCADOPAGO_ACCESS_TOKEN no configurado")
        return JsonResponse(
            {"error": "payment_unavailable", "message": "Servicio de pago no disponible temporalmente."},
            status=503,
        )
    
    sdk = mercadopago.SDK(access_token)
    
    items = []
    for item in cart_items:
        title = (item.product.title or "Producto").strip()[:120]
        items.append({
            "title": title,
            "quantity": int(item.quantity),
            "unit_price": float(item.product.price),
            "currency_id": "ARS",
        })
    
    base_url = f"{request.scheme}://{request.get_host()}"
    success_url = f"{base_url}/market/pago-exitoso/"
    failure_url = f"{base_url}/market/pago-fallido/"
    
    preference_data = {
        "items": items,
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": failure_url,
        },
        "external_reference": f"user_{request.user.id}",
    }
    
    if not request.get_host().startswith(('localhost', '127.0.0.1')):
        webhook_url = f"{base_url}/market/webhook/"
        preference_data["notification_url"] = webhook_url
    
    logger.info(f"[DEV] Creando preferencia simple para usuario {request.user.id}")
    
    try:
        preference = sdk.preference().create(preference_data)
        response = preference.get("response", {})
        
        if preference.get("status") != 201:
            error_message = response.get("message", "Error desconocido")
            cause = response.get("cause", [])
            logger.error(f"MercadoPago error: {error_message}, cause: {cause}")
            return JsonResponse(
                {"error": "payment_error", "message": f"Error al crear la preferencia de pago: {error_message}"},
                status=502,
            )
        
        init_point = response.get("init_point")
        if not init_point:
            logger.error(f"MercadoPago no devolvió init_point. Response: {response}")
            return JsonResponse(
                {"error": "payment_error", "message": "No se pudo iniciar el pago. Intenta más tarde."},
                status=502,
            )
        
        logger.info(f"Preferencia simple creada exitosamente para usuario {request.user.id}")
        return JsonResponse({"init_point": init_point})
        
    except Exception as e:
        logger.exception(f"Error al crear preferencia: {e}")
        return JsonResponse(
            {"error": "payment_exception", "message": f"Ocurrió un error al iniciar el pago: {str(e)}"},
            status=502,
        )


def _create_marketplace_preference(request, cart, cart_items):
    """
    Crea preferencia con MercadoPago Marketplace y split payments.
    Cada vendedor recibe su parte directamente en su cuenta.
    """
    access_token = getattr(settings, "MERCADOPAGO_ACCESS_TOKEN", None)
    if not access_token:
        logger.error("MERCADOPAGO_ACCESS_TOKEN no configurado")
        return JsonResponse(
            {"error": "payment_unavailable", "message": "Servicio de pago no disponible temporalmente."},
            status=503,
        )
    
    sdk = mercadopago.SDK(access_token)
    platform_fee_percentage = settings.MERCADOPAGO_PLATFORM_FEE_PERCENTAGE
    
    from collections import defaultdict
    seller_totals = defaultdict(float)
    
    items = []
    for item in cart_items:
        title = (item.product.title or "Producto").strip()[:120]
        unit_price = float(item.product.price)
        quantity = int(item.quantity)
        subtotal = unit_price * quantity
        
        items.append({
            "title": title,
            "quantity": quantity,
            "unit_price": unit_price,
            "currency_id": "ARS",
        })
        
        seller_totals[item.product.seller.id] += subtotal
    
    disbursements = []
    for seller_id, total_amount in seller_totals.items():
        from django.contrib.auth import get_user_model
        User = get_user_model()
        seller = get_object_or_404(User, id=seller_id)
        seller_profile = getattr(seller, 'profile', None)
        
        if not seller_profile:
            logger.error(f"Vendedor {seller.username} sin perfil")
            continue
            
        seller_mp_id = seller_profile.mp_user_id
        
        if not seller_mp_id:
            logger.error(f"Vendedor {seller.username} sin mp_user_id")
            continue
        
        # Calcular comisión de plataforma
        platform_fee = round(total_amount * (platform_fee_percentage / 100), 2)
        seller_amount = round(total_amount - platform_fee, 2)
        
        disbursements.append({
            "collector_id": int(seller_mp_id),
            "amount": seller_amount,
            "application_fee": platform_fee,
            "description": f"Venta de {seller.username}",
        })
    
    base_url = f"{request.scheme}://{request.get_host()}"
    
    preference_data = {
        "items": items,
        "back_urls": {
            "success": f"{base_url}/market/pago-exitoso/",
            "failure": f"{base_url}/market/pago-fallido/",
            "pending": f"{base_url}/market/pago-fallido/",
        },
        "external_reference": f"user_{request.user.id}",
        "marketplace": "Commercium",
        "marketplace_fee": sum(d["application_fee"] for d in disbursements),
        "disbursements": disbursements,
        "notification_url": f"{base_url}/market/webhook/",
    }
    
    logger.info(f"[MARKETPLACE] Creando preferencia con {len(disbursements)} splits para usuario {request.user.id}")
    logger.info(f"Disbursements: {disbursements}")
    
    try:
        preference = sdk.preference().create(preference_data)
        response = preference.get("response", {})
        
        if preference.get("status") != 201:
            error_message = response.get("message", "Error desconocido")
            cause = response.get("cause", [])
            logger.error(f"MercadoPago Marketplace error: {error_message}, cause: {cause}")
            return JsonResponse(
                {"error": "payment_error", "message": f"Error al crear la preferencia de pago: {error_message}"},
                status=502,
            )
        
        init_point = response.get("init_point")
        if not init_point:
            logger.error(f"MercadoPago no devolvió init_point. Response: {response}")
            return JsonResponse(
                {"error": "payment_error", "message": "No se pudo iniciar el pago. Intenta más tarde."},
                status=502,
            )
        
        logger.info(f"Preferencia Marketplace creada exitosamente para usuario {request.user.id}")
        return JsonResponse({"init_point": init_point})
        
    except Exception as e:
        logger.exception(f"Error al crear preferencia Marketplace: {e}")
        return JsonResponse(
            {"error": "payment_exception", "message": f"Ocurrió un error al iniciar el pago: {str(e)}"},
            status=502,
        )


@login_required
def payment_success(request):
    """
    Vista para manejar el retorno exitoso desde MercadoPago.
    Verifica el pago, crea la orden, reduce stock y notifica vendedores.
    
    Args:
        request: HttpRequest con parámetros de pago de MercadoPago
    
    Returns:
        HttpResponse con template de éxito o error
    """
    payment_id = request.GET.get('payment_id')
    status = request.GET.get('status')
    
    if not payment_id:
        messages.error(request, "No se recibió información del pago.")
        return redirect('mercado:view-cart')
    
    # Verificar si ya existe una orden con este payment_id
    existing_order = Order.objects.filter(payment_id=payment_id).first()
    if existing_order:
        logger.info(f"Payment {payment_id} ya fue procesado (orden #{existing_order.id})")
        messages.success(request, "Tu pago ya fue procesado anteriormente.")
        return render(request, "payment_success.html", {"order": existing_order})
    
    # Verificar el pago con MercadoPago
    access_token = getattr(settings, "MERCADOPAGO_ACCESS_TOKEN", None)
    if not access_token:
        logger.error("MERCADOPAGO_ACCESS_TOKEN no configurado al procesar pago")
        messages.error(request, "Error de configuración. Contacta al administrador.")
        return redirect('mercado:view-cart')
    
    try:
        success, order, message = OrderService.verify_and_process_payment(payment_id, access_token)
        
        if not success:
            messages.error(request, f"No se pudo verificar el pago: {message}")
            return redirect('mercado:view-cart')
        
        # Si el pago está verificado, crear la orden desde el carrito
        cart, _ = CartService.get_or_create_cart(request.user)
        
        if not cart.items.exists():
            # El carrito ya fue procesado (por webhook o doble click)
            if order:
                messages.info(request, "Tu orden ya fue procesada.")
                return render(request, "payment_success.html", {"order": order})
            else:
                messages.warning(request, "Tu carrito está vacío.")
                return redirect('mercado:productlist')
        
        # Crear la orden
        with transaction.atomic():
            order = OrderService.create_order_from_cart(
                cart,
                payment_id=payment_id,
                preference_id=request.GET.get('preference_id')
            )
            order.payment_status = status
            order.save(update_fields=['payment_status'])
        
        logger.info(f"Orden {order.id} creada exitosamente para payment {payment_id}")
        messages.success(request, f"¡Pago aprobado! Tu orden #{order.id} ha sido procesada.")
        
        return render(request, "payment_success.html", {"order": order})
        
    except ValueError as e:
        logger.error(f"Error al crear orden desde carrito: {e}")
        messages.error(request, f"Error al procesar tu compra: {str(e)}")
        return redirect('mercado:view-cart')
    except Exception as e:
        logger.exception(f"Error inesperado al procesar payment {payment_id}: {e}")
        messages.error(request, "Ocurrió un error al procesar tu compra. Contacta al administrador.")
        return redirect('mercado:view-cart')


def payment_failure(request):
    """
    Vista para manejar fallo o cancelación del pago desde MercadoPago.
    
    Args:
        request: HttpRequest con parámetros de pago de MercadoPago
    
    Returns:
        HttpResponse con template de fallo
    """
    messages.error(request, "El pago no se pudo completar o fue cancelado.")
    return render(request, "payment_failure.html")


@csrf_exempt
@require_http_methods(["POST"])
def mercadopago_webhook(request):
    """
    Webhook para recibir notificaciones IPN de MercadoPago.
    Este endpoint procesa pagos de forma asíncrona cuando el usuario no regresa al sitio.
    
    Args:
        request: HttpRequest con notificación de MercadoPago
    
    Returns:
        HttpResponse con status 200 o error
    """
    try:
        import json
        
        # MercadoPago envía el tipo de notificación
        topic = request.GET.get('topic') or request.GET.get('type')
        notification_id = request.GET.get('id')
        
        logger.info(f"Webhook recibido: topic={topic}, id={notification_id}")
        
        if topic != 'payment':
            logger.info(f"Webhook ignorado: topic {topic} no es payment")
            return HttpResponse(status=200)
        
        # Obtener información del pago
        access_token = getattr(settings, "MERCADOPAGO_ACCESS_TOKEN", None)
        if not access_token:
            logger.error("MERCADOPAGO_ACCESS_TOKEN no configurado en webhook")
            return HttpResponse(status=500)
        
        sdk = mercadopago.SDK(access_token)
        
        # Si recibimos notification_id, obtener info de la notificación
        if notification_id:
            payment_info = sdk.payment().get(notification_id)
        else:
            logger.warning("Webhook sin notification_id")
            return HttpResponse(status=200)
        
        response = payment_info.get("response", {})
        
        if not response:
            logger.error(f"No se pudo obtener información del pago {notification_id}")
            return HttpResponse(status=200)
        
        payment_id = str(response.get("id"))
        status = response.get("status")
        
        logger.info(f"Webhook payment_id={payment_id}, status={status}")
        
        # Solo procesar pagos aprobados
        if status != "approved":
            logger.info(f"Pago {payment_id} no aprobado (status={status}), no se procesa")
            return HttpResponse(status=200)
        
        # Verificar si ya existe una orden
        existing_order = Order.objects.filter(payment_id=payment_id).first()
        if existing_order:
            logger.info(f"Pago {payment_id} ya fue procesado (orden #{existing_order.id})")
            return HttpResponse(status=200)
        
        external_reference = response.get("external_reference")
       
        logger.info(f"Pago {payment_id} aprobado pero sin carrito asociado en webhook")
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.exception(f"Error en webhook de MercadoPago: {e}")
        return HttpResponse(status=500)


@login_required
@require_POST
def delete_product_image(request, image_id):
    """
    Elimina una imagen adicional de un producto.
    Solo el propietario del producto puede eliminar imágenes.
    
    Args:
        request: HttpRequest (POST)
        image_id: ID de la imagen a eliminar
    
    Returns:
        JsonResponse con resultado
    """
    image = get_object_or_404(ProductImage, pk=image_id)
    
    # Verificar que el usuario sea el propietario del producto
    if image.product.seller != request.user:
        return JsonResponse({"success": False, "error": "No autorizado"}, status=403)
    
    try:
        image.image.delete(save=False)  # Eliminar archivo físico
        image.delete()  # Eliminar registro de BD
        logger.info(f"Imagen {image_id} eliminada de producto {image.product.id} por usuario {request.user.id}")
        return JsonResponse({"success": True})
    except Exception as e:
        logger.error(f"Error al eliminar imagen {image_id}: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def my_purchases(request):
    """Vista para ver el historial de compras del usuario."""
    orders = OrderService.get_user_purchases(request.user)
    return render(request, "my_purchases.html", {"orders": orders})


@login_required
def my_sales(request):
    """Vista para ver el historial de ventas del usuario."""
    sales = OrderService.get_user_sales(request.user).order_by('order_id')  # Ordenar antes de groupby
    
    # Agrupar por orden para mejor visualización
    from itertools import groupby
    sales_by_order = []
    for order_id, items in groupby(sales, key=lambda x: x.order.id):
        items_list = list(items)
        if items_list:  # Validar que no esté vacío
            sales_by_order.append({
                'order': items_list[0].order,
                'items': items_list,
                'total': sum(item.subtotal() for item in items_list)
            })
    
    return render(request, "my_sales.html", {"sales_by_order": sales_by_order})


@login_required
def order_detail(request, order_id):
    """Vista para ver el detalle de una orden."""
    order = get_object_or_404(Order, id=order_id)
    
    # Solo el comprador o los vendedores pueden ver la orden
    is_buyer = order.buyer == request.user
    is_seller = order.items.filter(seller=request.user).exists()
    
    if not (is_buyer or is_seller or request.user.is_staff):
        messages.error(request, "No tienes permiso para ver esta orden.")
        return redirect('mercado:productlist')
    
    # Si es vendedor, solo mostrar sus items
    if is_seller and not is_buyer:
        items = order.items.filter(seller=request.user)
    else:
        items = order.items.all()
    
    return render(request, "order_detail.html", {
        "order": order,
        "items": items,
        "is_buyer": is_buyer,
        "is_seller": is_seller
    })


