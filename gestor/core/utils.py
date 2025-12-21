from datetime import date, timedelta
from .models import Product

def get_expiring_products(days=10):
    today = date.today()
    limit_date = today + timedelta(days=days)
    return Product.objects.filter(expiration_date__range=[today, limit_date])
