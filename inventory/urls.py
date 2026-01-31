from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Alerts
    path('alerts/', views.alerts, name='alerts'),
    path('alerts/expiring/', views.expiring_products, name='expiring_products'),
    path('alerts/low-stock/', views.low_stock_products, name='low_stock_products'),
    
    # Barcode Scanner
    path('scan/', views.barcode_scanner, name='barcode_scanner'),
    path('api/search-barcode/', views.search_barcode, name='search_barcode'),
    
    # Stock Movements
    path('stock/movements/', views.stock_movements, name='stock_movements'),
    path('stock/adjust/<int:pk>/', views.adjust_stock, name='adjust_stock'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/monthly/', views.monthly_report, name='monthly_report'),
    path('reports/inventory/', views.inventory_report, name='inventory_report'),
    
    path('productos/exportar/', views.export_products_excel, name='export_products_excel'),
    path('productos/importar/', views.import_products_excel, name='import_products_excel'),
    path('productos/plantilla/', views.download_products_template, name='download_products_template'),
    path('productos/<int:pk>/historial-precios/', views.price_history, name='price_history'),
    path('historial-precios/', views.all_price_changes, name='all_price_changes'),
    path('reportes/', views.reports_dashboard, name='reports_dashboard'),
    path('reportes/ventas/', views.sales_report, name='sales_report'),
    path('reportes/productos/', views.products_report, name='products_report'),
]