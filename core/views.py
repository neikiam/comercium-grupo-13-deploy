from django.shortcuts import redirect, render

from mercado.models import Product


def home(request):
    products = Product.objects.filter(active=True).select_related('seller').order_by("-created_at")[:6]
    return render(request, "index.html", {"products": products})

def login_view(request):
    return render(request, 'login.html')


def error_404(request, exception):
    """Handler para errores 404 (página no encontrada)."""
    return render(request, 'errors/404.html', status=404)


def error_500(request):
    """Handler para errores 500 (error interno del servidor)."""
    return render(request, 'errors/500.html', status=500)
