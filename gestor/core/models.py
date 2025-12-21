import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    barcode = models.CharField(max_length=50, blank=True, null=True)
    expiration_date = models.DateField(null=True, blank=True)


    # SKU autogenerado
    sku = models.CharField(max_length=20, unique=True, editable=False)

    # Nueva categoría del producto
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Nueva fecha de vencimiento
    expiration_date = models.DateField(null=True, blank=True)

    # Umbral estándar para "próximo a vencer"
    EXPIRATION_WARNING_DAYS = 7

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = uuid.uuid4().hex[:8].upper()  # Ej: A1B2C3D4
        super().save(*args, **kwargs)

    # ----------- PROPIEDADES ÚTILES PARA FILTROS -----------

    @property
    def is_expired(self):
        """Retorna True si el producto ya venció."""
        if not self.expiration_date:
            return False
        return self.expiration_date < timezone.now().date()

    @property
    def expires_soon(self):
        """Retorna True si está por vencer dentro del límite X días."""
        if not self.expiration_date:
            return False
        today = timezone.now().date()
        warning_limit = today + timedelta(days=self.EXPIRATION_WARNING_DAYS)
        return today <= self.expiration_date <= warning_limit

    def __str__(self):
        return f"{self.name} ({self.sku})"



class Sale(models.Model):
    # ¡NO definas el campo 'id'! Django lo hace automáticamente
    date = models.DateTimeField(auto_now_add=True)
    customer = models.CharField(max_length=100, blank=True, null=True)
    attendant = models.CharField(max_length=100, blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    def __str__(self):
        return f"Venta #{self.id} - ${self.total}"
    
    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-date']
        

class SaleItem(models.Model):
    # ¡NO definas el campo 'id'! Django lo hace automáticamente
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Calcular subtotal automáticamente
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)
        
        # Recalcular total de la venta
        self.update_sale_total()
    
    def update_sale_total(self):
        """Actualiza el total de la venta"""
        total = self.sale.items.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        Sale.objects.filter(id=self.sale.id).update(total=total)
        # Actualizar el objeto en memoria
        self.sale.total = total
        self.sale.save(update_fields=['total'])
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} = ${self.subtotal}"
    
    class Meta:
        verbose_name = "Item de Venta"
        verbose_name_plural = "Items de Venta"