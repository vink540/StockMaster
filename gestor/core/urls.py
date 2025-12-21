from django.urls import path
from django.shortcuts import render
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('register/', views.register, name='register'),  # COMENTADO si no lo necesitas
    path('profile/', views.profile, name='profile'),  # COMENTADO si no lo necesitas
    path('settings/', views.settings, name='settings'),  # COMENTADO si no lo necesitas
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("sales/register/", views.register_sale, name="register_sale"),
    path("report/month/", views.monthly_report, name="monthly_report"),
    path("scan/", lambda r: render(r, "core/barcode_scanner.html"), name="scan"),
    path("api/search_barcode/", views.search_barcode, name="search_barcode"),
    path("category/new/", views.category_create, name="category_create"),
    path("alerts/", views.alerts, name="alerts"),
    path("sales/", views.sales_list, name="sales_list"),
    path("sales/new/", views.create_sale, name="create_sale"),
    path("sales/<int:sale_id>/", views.sale_detail, name="sale_detail"),
    path("products/add/", views.add_product, name="add_product"),
    path("products/edit/<int:product_id>/", views.edit_product, name="edit_product"),
    path("products/delete/<int:product_id>/", views.delete_product, name="delete_product"),
    path("products/expiring/", views.expiring_products, name="expiring_products"),
    path("report/month/export/", views.export_monthly_report, name="export_monthly_report"),
    path("report/month/print/", views.print_monthly_report, name="print_monthly_report"),
    path("sales/<int:sale_id>/receipt/", views.sale_receipt, name="sales_receipt"),
]