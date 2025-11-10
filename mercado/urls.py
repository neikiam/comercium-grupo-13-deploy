from django.urls import path

from . import views

app_name = "mercado"

urlpatterns = [
    path("", views.product_list, name="productlist"),
    path("detail/<int:pk>/", views.product_detail, name="product-detail"),
    path("create/", views.product_create, name="productcreate"),
    path("edit/<int:pk>/", views.product_edit, name="product-edit"),
    path("delete/<int:pk>/", views.product_delete, name="product-delete"),
    path("image/delete/<int:image_id>/", views.delete_product_image, name="delete-product-image"),
    path("cart/", views.view_cart, name="view-cart"),
    path("add/<int:product_id>/", views.add_to_cart, name="add-to-cart"),
    path("cart/increase/<int:product_id>/", views.cart_increase, name="cart-increase"),
    path("cart/decrease/<int:product_id>/", views.cart_decrease, name="cart-decrease"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart-remove"),

    path("pago-carrito/", views.create_preference_cart, name="crear-preferencia-carrito"),
    path("pago-exitoso/", views.payment_success, name="pago-exitoso"),
    path("pago-fallido/", views.payment_failure, name="pago-fallido"),
    path("webhook/", views.mercadopago_webhook, name="mercadopago-webhook"),
    
    path("mis-compras/", views.my_purchases, name="my-purchases"),
    path("mis-ventas/", views.my_sales, name="my-sales"),
    path("orden/<int:order_id>/", views.order_detail, name="order-detail"),
]
