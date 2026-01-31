# accounts/context_processors.py
# REEMPLAZAR TODO EL CONTENIDO con este archivo

from accounts.models import SystemConfig, AlertSnapshot
from inventory.models import Product
from sales.models import Customer
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

def system_config(request):
    """Context processor para configuración del sistema y alertas"""
    config = SystemConfig.get_config()
    
    # Inicializar contadores
    alert_counts = {
        'total': 0,
        'new': 0,  # Solo alertas nuevas (no vistas)
        'low_stock': 0,
        'expiring_soon': 0,
        'expired': 0,
        'high_debt': 0,
    }
    
    alert_ids = {
        'low_stock_ids': [],
        'expiring_soon_ids': [],
        'expired_ids': [],
        'high_debt_ids': [],
    }
    
    # Solo calcular si el usuario está autenticado
    if request.user.is_authenticated:
        # ✅ Obtener la empresa del usuario
        if hasattr(request.user, 'company'):
            user_company = request.user.company
            
            # Productos con stock bajo
            if config.enable_low_stock_alerts:
                low_stock_products = Product.objects.filter(
                    company=user_company,  # ← FILTRO POR EMPRESA
                    is_active=True, 
                    stock__lte=F('min_stock')
                )
                alert_counts['low_stock'] = low_stock_products.count()
                alert_ids['low_stock_ids'] = list(low_stock_products.values_list('id', flat=True))
            
            # Productos por vencer
            if config.enable_expiration_alerts:
                expiring_products = Product.objects.filter(
                    company=user_company,  # ← FILTRO POR EMPRESA
                    is_active=True,
                    expiration_date__gte=timezone.now().date(),
                    expiration_date__lte=timezone.now().date() + timedelta(days=config.expiration_alert_days)
                )
                alert_counts['expiring_soon'] = expiring_products.count()
                alert_ids['expiring_soon_ids'] = list(expiring_products.values_list('id', flat=True))
                
                # Productos vencidos
                expired_products = Product.objects.filter(
                    company=user_company,  # ← FILTRO POR EMPRESA
                    is_active=True,
                    expiration_date__lt=timezone.now().date()
                )
                alert_counts['expired'] = expired_products.count()
                alert_ids['expired_ids'] = list(expired_products.values_list('id', flat=True))
            
            # Clientes con deuda alta (opcional)
            if config.enable_credits and config.enable_customers:
                # Clientes que superan el 80% de su límite de crédito
                high_debt_customer_ids = []
                customers = Customer.objects.filter(
                    company=user_company,  # ← FILTRO POR EMPRESA
                    is_active=True
                )
                for customer in customers:
                    if customer.available_credit < (customer.credit_limit * Decimal('0.2')):
                        alert_counts['high_debt'] += 1
                        high_debt_customer_ids.append(customer.id)
                alert_ids['high_debt_ids'] = high_debt_customer_ids
            
            # Total de alertas actuales
            alert_counts['total'] = (
                alert_counts['low_stock'] + 
                alert_counts['expiring_soon'] + 
                alert_counts['expired'] + 
                alert_counts['high_debt']
            )
            
            # Calcular alertas NUEVAS (comparando con el último snapshot)
            last_snapshot = AlertSnapshot.get_last_snapshot(request.user)
            
            if last_snapshot:
                # Convertir IDs guardados a sets
                old_low_stock = set(map(int, last_snapshot.low_stock_ids.split(',') if last_snapshot.low_stock_ids else []))
                old_expiring = set(map(int, last_snapshot.expiring_soon_ids.split(',') if last_snapshot.expiring_soon_ids else []))
                old_expired = set(map(int, last_snapshot.expired_ids.split(',') if last_snapshot.expired_ids else []))
                old_high_debt = set(map(int, last_snapshot.high_debt_ids.split(',') if last_snapshot.high_debt_ids else []))
                
                # Comparar con los actuales
                new_low_stock = set(alert_ids['low_stock_ids']) - old_low_stock
                new_expiring = set(alert_ids['expiring_soon_ids']) - old_expiring
                new_expired = set(alert_ids['expired_ids']) - old_expired
                new_high_debt = set(alert_ids['high_debt_ids']) - old_high_debt
                
                # Contar solo las nuevas
                alert_counts['new'] = len(new_low_stock) + len(new_expiring) + len(new_expired) + len(new_high_debt)
            else:
                # Si nunca vio alertas, todas son nuevas
                alert_counts['new'] = alert_counts['total']
    
    return {
        'system_config': config,
        'alert_counts': alert_counts,
        'alert_ids': alert_ids,  # Para usar en la vista de alertas
    }