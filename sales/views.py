from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction, models
from decimal import Decimal
from .models import Sale, SaleItem, Customer, Payment, Return, ReturnItem, CashRegister, CashMovement
from inventory.models import Product, StockMovement

# ========== SALES ==========

@login_required
def sale_list(request):
    """Lista de ventas"""
    company = request.user.company
    sales = Sale.objects.filter(company=company).order_by('-created_at')
    
    # Filtros
    search = request.GET.get('search', '')
    payment_method = request.GET.get('payment_method', '')
    is_paid = request.GET.get('is_paid', '')
    
    if search:
        sales = sales.filter(
            Q(id__icontains=search) |
            Q(customer__name__icontains=search)
        )
    
    if payment_method:
        sales = sales.filter(payment_method=payment_method)
    
    if is_paid == 'paid':
        sales = sales.filter(is_paid=True)
    elif is_paid == 'pending':
        sales = sales.filter(is_paid=False)
    
    # Estadísticas
    total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
    
    context = {
        'sales': sales,
        'total_sales': total_sales,
        'search': search,
        'payment_method': payment_method,
        'is_paid_filter': is_paid,
    }
    return render(request, 'sales/sale_list.html', context)

@login_required
def sale_detail(request, pk):
    """Detalle de venta"""
    company = request.user.company
    sale = get_object_or_404(Sale, pk=pk, company=company)
    items = sale.items.all()
    payments = sale.payments.all()
    
    context = {
        'sale': sale,
        'items': items,
        'payments': payments,
    }
    return render(request, 'sales/sale_detail.html', context)

@login_required
def sale_create(request):
    """Crear nueva venta con soporte para productos por peso"""
    company = request.user.company
    
    if request.method == 'POST':
        try:
            # Datos básicos de la venta
            payment_method = request.POST.get('payment_method')
            customer_id = request.POST.get('customer') if payment_method == 'CREDIT' else None
            discount = Decimal(request.POST.get('discount', 0))
            notes = request.POST.get('notes', '')
            
            # Validar cliente si es fiado
            customer = None
            if payment_method == 'CREDIT':
                if not customer_id:
                    messages.error(request, 'Debe seleccionar un cliente para ventas fiadas.')
                    return redirect('sales:sale_create')
                
                customer = get_object_or_404(Customer, pk=customer_id, company=company)
                
                # Verificar límite de crédito
                if not customer.can_buy_on_credit:
                    messages.error(request, f'El cliente {customer.name} no puede comprar fiado. Límite de crédito excedido.')
                    return redirect('sales:sale_create')
            
            # Crear la venta
            sale = Sale.objects.create(
                company=company,
                customer=customer,
                payment_method=payment_method,
                discount=discount,
                notes=notes,
                is_paid=(payment_method != 'CREDIT'),
                created_by=request.user
            )
            
            # Procesar items del catálogo
            product_ids = request.POST.getlist('product_id[]')
            quantities = request.POST.getlist('quantity[]')
            
            if not product_ids:
                sale.delete()
                messages.error(request, 'Debe agregar al menos un producto.')
                return redirect('sales:sale_create')
            
            for i, product_id in enumerate(product_ids):
                if product_id:  # Producto del catálogo
                    quantity = Decimal(str(quantities[i]))
                    product = get_object_or_404(Product, pk=product_id, company=company)
                    
                    # Verificar stock
                    if product.stock < quantity:
                        sale.delete()
                        messages.error(request, f'Stock insuficiente para {product.name}. Disponible: {product.stock}')
                        return redirect('sales:sale_create')
                    
                    # Crear item de venta
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=quantity,
                        unit_price=product.sale_price
                    )
                    
                    # Descontar stock
                    previous_stock = product.stock
                    product.stock -= quantity
                    product.save()
                    
                    # Registrar movimiento de stock
                    StockMovement.objects.create(
                        product=product,
                        movement_type='OUT',
                        quantity=quantity,
                        previous_stock=previous_stock,
                        new_stock=product.stock,
                        reason=f'Venta #{sale.id}',
                        created_by=request.user
                    )
            
            # ✅ Procesar productos manuales (CON SOPORTE PARA PESO)
            manual_names = request.POST.getlist('manual_product_name[]')
            manual_prices = request.POST.getlist('manual_price[]')
            manual_weights = request.POST.getlist('manual_weight[]')
            manual_weight_units = request.POST.getlist('manual_weight_unit[]')
            
            manual_index = 0
            for i in range(len(manual_names)):
                if manual_names[i].strip():  # Si hay nombre
                    manual_name = manual_names[i].strip()
                    manual_price = Decimal(str(manual_prices[i])) if manual_prices[i] else Decimal('0')
                    
                    # Determinar cantidad según tipo de venta
                    if i < len(manual_weights) and manual_weights[i]:
                        # Venta por peso
                        weight_value = Decimal(str(manual_weights[i]))
                        weight_unit = manual_weight_units[i] if i < len(manual_weight_units) else 'kg'
                        
                        # Convertir a kg si es en gramos
                        if weight_unit == 'g':
                            quantity = weight_value / 1000  # Convertir gramos a kg
                        else:
                            quantity = weight_value
                        
                        # Actualizar nombre para mostrar el peso
                        manual_name = f"{manual_name} ({weight_value} {weight_unit})"
                    else:
                        # Venta por unidad
                        quantity = Decimal('1')
                    
                    # Crear producto temporal
                    temp_product = Product.objects.create(
                        company=company,
                        barcode=f'MANUAL-{sale.id}-{manual_index}',
                        name=manual_name,
                        cost_price=Decimal('0'),
                        sale_price=manual_price,
                        stock=Decimal('0'),
                        min_stock=Decimal('0'),
                        is_active=False,  # No aparecerá en el inventario
                        created_by=request.user
                    )
                    
                    # Crear item de venta
                    SaleItem.objects.create(
                        sale=sale,
                        product=temp_product,
                        quantity=quantity,
                        unit_price=manual_price
                    )
                    
                    manual_index += 1
            
            # Calcular totales
            sale.calculate_totals()
            
            # Si no es fiado, marcar como pagado
            if payment_method != 'CREDIT':
                sale.paid_amount = sale.total
                sale.is_paid = True
                sale.save()
            
            messages.success(request, f'Venta #{sale.id} registrada exitosamente.')
            return redirect('sales:sale_detail', pk=sale.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear venta: {str(e)}')
            return redirect('sales:sale_create')
    
    # GET request
    products = Product.objects.filter(company=company, is_active=True, stock__gt=0)
    customers = Customer.objects.filter(company=company, is_active=True)
    
    context = {
        'products': products,
        'customers': customers,
    }
    return render(request, 'sales/sale_form.html', context)

@login_required
def sale_delete(request, pk):
    """Eliminar venta (devolver stock)"""
    company = request.user.company
    sale = get_object_or_404(Sale, pk=pk, company=company)
    
    if request.method == 'POST':
        try:
            # Devolver stock
            for item in sale.items.all():
                product = item.product
                previous_stock = product.stock
                product.stock += item.quantity
                product.save()
                
                # Registrar movimiento
                StockMovement.objects.create(
                    product=product,
                    movement_type='RETURN',
                    quantity=item.quantity,
                    previous_stock=previous_stock,
                    new_stock=product.stock,
                    reason=f'Devolución venta #{sale.id}',
                    created_by=request.user
                )
            
            sale.delete()
            messages.success(request, f'Venta #{pk} eliminada y stock devuelto.')
            return redirect('sales:sale_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar venta: {str(e)}')
    
    context = {'sale': sale}
    return render(request, 'sales/sale_confirm_delete.html', context)

@login_required
def sale_receipt(request, pk):
    """Recibo de venta"""
    company = request.user.company
    sale = get_object_or_404(Sale, pk=pk, company=company)
    items = sale.items.all()
    
    context = {
        'sale': sale,
        'items': items,
    }
    return render(request, 'sales/sale_receipt.html', context)

@login_required
def print_receipt(request, pk):
    """Versión imprimible del recibo"""
    company = request.user.company
    sale = get_object_or_404(Sale, pk=pk, company=company)
    items = sale.items.all()
    
    context = {
        'sale': sale,
        'items': items,
    }
    return render(request, 'sales/print_receipt.html', context)

# ========== CUSTOMERS ==========

@login_required
def customer_list(request):
    """Lista de clientes"""
    company = request.user.company
    customers = Customer.objects.filter(company=company)
    
    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    context = {
        'customers': customers,
        'search': search,
    }
    return render(request, 'sales/customer_list.html', context)

@login_required
def customer_detail(request, pk):
    """Detalle de cliente"""
    company = request.user.company
    customer = get_object_or_404(Customer, pk=pk, company=company)
    sales = customer.sales.all().order_by('-created_at')
    pending_sales = customer.sales.filter(is_paid=False)
    
    context = {
        'customer': customer,
        'sales': sales,
        'pending_sales': pending_sales,
    }
    return render(request, 'sales/customer_detail.html', context)

@login_required
def customer_create(request):
    """Crear cliente"""
    company = request.user.company
    
    if request.method == 'POST':
        try:
            customer = Customer.objects.create(
                company=company,  # ← FILTRO POR EMPRESA
                name=request.POST.get('name'),
                phone=request.POST.get('phone', ''),
                email=request.POST.get('email', ''),
                address=request.POST.get('address', ''),
                credit_limit=request.POST.get('credit_limit', 0),
                notes=request.POST.get('notes', '')
            )
            messages.success(request, f'Cliente "{customer.name}" creado exitosamente.')
            return redirect('sales:customer_list')
        except Exception as e:
            messages.error(request, f'Error al crear cliente: {str(e)}')
    
    return render(request, 'sales/customer_form.html')

@login_required
def customer_update(request, pk):
    """Actualizar cliente"""
    company = request.user.company
    customer = get_object_or_404(Customer, pk=pk, company=company)
    
    if request.method == 'POST':
        try:
            customer.name = request.POST.get('name')
            customer.phone = request.POST.get('phone', '')
            customer.email = request.POST.get('email', '')
            customer.address = request.POST.get('address', '')
            customer.credit_limit = request.POST.get('credit_limit', 0)
            customer.notes = request.POST.get('notes', '')
            customer.save()
            
            messages.success(request, f'Cliente "{customer.name}" actualizado.')
            return redirect('sales:customer_detail', pk=customer.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar cliente: {str(e)}')
    
    context = {'customer': customer, 'is_update': True}
    return render(request, 'sales/customer_form.html', context)

@login_required
def customer_delete(request, pk):
    """Eliminar cliente"""
    company = request.user.company
    customer = get_object_or_404(Customer, pk=pk, company=company)
    
    if request.method == 'POST':
        customer.is_active = False
        customer.save()
        messages.success(request, f'Cliente "{customer.name}" desactivado.')
        return redirect('sales:customer_list')
    
    context = {'customer': customer}
    return render(request, 'sales/customer_confirm_delete.html', context)

# ========== CREDIT SALES (FIADOS) ==========

@login_required
def credit_sales(request):
    """Lista de ventas fiadas"""
    company = request.user.company
    sales = Sale.objects.filter(company=company, payment_method='CREDIT').order_by('-created_at')
    
    total_credit = sales.aggregate(total=Sum('total'))['total'] or 0
    total_pending = sales.filter(is_paid=False).aggregate(total=Sum('total'))['total'] or 0
    
    context = {
        'sales': sales,
        'total_credit': total_credit,
        'total_pending': total_pending,
    }
    return render(request, 'sales/credit_sales.html', context)

@login_required
def pending_credits(request):
    """Ventas fiadas pendientes"""
    company = request.user.company
    sales = Sale.objects.filter(company=company, payment_method='CREDIT', is_paid=False).order_by('-created_at')
    
    total_pending = sales.aggregate(total=Sum('total'))['total'] or 0
    
    context = {
        'sales': sales,
        'total_pending': total_pending,
    }
    return render(request, 'sales/pending_credits.html', context)

@login_required
def add_payment(request, pk):
    """Agregar pago a venta fiada"""
    company = request.user.company
    sale = get_object_or_404(Sale, pk=pk, company=company)
    
    if request.method == 'POST':
        try:
            amount = Decimal(str(request.POST.get('amount', 0)))
            payment_method = request.POST.get('payment_method', 'CASH')
            notes = request.POST.get('notes', '')
            
            if amount <= 0:
                messages.error(request, 'El monto debe ser mayor a 0.')
                return redirect('sales:add_payment', pk=pk)
            
            if amount > sale.pending_amount:
                messages.error(request, f'El monto no puede ser mayor al pendiente (${sale.pending_amount}).')
                return redirect('sales:add_payment', pk=pk)
            
            Payment.objects.create(
                sale=sale,
                amount=amount,
                payment_method=payment_method,
                notes=notes,
                created_by=request.user
            )
            
            messages.success(request, f'Pago de ${amount} registrado exitosamente.')
            return redirect('sales:sale_detail', pk=sale.pk)
        except Exception as e:
            messages.error(request, f'Error al registrar pago: {str(e)}')
    
    context = {'sale': sale}
    return render(request, 'sales/add_payment.html', context)

# ========== PAYMENTS ==========

@login_required
def payment_list(request):
    """Lista de pagos"""
    company = request.user.company
    payments = Payment.objects.filter(sale__company=company).order_by('-created_at')
    
    total_payments = payments.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'payments': payments,
        'total_payments': total_payments,
    }
    return render(request, 'sales/payment_list.html', context)

@login_required
def payment_delete(request, pk):
    """Eliminar pago"""
    company = request.user.company
    payment = get_object_or_404(Payment, pk=pk, sale__company=company)
    sale = payment.sale
    
    if request.method == 'POST':
        payment.delete()
        
        # Recalcular totales de la venta
        sale.paid_amount = sum(p.amount for p in sale.payments.all())
        sale.is_paid = sale.paid_amount >= sale.total
        sale.save()
        
        messages.success(request, 'Pago eliminado.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    context = {'payment': payment}
    return render(request, 'sales/payment_confirm_delete.html', context)

# ========== RETURNS (DEVOLUCIONES) ==========

@login_required
def create_return(request, sale_pk):
    """Crear devolución de una venta"""
    company = request.user.company
    sale = get_object_or_404(Sale, pk=sale_pk, company=company)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                reason = request.POST.get('reason', '')
                refund_method = request.POST.get('refund_method', 'CASH')
                
                # Crear devolución
                return_obj = Return.objects.create(
                    sale=sale,
                    reason=reason,
                    refund_method=refund_method,
                    created_by=request.user
                )
                
                total_amount = Decimal('0')
                items_returned = 0
                
                # Procesar items devueltos
                for key, value in request.POST.items():
                    if key.startswith('return_qty_'):
                        sale_item_id = int(key.replace('return_qty_', ''))
                        quantity = Decimal(str(value)) if value else Decimal('0')
                        
                        if quantity > 0:
                            sale_item = SaleItem.objects.get(id=sale_item_id)
                            
                            # Validar que no devuelva más de lo comprado
                            already_returned = sale_item.return_items.aggregate(
                                total=models.Sum('quantity')
                            )['total'] or Decimal('0')
                            
                            max_returnable = sale_item.quantity - already_returned
                            
                            if quantity > max_returnable:
                                raise ValueError(f"No puedes devolver más de {max_returnable} unidades de {sale_item.product.name}")
                            
                            # Crear item de devolución
                            return_item = ReturnItem.objects.create(
                                return_obj=return_obj,
                                sale_item=sale_item,
                                quantity=quantity,
                                unit_price=sale_item.unit_price
                            )
                            
                            # Devolver stock al inventario
                            product = sale_item.product
                            previous_stock = product.stock
                            product.stock += quantity
                            product.save()
                            
                            # Registrar movimiento de stock
                            StockMovement.objects.create(
                                product=product,
                                movement_type='IN',
                                quantity=quantity,
                                previous_stock=previous_stock,
                                new_stock=product.stock,
                                reason=f'Devolución de venta #{sale.id}',
                                created_by=request.user
                            )
                            
                            total_amount += return_item.subtotal
                            items_returned += 1
                
                if items_returned == 0:
                    return_obj.delete()
                    messages.error(request, 'Debes seleccionar al menos un producto para devolver.')
                    return redirect('sales:create_return', sale_pk=sale.pk)
                
                # Actualizar totales
                return_obj.total_amount = total_amount
                
                # Determinar tipo de devolución
                total_items_in_sale = sale.items.count()
                if items_returned == total_items_in_sale:
                    return_obj.return_type = 'TOTAL'
                else:
                    return_obj.return_type = 'PARTIAL'
                
                return_obj.save()
                
                # Si la venta era fiada, ajustar deuda del cliente
                if sale.payment_method == 'CREDIT' and sale.customer:
                    sale.customer.current_debt -= total_amount
                    sale.customer.save()
                
                messages.success(request, f'✅ Devolución procesada exitosamente. Total reintegrado: ${total_amount}')
                return redirect('sales:return_detail', pk=return_obj.pk)
                
        except Exception as e:
            messages.error(request, f'❌ Error al procesar devolución: {str(e)}')
    
    # Calcular qué se puede devolver de cada item
    items_with_returns = []
    for item in sale.items.all():
        already_returned = item.return_items.aggregate(
            total=models.Sum('quantity')
        )['total'] or Decimal('0')
        
        max_returnable = item.quantity - already_returned
        
        items_with_returns.append({
            'item': item,
            'already_returned': already_returned,
            'max_returnable': max_returnable,
        })
    
    context = {
        'sale': sale,
        'items_with_returns': items_with_returns,
    }
    return render(request, 'sales/create_return.html', context)

@login_required
def return_detail(request, pk):
    """Ver detalle de una devolución"""
    company = request.user.company
    return_obj = get_object_or_404(Return, pk=pk, sale__company=company)
    
    context = {
        'return_obj': return_obj,
    }
    return render(request, 'sales/return_detail.html', context)

@login_required
def return_list(request):
    """Lista de todas las devoluciones"""
    company = request.user.company
    returns = Return.objects.filter(sale__company=company).select_related('sale', 'created_by')
    
    # Filtros
    search = request.GET.get('search', '')
    if search:
        returns = returns.filter(
            models.Q(sale__id__icontains=search) |
            models.Q(reason__icontains=search)
        )
    
    context = {
        'returns': returns,
        'search': search,
    }
    return render(request, 'sales/return_list.html', context)

@login_required
def cancel_return(request, pk):
    """Cancelar una devolución (volver stock atrás)"""
    company = request.user.company
    return_obj = get_object_or_404(Return, pk=pk, sale__company=company)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Quitar stock de vuelta
                for item in return_obj.items.all():
                    product = item.sale_item.product
                    previous_stock = product.stock
                    product.stock -= item.quantity
                    product.save()
                    
                    # Registrar movimiento
                    StockMovement.objects.create(
                        product=product,
                        movement_type='OUT',
                        quantity=item.quantity,
                        previous_stock=previous_stock,
                        new_stock=product.stock,
                        reason=f'Cancelación de devolución #{return_obj.id}',
                        created_by=request.user
                    )
                
                # Si era fiada, volver a sumar la deuda
                if return_obj.sale.payment_method == 'CREDIT' and return_obj.sale.customer:
                    return_obj.sale.customer.current_debt += return_obj.total_amount
                    return_obj.sale.customer.save()
                
                # Eliminar devolución
                return_obj.delete()
                
                messages.success(request, '✅ Devolución cancelada exitosamente.')
                return redirect('sales:return_list')
        except Exception as e:
            messages.error(request, f'❌ Error al cancelar devolución: {str(e)}')
    
    return render(request, 'sales/cancel_return.html', {'return_obj': return_obj})

# ========== CASH REGISTER ==========

@login_required
def cash_register_open(request):
    """Abrir caja del día"""
    company = request.user.company
    
    # Verificar si ya hay caja abierta
    if CashRegister.has_open_register(request.user):
        messages.warning(request, 'Ya tienes una caja abierta.')
        return redirect('sales:cash_register_current')
    
    if request.method == 'POST':
        opening_amount = Decimal(str(request.POST.get('opening_amount', 0)))
        notes = request.POST.get('notes', '')
        
        cash_register = CashRegister.objects.create(
            company=company,  # ← FILTRO POR EMPRESA
            user=request.user,
            opening_amount=opening_amount,
            opening_notes=notes,
            status='OPEN'
        )
        
        messages.success(request, f'Caja abierta con ${opening_amount}')
        return redirect('sales:cash_register_current')
    
    return render(request, 'sales/cash_register_open.html')

@login_required
def cash_register_current(request):
    """Ver caja actual abierta"""
    cash_register = CashRegister.get_current(request.user)
    
    if not cash_register:
        messages.info(request, 'No hay caja abierta. Abre una nueva caja.')
        return redirect('sales:cash_register_open')
    
    # Calcular totales actualizados
    cash_register.calculate_totals()
    
    # Obtener ventas de hoy
    company = request.user.company
    sales = Sale.objects.filter(
        company=company,
        created_at__gte=cash_register.opened_at
    ).order_by('-created_at')[:10]
    
    # Movimientos manuales
    movements = cash_register.movements.all()
    
    context = {
        'cash_register': cash_register,
        'sales': sales,
        'movements': movements,
    }
    return render(request, 'sales/cash_register_current.html', context)

@login_required
def cash_register_close(request):
    """Cerrar caja del día"""
    cash_register = CashRegister.get_current(request.user)
    
    if not cash_register:
        messages.error(request, 'No hay caja abierta para cerrar.')
        return redirect('sales:cash_register_open')
    
    if request.method == 'POST':
        closing_amount = Decimal(str(request.POST.get('closing_amount', 0)))
        notes = request.POST.get('notes', '')
        
        difference = cash_register.close_register(closing_amount, notes)
        
        if difference == 0:
            messages.success(request, f'¡Caja cerrada! Todo cuadra perfectamente.')
        elif difference > 0:
            messages.warning(request, f'Caja cerrada con SOBRANTE de ${difference}')
        else:
            messages.warning(request, f'Caja cerrada con FALTANTE de ${abs(difference)}')
        
        return redirect('sales:cash_register_detail', pk=cash_register.pk)
    
    # Calcular totales antes de mostrar
    cash_register.calculate_totals()
    
    context = {
        'cash_register': cash_register,
    }
    return render(request, 'sales/cash_register_close.html', context)

@login_required
def cash_register_detail(request, pk):
    """Ver detalle de una caja cerrada"""
    company = request.user.company
    cash_register = get_object_or_404(CashRegister, pk=pk, company=company)
    
    # Ventas de esta caja
    sales = Sale.objects.filter(
        company=company,
        created_at__gte=cash_register.opened_at,
        created_at__lte=cash_register.closed_at if cash_register.closed_at else timezone.now()
    )
    
    context = {
        'cash_register': cash_register,
        'sales': sales,
    }
    return render(request, 'sales/cash_register_detail.html', context)

@login_required
def cash_register_list(request):
    """Historial de cajas"""
    company = request.user.company
    cash_registers = CashRegister.objects.filter(company=company)
    
    # Filtros
    status = request.GET.get('status', '')
    if status:
        cash_registers = cash_registers.filter(status=status)
    
    context = {
        'cash_registers': cash_registers,
        'status': status,
    }
    return render(request, 'sales/cash_register_list.html', context)

@login_required
def add_cash_movement(request):
    """Agregar movimiento de efectivo manual"""
    cash_register = CashRegister.get_current(request.user)
    
    if not cash_register:
        messages.error(request, 'No hay caja abierta.')
        return redirect('sales:cash_register_open')
    
    if request.method == 'POST':
        movement_type = request.POST.get('movement_type')
        amount = Decimal(str(request.POST.get('amount', 0)))
        reason = request.POST.get('reason', '')
        
        CashMovement.objects.create(
            cash_register=cash_register,
            movement_type=movement_type,
            amount=amount,
            reason=reason,
            created_by=request.user
        )
        
        if movement_type == 'IN':
            messages.success(request, f'Ingreso de ${amount} registrado')
        else:
            messages.success(request, f'Egreso de ${amount} registrado')
        
        return redirect('sales:cash_register_current')
    
    return render(request, 'sales/add_cash_movement.html', {'cash_register': cash_register})