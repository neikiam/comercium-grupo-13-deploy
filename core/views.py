from django.shortcuts import redirect, render

from mercado.models import Product


def home(request):
    products = Product.objects.filter(active=True).select_related('seller').order_by("-created_at")[:6]
    return render(request, "index.html", {"products": products})

def login_view(request):
    return render(request, 'login.html')