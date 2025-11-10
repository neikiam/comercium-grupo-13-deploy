from django.contrib import admin
from django.db import transaction

from .models import Cart, CartItem, Product, ProductImage, Order, OrderItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "seller", "marca", "price", "stock", "active", "created_at")
    search_fields = ("title", "description", "marca", "seller__username")
    list_filter = ("active", "created_at", "seller")
    actions = ("soft_delete_selected", "safe_delete_selected",)

    def delete_model(self, request, obj):
        CartItem.objects.filter(product=obj).delete()
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        CartItem.objects.filter(product__in=queryset).delete()
        super().delete_queryset(request, queryset)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    @admin.action(description="Ocultar seleccionados (soft delete)")
    def soft_delete_selected(self, request, queryset):
        queryset.update(active=False)

    @admin.action(description="Eliminar seleccionados (limpia carritos primero)")
    def safe_delete_selected(self, request, queryset):
        with transaction.atomic():
            CartItem.objects.filter(product__in=queryset).delete()
            for obj in queryset:
                super().delete_model(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "item_count", "total_amount")
    search_fields = ("user__username", "user__email")
    actions = ("empty_selected_carts",)

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = "Items"

    def total_amount(self, obj):
        try:
            return obj.total()
        except Exception:
            return "-"
    total_amount.short_description = "Total"

    @admin.action(description="Vaciar carritos seleccionados")
    def empty_selected_carts(self, request, queryset):
        CartItem.objects.filter(cart__in=queryset).delete()


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity")
    list_filter = ("product", "cart__user")
    search_fields = ("product__title", "cart__user__username")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "order", "uploaded_at")
    list_filter = ("product", "uploaded_at")
    search_fields = ("product__title",)
    ordering = ("product", "order")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'seller', 'product_title', 'product_price', 'quantity', 'subtotal')
    can_delete = False
    
    def subtotal(self, obj):
        return obj.subtotal()


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'status', 'total', 'payment_id', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('buyer__username', 'payment_id', 'preference_id')
    readonly_fields = ('buyer', 'total', 'payment_id', 'preference_id', 'payment_status', 'payment_type', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product_title', 'seller', 'quantity', 'product_price')
    list_filter = ('order__created_at', 'seller')
    search_fields = ('product_title', 'seller__username', 'order__buyer__username')
    readonly_fields = ('order', 'product', 'seller', 'product_title', 'product_price', 'quantity')

