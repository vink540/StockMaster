from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Sales
    path('', views.sale_list, name='sale_list'),
    path('new/', views.sale_create, name='sale_create'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('<int:pk>/delete/', views.sale_delete, name='sale_delete'),
    path('<int:pk>/receipt/', views.sale_receipt, name='sale_receipt'),
    path('<int:pk>/print/', views.print_receipt, name='print_receipt'),
    
    # Customers (Clientes para fiados)
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_update, name='customer_update'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    # Credit Sales (Fiados)
    path('credits/', views.credit_sales, name='credit_sales'),
    path('credits/<int:pk>/pay/', views.add_payment, name='add_payment'),
    path('credits/pending/', views.pending_credits, name='pending_credits'),
    
    # Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('ventas/<int:sale_pk>/devolucion/', views.create_return, name='create_return'),
    path('devoluciones/', views.return_list, name='return_list'),
    path('devoluciones/<int:pk>/', views.return_detail, name='return_detail'),
    path('devoluciones/<int:pk>/cancelar/', views.cancel_return, name='cancel_return'),
    path('caja/abrir/', views.cash_register_open, name='cash_register_open'),
    path('caja/actual/', views.cash_register_current, name='cash_register_current'),
    path('caja/cerrar/', views.cash_register_close, name='cash_register_close'),
    path('caja/<int:pk>/', views.cash_register_detail, name='cash_register_detail'),
    path('caja/', views.cash_register_list, name='cash_register_list'),
    path('caja/movimiento/', views.add_cash_movement, name='add_cash_movement'),
]