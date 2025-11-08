from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User


@admin.action(description="Desactivar usuarios y ocultar sus productos")
def deactivate_users_and_hide_products(modeladmin, request, queryset):
	from mercado.models import Product
	queryset.update(is_active=False)
	Product.objects.filter(seller__in=queryset).update(active=False)


class UserAdmin(DjangoUserAdmin):
	actions = DjangoUserAdmin.actions + (deactivate_users_and_hide_products,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
