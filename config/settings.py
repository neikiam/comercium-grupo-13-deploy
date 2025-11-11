import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("DEBUG", "False").lower() == "true":
        SECRET_KEY = "dev-secret-key-change-in-production-immediately"
    else:
        raise ValueError("SECRET_KEY must be set in production!")

# En Render, la variable de entorno 'RENDER' está presente. Se usa eso para desactivar DEBUG automáticamente.
DEBUG = 'RENDER' not in os.environ

# Hostname externo provisto por Render (si existe). Caso contrario, desarrollo local.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS = [RENDER_EXTERNAL_HOSTNAME]
else:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# CSRF Trusted Origins: si está en Render, agregamos el hostname automáticamente con https
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS = [f"https://{RENDER_EXTERNAL_HOSTNAME}"]
else:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]

BASICS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

TERCEROS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

PROPIAS = [
    "core",
    "mercado",
    "perfil",
    "user_activity",
    "chat_interno",
    "notifications",
]

INSTALLED_APPS = BASICS + TERCEROS + PROPIAS


SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# Configuración de allauth
ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = ['email', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "none")
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_UNIQUE_EMAIL = True 
ACCOUNT_PASSWORD_INPUT_RENDER_VALUE = False
ACCOUNT_SESSION_REMEMBER = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "none")
SOCIALACCOUNT_QUERY_EMAIL = True

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@comercium.local")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"

SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Middleware

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "user_activity.middleware.AutoLogoutMiddleware",
    "user_activity.middleware.UpdateLastSeenMiddleware",
]


ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "mercado.context_processors.cart",
                "core.context_processors.socialaccount_settings",
                "notifications.context_processors.notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

db_config = dj_database_url.config(default=os.environ.get("DATABASE_URL"), conn_max_age=600)
if db_config:
    DATABASES = {"default": db_config}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {
                "timeout": int(os.getenv("SQLITE_TIMEOUT", "10")),
            },
        }
    }

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
}

MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
MERCADOPAGO_PUBLIC_KEY = os.getenv("MERCADOPAGO_PUBLIC_KEY")

# MercadoPago Marketplace OAuth (para producción)
MERCADOPAGO_APP_ID = os.getenv("MERCADOPAGO_APP_ID")
MERCADOPAGO_CLIENT_SECRET = os.getenv("MERCADOPAGO_CLIENT_SECRET")
MERCADOPAGO_REDIRECT_URI = os.getenv("MERCADOPAGO_REDIRECT_URI", "http://localhost:8000/profiles/mercadopago/callback/")
MERCADOPAGO_PLATFORM_FEE_PERCENTAGE = float(os.getenv("MERCADOPAGO_PLATFORM_FEE_PERCENTAGE", "10"))  # Comisión de la plataforma (%)

# En desarrollo, usar credenciales de prueba si no están configuradas
if DEBUG and not MERCADOPAGO_ACCESS_TOKEN:
    print("⚠️  WARNING: MercadoPago credentials not configured.")
    print("   The payment system will not work until you add your test credentials.")
    print("   Get them from: https://www.mercadopago.com.ar/developers/panel/app")
    print("   Add to .env file:")
    print("   MERCADOPAGO_ACCESS_TOKEN=TEST-your-access-token")
    print("   MERCADOPAGO_PUBLIC_KEY=TEST-your-public-key")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# CONFIGURACIÓN DE MEDIA (IMÁGENES)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Cloudinary para imágenes en producción (opcional)
if os.getenv("CLOUDINARY_URL") and not DEBUG:
    try:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api
        
        cloudinary.config(cloudinary_url=os.getenv('CLOUDINARY_URL'))
        DEFAULT_FILE_STORAGE = 'config.cloudinary_storage.CloudinaryMediaStorage'
    except:
        pass  # Si falla, usa MEDIA_ROOT local

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Filtro personalizado para remover datos sensibles de los logs
class SensitiveDataFilter:
    """Filtro de logging para prevenir exposición de datos sensibles en logs."""
    
    # Lista de campos sensibles que deben ser censurados
    SENSITIVE_KEYS = [
        'password', 'token', 'secret', 'api_key', 'authorization',
        'csrf', 'session', 'cookie', 'credit_card', 'ssn', 'cvv',
        'access_token', 'refresh_token', 'private_key'
    ]
    
    def filter(self, record):
        """Filtra y censura información sensible en los mensajes de log."""
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            # Censurar datos sensibles comunes
            for key in self.SENSITIVE_KEYS:
                if key in msg.lower():
                    # Reemplazar con asteriscos
                    import re
                    pattern = rf"{key}['\"]?\s*[:=]\s*['\"]?([^'\"\s,}}]+)"
                    msg = re.sub(pattern, f"{key}=****", msg, flags=re.IGNORECASE)
            record.msg = msg
        return True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'sensitive_data': {
            '()': 'config.settings.SensitiveDataFilter',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'formatter': 'verbose',
            'filters': ['sensitive_data'],
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['sensitive_data'],
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
