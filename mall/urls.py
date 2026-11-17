from django.urls import path
from . import views

urlpatterns = [
    # 看板
    path("", views.console, name="console"),
    path("report/", views.report_view, name="report"),
    path("api/state/", views.api_state),
    path("api/toggle/", views.api_toggle),
    path("api/run/", views.api_run),

    # 被测商城接口（SUT）
    path("api/health/", views.api_health),
    path("api/admin/reset/", views.api_reset),
    path("api/auth/login/", views.api_login),
    path("api/auth/logout/", views.api_logout),
    path("api/auth/profile/", views.api_profile),
    path("api/products/", views.api_products),
    path("api/products/search/", views.api_search),
    path("api/products/<int:pk>/", views.api_product_detail),
    path("api/cart/", views.api_cart),
    path("api/cart/items/", views.api_cart_add),
    path("api/cart/items/<int:pk>/", views.api_cart_remove),
    path("api/orders/", views.api_orders),
    path("api/orders/<int:pk>/", views.api_order_detail),
    path("api/orders/<int:pk>/pay/", views.api_order_pay),
    path("api/orders/<int:pk>/cancel/", views.api_order_cancel),
]
