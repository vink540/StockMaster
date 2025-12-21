from .models import Category
from datetime import timedelta
from django.db.models import Sum, F, Count, Avg
from .utils import get_expiring_products
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Avg, F, Q
from datetime import datetime, timedelta  # ¡ESTA ES LA IMPORTACIÓN QUE FALTA!
from django.utils import timezone
from decimal import Decimal
import calendar
from .models import Product, Sale, SaleItem, Category
from django.db import transaction
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

@login_required
def settings(request):
    return render(request, 'core/settings.html')

@login_required
def profile(request):
    return render(request, 'core/profile.html', {'user': request.user})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')  # o la ruta que prefieras
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True



def product_list(request):
    products = Product.objects.all()
    categories = Category.objects.all()

    search = request.GET.get("search")
    category_filter = request.GET.get("category")
    filter_expired = request.GET.get("expired")
    filter_soon = request.GET.get("soon")
    filter_low_stock = request.GET.get("low_stock")

    # buscar por nombre
    if search:
        products = products.filter(name__icontains=search)

    # filtrar por categoría
    if category_filter and category_filter != "all":
        products = products.filter(category__id=category_filter)

    # filtrar vencidos
    if filter_expired:
        today = timezone.now().date()
        products = products.filter(expiration_date__lt=today)

    # filtrar próximos a vencer (10 días antes)
    if filter_soon:
        today = timezone.now().date()
        soon_limit = today + timedelta(days=10)
        products = products.filter(
            expiration_date__range=[today, soon_limit]
        )

    # filtrar stock bajo (menor o igual a 5)
    if filter_low_stock:
        products = products.filter(stock__lte=5)

    return render(request, "core/product_list.html", {
        "products": products,
        "categories": categories
    })
    
def product_create(request):
    if request.method == "POST":
        name = request.POST["name"]
        price = request.POST["price"]
        stock = request.POST["stock"]
        barcode = request.POST.get("barcode")  # opcional

        Product.objects.create(
            name=name,
            price=price,
            stock=stock,
            barcode=barcode
        )
        return redirect("product_list")

    return render(request, "core/product_create.html")

from django.utils import timezone

def register_sale(request):
    """
    Vista para registrar una nueva venta
    URL: /sales/register/
    """
    
    # Obtener productos con stock disponible
    products = Product.objects.filter(stock__gt=0).order_by('name')
    
    if request.method == 'POST':
        try:
            # 1. Obtener datos del formulario
            product_id = request.POST.get('product')
            quantity_str = request.POST.get('quantity', '1')
            
            # 2. Validaciones básicas
            if not product_id:
                messages.error(request, "❌ Debe seleccionar un producto")
                return render(request, 'core/register_sale.html', {
                    'products': products,
                    'error': "Debe seleccionar un producto"
                })
            
            try:
                quantity = int(quantity_str)
                if quantity <= 0:
                    raise ValueError("La cantidad debe ser mayor a 0")
            except (ValueError, TypeError):
                messages.error(request, "❌ La cantidad debe ser un número válido mayor a 0")
                return render(request, 'core/register_sale.html', {
                    'products': products,
                    'error': "La cantidad debe ser un número válido mayor a 0"
                })
            
            # 3. Obtener el producto
            product = get_object_or_404(Product, id=product_id)
            
            # 4. Validar stock disponible
            if quantity > product.stock:
                messages.error(request, f"❌ Stock insuficiente. Disponible: {product.stock} unidades")
                return render(request, 'core/register_sale.html', {
                    'products': products,
                    'error': f"Stock insuficiente. Disponible: {product.stock} unidades"
                })
            
            # 5. Usar TRANSACCIÓN para asegurar consistencia
            with transaction.atomic():
                # DEBUG: Verificar antes de crear
                print(f"DEBUG: Intentando crear venta...")
                
                # 6. Crear la venta (¡SIN ESPECIFICAR ID!)
                sale = Sale.objects.create(
                    # date se establece automáticamente con auto_now_add=True
                    customer=request.POST.get('customer', ''),  # Opcional
                    attendant=request.POST.get('attendant', ''),  # Opcional
                    total=Decimal('0.00')  # Inicial en 0, se actualizará después
                )
                
                print(f"DEBUG: Venta creada con ID: {sale.id}")
                
                # 7. Crear el item de venta
                subtotal = product.price * quantity
                sale_item = SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=product.price,
                    subtotal=subtotal
                )
                
                print(f"DEBUG: Item creado: {sale_item}")
                
                # 8. Actualizar stock del producto
                product.stock -= quantity
                product.save()
                
                print(f"DEBUG: Stock actualizado. Nuevo stock: {product.stock}")
                
                # 9. Mensaje de éxito
                messages.success(request, 
                    f"✅ Venta registrada exitosamente!\n"
                    f"📋 Número de venta: #{sale.id}\n"
                    f"🛒 Producto: {product.name}\n"
                    f"🔢 Cantidad: {quantity}\n"
                    f"💰 Total: ${sale.total:.2f}"
                )
                
                # 10. Redirigir al detalle de la venta
                return redirect('sale_detail', sale_id=sale.id)
                
        except Exception as e:
            # Capturar cualquier error y mostrar información detallada
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ ERROR DETALLADO:\n{error_details}")
            
            messages.error(request, 
                f"❌ Error al registrar la venta\n"
                f"🔧 Detalles: {str(e)}"
            )
            
            return render(request, 'core/register_sale.html', {
                'products': products,
                'error': f"Error: {str(e)}"
            })
    
    # GET request - mostrar formulario vacío
    return render(request, 'core/register_sale.html', {
        'products': products
    })


def monthly_report(request):
    """
    Vista para generar reportes por semana, mes o año
    """
    try:
        # Obtener el primer año de ventas para el filtro
        first_sale = Sale.objects.order_by('date').first()
        
        # Si no hay ventas, usar el año actual
        if first_sale:
            first_year = first_sale.date.year
        else:
            first_year = datetime.now().year
        
        # Obtener filtros actuales de la URL
        current_week = request.GET.get('week')
        current_month = request.GET.get('month', str(datetime.now().month))
        current_year = request.GET.get('year', str(datetime.now().year))
        period_type = request.GET.get('period', 'month')  # 'week', 'month', 'year'
        
        # Convertir a enteros para comparaciones
        try:
            current_month_int = int(current_month)
        except (ValueError, TypeError):
            current_month_int = datetime.now().month
            
        try:
            current_year_int = int(current_year)
        except (ValueError, TypeError):
            current_year_int = datetime.now().year
        
        # Filtrar ventas según el período
        sales = Sale.objects.all()
        
        if period_type == 'week' and current_week:
            try:
                # Parsear semana (formato: YYYY-WW)
                year, week = map(int, current_week.split('-W'))
                # Calcular fecha de inicio de la semana
                start_date = datetime(year, 1, 1) + timedelta(weeks=week-1)
                end_date = start_date + timedelta(weeks=1)
                
                # Convertir a timezone aware si es necesario
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
                    
                sales = sales.filter(date__gte=start_date, date__lt=end_date)
            except (ValueError, IndexError):
                # Si hay error al parsear la semana, usar semana actual
                pass
                
        elif period_type == 'month':
            sales = sales.filter(
                date__year=current_year_int, 
                date__month=current_month_int
            )
        elif period_type == 'year':
            sales = sales.filter(date__year=current_year_int)
        
        # Calcular estadísticas básicas
        total_sales_count = sales.count()
        
        # Calcular total de ingresos
        month_total_result = sales.aggregate(total_sum=Sum('total'))
        month_total = month_total_result['total_sum'] or Decimal('0')
        
        # Calcular total de productos vendidos
        total_products_sold = 0
        for sale in sales:
            total_products_sold += sale.items.aggregate(
                total_qty=Sum('quantity')
            )['total_qty'] or 0
        
        # Calcular crecimiento vs período anterior (simplificado)
        month_growth = 0
        sales_growth = 0
        products_growth = 0
        
        # Obtener el nombre del mes actual
        current_month_name = calendar.month_name[current_month_int]
        
        # Obtener opciones para los filtros
        year_options = list(range(first_year, datetime.now().year + 2))
        
        month_options = [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ]
        
        # Generar opciones de semanas (últimas 12 semanas)
        week_options = []
        today = timezone.now()
        for i in range(12):
            week_date = today - timedelta(weeks=i)
            year, week_num, _ = week_date.isocalendar()
            week_options.append((f"{year}-W{week_num:02d}", f"Semana {week_num}, {year}"))
        
        # Obtener datos para gráficos (datos de ejemplo - deberías reemplazar con datos reales)
        if period_type == 'week':
            # Para semana: mostrar días de la semana
            daily_sales_labels = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
        elif period_type == 'month':
            # Para mes: mostrar los días del mes
            if sales.exists():
                # Obtener el primer día del mes
                first_day = datetime(current_year_int, current_month_int, 1)
                # Calcular días en el mes
                days_in_month = calendar.monthrange(current_year_int, current_month_int)[1]
                daily_sales_labels = [str(day) for day in range(1, days_in_month + 1)]
            else:
                daily_sales_labels = [str(day) for day in range(1, 31)]
        else:
            # Para año: mostrar meses
            daily_sales_labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                                  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        # Datos de ejemplo para gráficos (deberías reemplazar con cálculos reales)
        daily_sales_data = [100 + i*20 for i in range(len(daily_sales_labels))]
        
        # Obtener categorías para el gráfico de pastel
        categories = Category.objects.all()
        category_labels = [cat.name for cat in categories[:5]]
        category_values = [100, 80, 60, 40, 20]  # Datos de ejemplo
        
        # Calcular promedio de venta
        avg_sale = month_total / total_sales_count if total_sales_count > 0 else Decimal('0')
        
        # Obtener producto más vendido
        most_sold_product_data = SaleItem.objects.filter(
            sale__in=sales
        ).values(
            'product__name'
        ).annotate(
            total_quantity=Sum('quantity')
        ).order_by('-total_quantity').first()
        
        if most_sold_product_data:
            most_sold_product = {
                'name': most_sold_product_data['product__name'],
                'quantity': most_sold_product_data['total_quantity'] or 0
            }
        else:
            most_sold_product = {'name': 'No hay datos', 'quantity': 0}
        
        # Obtener mejor día
        best_day_data = sales.annotate(
            day=F('date__day')
        ).values('day').annotate(
            sales_count=Count('id')
        ).order_by('-sales_count').first()
        
        if best_day_data:
            best_day = {
                'date': f"{best_day_data['day']}/{current_month_int}",
                'sales': best_day_data['sales_count']
            }
        else:
            best_day = {'date': 'N/A', 'sales': 0}
        
        # Obtener hora pico (simplificado)
        peak_hour = {'hour': 14}  # Datos de ejemplo
        
        # Obtener ventas destacadas (top 10)
        top_sales = sales.order_by('-total')[:10]
        
        # Preparar contexto para el template
        context = {
            'month_total': month_total,
            'total_sales': total_sales_count,
            'total_products_sold': total_products_sold,
            'month_growth': month_growth,
            'sales_growth': sales_growth,
            'products_growth': products_growth,
            'current_month': current_month,
            'current_year': current_year,
            'current_week': current_week,
            'period_type': period_type,
            'first_year': first_year,
            'year_options': year_options,
            'month_options': month_options,
            'week_options': week_options,
            'daily_sales_data': daily_sales_data,
            'daily_sales_labels': daily_sales_labels,
            'category_labels': category_labels,
            'category_values': category_values,
            'avg_sale': avg_sale,
            'most_sold_product': most_sold_product,
            'best_day': best_day,
            'peak_hour': peak_hour,
            'top_sales': top_sales,
            'current_month_name': current_month_name,
        }
        
        return render(request, 'core/monthly_report.html', context)
        
    except Exception as e:
        # Manejo de errores básico
        messages.error(request, f'Error al generar el reporte: {str(e)}')
        return render(request, 'core/monthly_report.html', {
            'month_total': 0,
            'total_sales': 0,
            'total_products_sold': 0,
            'month_growth': 0,
            'sales_growth': 0,
            'products_growth': 0,
            'current_month': datetime.now().month,
            'current_year': datetime.now().year,
            'period_type': 'month',
            'first_year': datetime.now().year,
            'year_options': [datetime.now().year],
            'month_options': [(datetime.now().month, calendar.month_name[datetime.now().month])],
            'week_options': [],
            'daily_sales_data': [],
            'daily_sales_labels': [],
            'category_labels': [],
            'category_values': [],
            'avg_sale': 0,
            'most_sold_product': {'name': 'Error', 'quantity': 0},
            'best_day': {'date': 'Error', 'sales': 0},
            'peak_hour': {'hour': 0},
            'top_sales': [],
            'current_month_name': calendar.month_name[datetime.now().month],
        })

def export_monthly_report(request):
    return HttpResponse("Exportar reporte mensual — aún no implementado")

def print_monthly_report(request):
    return HttpResponse("Versión para imprimir — aún no implementado")


from django.http import JsonResponse

def search_barcode(request):
    barcode = request.GET.get("barcode")
    try:
        product = Product.objects.get(barcode=barcode)
        return JsonResponse({
            "found": True,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock,
            "id": product.id
        })
    except Product.DoesNotExist:
        return JsonResponse({"found": False})

def category_create(request):
    if request.method == "POST":
        name = request.POST["name"]
        Category.objects.create(name=name)
        return redirect("category_create")

    categories = Category.objects.all()

    return render(request, "core/category_create.html", {
        "categories": categories
    })
    
def alerts(request):
    today = timezone.now().date()
    soon_limit = today + timedelta(days=10)

    expired = Product.objects.filter(expiration_date__lt=today)
    soon = Product.objects.filter(expiration_date__range=[today, soon_limit])
    low_stock = Product.objects.filter(stock__lte=5)

    return render(request, "core/alerts.html", {
        "expired": expired,
        "soon": soon,
        "low_stock": low_stock,
    })
    
def home(request):
    today = timezone.now().date()
    soon_limit = today + timedelta(days=10)

    # Tus contadores
    expired_count = Product.objects.filter(expiration_date__lt=today).count()
    soon_count = Product.objects.filter(expiration_date__range=[today, soon_limit]).count()
    low_stock_count = Product.objects.filter(stock__lte=5).count()

    alerts_total = expired_count + soon_count + low_stock_count

    # 🔥 Lista de próximos a vencer (máximo 5 para el Dashboard)
    soon_products_list = Product.objects.filter(
        expiration_date__range=[today, soon_limit]
    ).order_by("expiration_date")[:5]

    return render(request, "core/home.html", {
        "alerts_total": alerts_total,
        "expired_count": expired_count,
        "soon_count": soon_count,
        "low_stock_count": low_stock_count,
        "soon_products_list": soon_products_list,  # 🔥 NUEVO
    })

def create_sale(request):
    """Vista para crear una nueva venta - VERSIÓN CORREGIDA"""
    
    # Obtener productos disponibles (con stock > 0)
    products = Product.objects.filter(stock__gt=0)
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            product_id = request.POST.get('product')
            quantity_str = request.POST.get('quantity', '0')
            
            # Validaciones básicas
            if not product_id:
                messages.error(request, "Debe seleccionar un producto")
                return render(request, 'core/create_sale.html', {
                    'products': products,
                    'error': "Debe seleccionar un producto"
                })
            
            try:
                quantity = int(quantity_str)
                if quantity <= 0:
                    raise ValueError
            except ValueError:
                messages.error(request, "La cantidad debe ser un número mayor a 0")
                return render(request, 'core/create_sale.html', {
                    'products': products,
                    'error': "La cantidad debe ser un número mayor a 0"
                })
            
            # Obtener producto
            product = get_object_or_404(Product, id=product_id)
            
            # Validar stock
            if quantity > product.stock:
                messages.error(request, f"No hay suficiente stock. Disponible: {product.stock} unidades")
                return render(request, 'core/create_sale.html', {
                    'products': products,
                    'error': f"No hay suficiente stock. Disponible: {product.stock} unidades"
                })
            
            # Usar transacción atómica
            with transaction.atomic():
                # CREAR LA VENTA - ¡SIN ESPECIFICAR ID!
                sale = Sale.objects.create(
                    date=timezone.now(),
                    total=Decimal('0.00')  # Inicializar en 0
                )
                
                print(f"Venta creada con ID: {sale.id}")  # Debug
                
                # Crear el item de venta
                subtotal = product.price * quantity
                sale_item = SaleItem.objects.create(
                    sale=sale,  # ¡Asociar con la venta recién creada!
                    product=product,
                    quantity=quantity,
                    unit_price=product.price,
                    subtotal=subtotal
                )
                
                # Actualizar stock del producto
                product.stock -= quantity
                product.save()
                
                # Actualizar total de la venta
                sale.total = subtotal
                sale.save()  # Esto llamará al método save() del modelo
                
                messages.success(request, 
                    f"✅ Venta #{sale.id} registrada exitosamente!\n"
                    f"Producto: {product.name}\n"
                    f"Cantidad: {quantity}\n"
                    f"Total: ${sale.total:.2f}"
                )
                
                return redirect('sale_detail', sale_id=sale.id)
                
        except Exception as e:
            messages.error(request, f"❌ Error al registrar la venta: {str(e)}")
            import traceback
            traceback.print_exc()  # Para debug en consola
            return render(request, 'core/create_sale.html', {
                'products': products,
                'error': f"Error: {str(e)}"
            })
    
    # GET request - mostrar formulario
    return render(request, 'core/create_sale.html', {
        'products': products
    })    

def sale_detail(request, sale_id):
    """Vista para ver el detalle de una venta"""
    sale = get_object_or_404(Sale, id=sale_id)
    
    # Calcular total si es necesario
    if sale.total == 0 and sale.items.exists():
        total = sum(item.subtotal for item in sale.items.all())
        sale.total = total
        sale.save(update_fields=['total'])
    
    context = {
        'sale': sale,
    }
    return render(request, 'core/sale_detail.html', context)



def sales_list(request):
    sales = Sale.objects.all().order_by('-date')
    
    # Calcular estadísticas
    total_sales = sales.count()
    total_revenue = sales.aggregate(Sum('total'))['total__sum'] or 0
    total_items = sum(item.quantity for sale in sales for item in sale.items.all())
    avg_sale = sales.aggregate(Avg('total'))['total__avg'] or 0
    
    # Filtrar por fechas si se especifica
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        sales = sales.filter(date__gte=date_from)
    if date_to:
        sales = sales.filter(date__lte=date_to)
    
    # Filtrar por rango de monto
    amount_range = request.GET.get('amount_range')
    if amount_range == '0-100':
        sales = sales.filter(total__gte=0, total__lte=100)
    elif amount_range == '100-500':
        sales = sales.filter(total__gte=100, total__lte=500)
    elif amount_range == '500-1000':
        sales = sales.filter(total__gte=500, total__lte=1000)
    elif amount_range == '1000+':
        sales = sales.filter(total__gte=1000)
    
    # Pasar datos adicionales para la tabla
    for sale in sales:
        # Calcular unidades totales por venta
        sale.total_units = sum(item.quantity for item in sale.items.all())
    
    context = {
        'sales': sales,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'total_items': total_items,
        'avg_sale': avg_sale,
    }
    
    return render(request, 'core/sales_list.html', context)

def sale_receipt(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)

    return HttpResponse(f"Recibo de la venta #{sale.id}")

def expiring_products(request):
    today = timezone.now().date()
    soon_limit = today + timedelta(days=10)

    products = Product.objects.filter(
        expiration_date__range=[today, soon_limit]
    ).order_by("expiration_date")

    return render(request, "core/expiring_products.html", {
        "products": products
    })


def add_product(request):
    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        expiration = request.POST.get("expiration_date")  # 🔥 NUEVO

        if expiration == "":
            expiration = None  # si el usuario no pone fecha

        Product.objects.create(
            name=name,
            price=price,
            stock=stock,
            expiration_date=expiration
        )

        return redirect("product_list")

    return render(request, "core/add_product.html")

def edit_product(request, product_id):
    product = Product.objects.get(id=product_id)

    if request.method == "POST":
        product.name = request.POST.get("name")
        product.price = request.POST.get("price")
        product.stock = request.POST.get("stock")

        expiration = request.POST.get("expiration_date")
        product.expiration_date = expiration if expiration != "" else None

        product.save()

        return redirect("product_list")

    return render(request, "core/edit_product.html", {"product": product})

def delete_product(request, product_id):
    product = Product.objects.get(id=product_id)

    if request.method == "POST":
        product.delete()
        return redirect("product_list")

    return render(request, "core/delete_product.html", {"product": product})

def add_sale(request):
    products = Product.objects.all()

    if request.method == "POST":
        product_id = request.POST.get("product")
        quantity = int(request.POST.get("quantity"))

        product = Product.objects.get(id=product_id)

        # Validar stock
        if quantity > product.stock:
            return render(request, "core/add_sale.html", {
                "products": products,
                "error": "No hay suficiente stock para esta venta."
            })

        price = product.price
        total = price * quantity

        # Registrar la venta
        Sale.objects.create(
            product=product,
            quantity=quantity,
            price=price,
            total=total
        )

        # Descontar stock automáticamente
        product.stock -= quantity
        product.save()

        return redirect("sales_list")

    return render(request, "core/add_sale.html", {"products": products})
