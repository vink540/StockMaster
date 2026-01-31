from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

class Category(models.Model):
    """Categorías de productos"""
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['name']
        unique_together = [['company', 'name']]  # Nombre único por empresa
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """Productos del inventario"""
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='products')
    barcode = models.CharField(max_length=50, verbose_name="Código de barras")
    name = models.CharField(max_length=200, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name="Categoría")
    
    # Precios
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de costo")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de venta")
    
    # Stock
    stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name="Stock actual")
    min_stock = models.DecimalField(max_digits=10, decimal_places=3, default=5, verbose_name="Stock mínimo")
    
    # Fechas
    expiration_date = models.DateField(null=True, blank=True, verbose_name="Fecha de vencimiento")
    
    # Imagen
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="Imagen")
    
    # Metadatos
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='products_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-created_at']
        unique_together = [['company', 'barcode']]  # Código único por empresa
    
    def __str__(self):
        return f"{self.name} ({self.barcode})"
    
    @property
    def is_low_stock(self):
        """Verifica si el stock está bajo"""
        stock = Decimal(str(self.stock))
        min_stock = Decimal(str(self.min_stock))
        return stock <= min_stock
    
    @property
    def is_expiring_soon(self):
        """Verifica si el producto vence en los próximos 30 días"""
        if not self.expiration_date:
            return False
        days_until_expiration = (self.expiration_date - timezone.now().date()).days
        return 0 <= days_until_expiration <= 30
    
    @property
    def is_expired(self):
        """Verifica si el producto ya venció"""
        if not self.expiration_date:
            return False
        return self.expiration_date < timezone.now().date()
    
    @property
    def profit_margin(self):
        """Calcula el margen de ganancia"""
        if self.cost_price == 0:
            return 0
        return ((self.sale_price - self.cost_price) / self.cost_price) * 100
    
    @property
    def total_value(self):
        """Valor total del stock"""
        return self.stock * self.sale_price

class StockMovement(models.Model):
    """Registro de movimientos de stock"""
    MOVEMENT_TYPES = [
        ('IN', 'Entrada'),
        ('OUT', 'Salida'),
        ('ADJUSTMENT', 'Ajuste'),
        ('RETURN', 'Devolución'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    reason = models.TextField(blank=True)
    
    previous_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    new_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"

class PriceHistory(models.Model):
    """Historial de cambios de precios de productos"""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='price_history')
    
    # Precios anteriores
    previous_cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    previous_sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Precios nuevos
    new_cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    new_sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Cambios en porcentaje
    cost_change_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    sale_change_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Margen de ganancia en ese momento
    profit_margin = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Metadatos
    reason = models.CharField(max_length=200, blank=True, default='')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Historial de Precio'
        verbose_name_plural = 'Historial de Precios'
    
    def __str__(self):
        return f"{self.product.name} - {self.changed_at.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def create_price_change(cls, product, old_cost, old_sale, new_cost, new_sale, user, reason=''):
        """Crear un registro de cambio de precio"""
        cost_change = 0
        if old_cost > 0:
            cost_change = ((new_cost - old_cost) / old_cost) * 100
        
        sale_change = 0
        if old_sale > 0:
            sale_change = ((new_sale - old_sale) / old_sale) * 100
        
        profit_margin = 0
        if new_cost > 0:
            profit_margin = ((new_sale - new_cost) / new_cost) * 100
        
        return cls.objects.create(
            product=product,
            previous_cost_price=old_cost,
            previous_sale_price=old_sale,
            new_cost_price=new_cost,
            new_sale_price=new_sale,
            cost_change_percent=cost_change,
            sale_change_percent=sale_change,
            profit_margin=profit_margin,
            reason=reason,
            changed_by=user
        )
    
    def get_cost_change_badge(self):
        """Retorna clase CSS según el cambio de costo"""
        if self.cost_change_percent > 0:
            return 'badge-danger'
        elif self.cost_change_percent < 0:
            return 'badge-success'
        return 'badge-secondary'
    
    def get_sale_change_badge(self):
        """Retorna clase CSS según el cambio de venta"""
        if self.sale_change_percent > 0:
            return 'badge-success'
        elif self.sale_change_percent < 0:
            return 'badge-danger'
        return 'badge-secondary'