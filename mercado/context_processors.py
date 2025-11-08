from .models import Cart


def cart(request):
    count = 0
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        try:
            c = Cart.objects.prefetch_related("items").only("id").get(user=user)
            count = c.items.count()
        except Cart.DoesNotExist:
            count = 0
    return {"cart_count": count}
