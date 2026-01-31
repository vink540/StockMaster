from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def smart_decimal(value):
    """
    Muestra decimales solo si son necesarios
    2.000 -> 2
    2.500 -> 2.5
    2.125 -> 2.125
    """
    if value is None:
        return "0"
    
    try:
        value = Decimal(str(value))
        # Si el número es entero, mostrar sin decimales
        if value == value.to_integral_value():
            return str(int(value))
        # Si tiene decimales, mostrar solo los necesarios
        else:
            return str(value.normalize())
    except:
        return str(value)