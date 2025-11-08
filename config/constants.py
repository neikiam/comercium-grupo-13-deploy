"""
Constantes globales del proyecto Comercium.
Centraliza valores mágicos y configuraciones reutilizables.
"""

# Carrito
CART_ABANDONMENT_DAYS = 30  # Días para considerar un carrito abandonado
CART_MAX_QUANTITY_PER_ITEM = 99  # Cantidad máxima por ítem en el carrito

# Productos
PRODUCT_TITLE_MAX_LENGTH = 200
PRODUCT_MARCA_MAX_LENGTH = 100
PRODUCT_IMAGE_MAX_SIZE_MB = 5
PRODUCT_IMAGE_MIN_WIDTH = 100
PRODUCT_IMAGE_MIN_HEIGHT = 100
PRODUCT_IMAGE_MAX_WIDTH = 4000
PRODUCT_IMAGE_MAX_HEIGHT = 4000
PRODUCTS_PER_PAGE = 50

# Imágenes de perfil
AVATAR_MAX_SIZE_MB = 2
AVATAR_ALLOWED_FORMATS = ['JPEG', 'PNG', 'WEBP']

# Chat
CHAT_MESSAGE_MAX_LENGTH = 1000
CHAT_MESSAGES_PER_PAGE = 50
CHAT_MIN_SEARCH_QUERY_LENGTH = 2
CHAT_MAX_SEARCH_RESULTS = 10

# Rate limiting
RATE_LIMIT_CHAT_POST = "10/m"
RATE_LIMIT_CHAT_GET = "60/m"
RATE_LIMIT_SEARCH = "30/m"

# UI Avatars (servicio de avatares por defecto)
DEFAULT_AVATAR_SIZE = 200
DEFAULT_AVATAR_SERVICE_URL = "https://ui-avatars.com/api/"

# Mercado Pago
MP_CURRENCY = "ARS"
MP_AUTO_RETURN = "approved"

# Caché
CACHE_PRODUCT_LIST_SECONDS = 60 * 5  # 5 minutos
