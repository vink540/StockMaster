from django.db import models
from django.contrib.auth.models import User
from inventory.models import Product
from django.utils import timezone
from decimal import Decimal

class Customer(models.Model):
    """Clientes (para fiados)"""
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=200, verbose_name="Nombre completo")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.TextField(blank=True, verbose_name="Dirección")
    
    # Límite de crédito
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Límite de crédito")
    
    # Metadatos
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['name']
        unique_together = [['company', 'name']]  # Nombre único por empresa
    
    def __str__(self):
        return self.name
    
    @property
    def total_debt(self):
        """Total de deuda pendiente"""
        return sum(sale.pending_amount for sale in self.sales.filter(is_paid=False))
    
    @property
    def available_credit(self):
        """Crédito disponible"""
        return self.credit_limit - self.total_debt
    
    @property
    def can_buy_on_credit(self):
        """Verifica si puede comprar fiado"""
        return self.is_active and self.total_debt < self.credit_limit

class Sale(models.Model):
    """Ventas"""
    PAYMENT_METHODS = [
        ('CASH', 'Efectivo'),
        ('CARD', 'Tarjeta'),
        ('TRANSFER', 'Transferencia'),
        ('CREDIT', 'Fiado'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='sales')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales', verbose_name="Cliente")
    
    # Totales
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Pago
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH')
    is_paid = models.BooleanField(default=True, verbose_name="Pagado")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Monto pagado")
    
    # Metadatos
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Venta #{self.id} - ${self.total}"
    
    @property
    def pending_amount(self):
        """Monto pendiente de pago"""
        return self.total - self.paid_amount
    
    @property
    def is_credit_sale(self):
        """Es una venta fiada"""
        return self.payment_method == 'CREDIT'
    
    def calculate_totals(self):
        """Calcula los totales de la venta"""
        self.subtotal = sum(item.subtotal for item in self.items.all())
        self.total = self.subtotal - self.discount
        self.save()

class SaleItem(models.Model):
    """Items de una venta"""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = "Item de Venta"
        verbose_name_plural = "Items de Venta"
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        """Calcula el subtotal automáticamente"""
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class Payment(models.Model):
    """Pagos de ventas fiadas"""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Sale.PAYMENT_METHODS, default='CASH')
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Pago ${self.amount} - Venta #{self.sale.id}"
    
    def save(self, *args, **kwargs):
        """Actualiza el monto pagado de la venta"""
        super().save(*args, **kwargs)
        self.sale.paid_amount = sum(p.amount for p in self.sale.payments.all())
        self.sale.is_paid = self.sale.paid_amount >= self.sale.total
        self.sale.save()

class Return(models.Model):
    """Devolución de productos de una venta"""
    RETURN_TYPES = [
        ('TOTAL', 'Devolución Total'),
        ('PARTIAL', 'Devolución Parcial'),
    ]
    
    REFUND_METHODS = [
        ('CASH', 'Efectivo'),
        ('CREDIT', 'Crédito en cuenta'),
        ('EXCHANGE', 'Cambio por otro producto'),
    ]
    
    sale = models.ForeignKey('Sale', on_delete=models.CASCADE, related_name='returns')
    return_type = models.CharField(max_length=10, choices=RETURN_TYPES, default='PARTIAL')
    reason = models.TextField(help_text='Motivo de la devolución')
    refund_method = models.CharField(max_length=10, choices=REFUND_METHODS, default='CASH')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_processed = models.BooleanField(default=True, help_text='Si ya se procesó (devolvió stock)')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'
    
    def __str__(self):
        return f"Devolución #{self.id} - Venta #{self.sale.id} - ${self.total_amount}"
    
    @property
    def items_count(self):
        """Cantidad de items devueltos"""
        return self.items.count()

class ReturnItem(models.Model):
    """Item individual devuelto"""
    return_obj = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey('SaleItem', on_delete=models.CASCADE, related_name='return_items')
    
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = 'Item Devuelto'
        verbose_name_plural = 'Items Devueltos'
    
    def __str__(self):
        return f"{self.sale_item.product.name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class CashRegister(models.Model):
    """Caja diaria - Apertura y cierre"""
    STATUS_CHOICES = [
        ('OPEN', 'Abierta'),
        ('CLOSED', 'Cerrada'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='cash_registers')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cash_registers')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    
    opened_at = models.DateTimeField(default=timezone.now)
    opening_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    closed_at = models.DateTimeField(null=True, blank=True)
    closing_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    expected_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cash_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_card_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_transfer_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_credit_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    difference = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    opening_notes = models.TextField(blank=True, default='')
    closing_notes = models.TextField(blank=True, default='')
    
    class Meta:
        ordering = ['-opened_at']
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'
    
    def __str__(self):
        return f"Caja {self.opened_at.strftime('%d/%m/%Y')} - {self.get_status_display()}"
    
    @classmethod
    def get_current(cls, user=None, company=None):
        """Obtener caja abierta actual"""
        filters = {'status': 'OPEN'}
        if user:
            filters['user'] = user
        if company:
            filters['company'] = company
        return cls.objects.filter(**filters).first()
    
    @classmethod
    def has_open_register(cls, user=None, company=None):
        """Verificar si hay caja abierta"""
        return cls.get_current(user, company) is not None
    
    def calculate_totals(self):
        """Calcular totales desde las ventas de esta caja"""
        sales = Sale.objects.filter(
            company=self.company,
            created_at__gte=self.opened_at,
            created_at__lte=self.closed_at if self.closed_at else timezone.now()
        )
        
        self.total_sales = sales.aggregate(total=models.Sum('total'))['total'] or Decimal('0')
        self.total_cash_sales = sales.filter(payment_method='CASH').aggregate(total=models.Sum('total'))['total'] or Decimal('0')
        self.total_card_sales = sales.filter(payment_method='CARD').aggregate(total=models.Sum('total'))['total'] or Decimal('0')
        self.total_transfer_sales = sales.filter(payment_method='TRANSFER').aggregate(total=models.Sum('total'))['total'] or Decimal('0')
        self.total_credit_sales = sales.filter(payment_method='CREDIT').aggregate(total=models.Sum('total'))['total'] or Decimal('0')
        
        self.expected_cash = self.opening_amount + self.total_cash_sales
        self.save()
    
    def close_register(self, closing_amount, notes=''):
        """Cerrar caja"""
        self.closing_amount = closing_amount
        self.closing_notes = notes
        self.closed_at = timezone.now()
        self.status = 'CLOSED'
        self.calculate_totals()
        self.difference = self.closing_amount - self.expected_cash
        self.save()
        return self.difference

class CashMovement(models.Model):
    """Movimientos de efectivo (ingresos/egresos manuales)"""
    MOVEMENT_TYPES = [
        ('IN', 'Ingreso'),
        ('OUT', 'Egreso'),
    ]
    
    cash_register = models.ForeignKey(CashRegister, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=200, help_text='Motivo del movimiento')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Movimiento de Efectivo'
        verbose_name_plural = 'Movimientos de Efectivo'
    
    def __str__(self):
        symbol = '+' if self.movement_type == 'IN' else '-'
        return f"{symbol}${self.amount} - {self.reason}"