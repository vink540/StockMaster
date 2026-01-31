from django.db import models
# Al INICIO del archivo accounts/models.py
from django.contrib.auth.models import User

class Company(models.Model):
    """Empresa/Tienda de cada usuario"""
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company')
    name = models.CharField(max_length=200, default='Mi Tienda')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
    
    def __str__(self):
        return f"{self.name} - {self.owner.username}"

class SystemConfig(models.Model):
    """Configuración del sistema"""
    
    # Módulos activados
    enable_credits = models.BooleanField(default=True, verbose_name="Habilitar Fiados")
    enable_categories = models.BooleanField(default=True, verbose_name="Habilitar Categorías")
    enable_expiration_alerts = models.BooleanField(default=True, verbose_name="Habilitar Alertas de Vencimiento")
    enable_low_stock_alerts = models.BooleanField(default=True, verbose_name="Habilitar Alertas de Stock Bajo")
    enable_barcode_scanner = models.BooleanField(default=True, verbose_name="Habilitar Escáner de Códigos")
    enable_reports = models.BooleanField(default=True, verbose_name="Habilitar Reportes")
    enable_customers = models.BooleanField(default=True, verbose_name="Habilitar Gestión de Clientes")
    
    # Configuraciones generales
    company_name = models.CharField(max_length=200, default="StockMaster", verbose_name="Nombre del negocio")
    expiration_alert_days = models.IntegerField(default=30, verbose_name="Días de alerta de vencimiento")
    
    # Metadatos
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuraciones del Sistema"
    
    def __str__(self):
        return f"Configuración - {self.company_name}"
    
    @classmethod
    def get_config(cls):
        """Obtener o crear la configuración del sistema"""
        config, created = cls.objects.get_or_create(pk=1)
        return config
    
    # accounts/models.py
# AGREGAR este modelo al final del archivo (después de SystemConfig)

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class AlertSnapshot(models.Model):
    """Modelo para rastrear el estado de las alertas cuando el usuario las vio"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alert_snapshots')
    viewed_at = models.DateTimeField(default=timezone.now)
    
    # Contadores en el momento que vio las alertas
    low_stock_count = models.IntegerField(default=0)
    expiring_soon_count = models.IntegerField(default=0)
    expired_count = models.IntegerField(default=0)
    high_debt_count = models.IntegerField(default=0)
    
    # IDs de productos/clientes específicos que vio
    low_stock_ids = models.TextField(default='', blank=True)  # IDs separados por comas
    expiring_soon_ids = models.TextField(default='', blank=True)
    expired_ids = models.TextField(default='', blank=True)
    high_debt_ids = models.TextField(default='', blank=True)
    
    class Meta:
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.viewed_at.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def get_last_snapshot(cls, user):
        """Obtener el último snapshot del usuario"""
        return cls.objects.filter(user=user).first()
    
    @classmethod
    def create_snapshot(cls, user, alert_data):
        """Crear un nuevo snapshot de las alertas actuales"""
        return cls.objects.create(
            user=user,
            low_stock_count=alert_data.get('low_stock_count', 0),
            expiring_soon_count=alert_data.get('expiring_soon_count', 0),
            expired_count=alert_data.get('expired_count', 0),
            high_debt_count=alert_data.get('high_debt_count', 0),
            low_stock_ids=alert_data.get('low_stock_ids', ''),
            expiring_soon_ids=alert_data.get('expiring_soon_ids', ''),
            expired_ids=alert_data.get('expired_ids', ''),
            high_debt_ids=alert_data.get('high_debt_ids', ''),
        )


# IMPORTANTE: Después de agregar este modelo, ejecutar:
# python manage.py makemigrations
# python manage.py migrate