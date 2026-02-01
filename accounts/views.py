from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from django.http import FileResponse, Http404, JsonResponse
from django.core.management import call_command
from django.conf import settings as django_settings
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path
from datetime import datetime
import os
import glob
import json

from inventory.models import Product
from sales.models import Sale, Customer
from .models import SystemConfig, Company  # ✅ IMPORTAR Company

# ========== AUTHENTICATION ==========

@transaction.atomic
def register(request):
    """Vista para registro de nuevos usuarios"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # Guardar el usuario
            user = form.save()
            
            # ✅ Crear empresa automáticamente para el nuevo usuario
            try:
                Company.objects.create(
                    owner=user,
                    name=f"Tienda de {user.username}"
                )
                
                # Iniciar sesión automáticamente
                login(request, user)
                messages.success(request, f'✅ ¡Bienvenido {user.username}! Tu tienda está lista.')
                return redirect('inventory:home')
            except Exception as e:
                # Si falla la creación de la empresa, eliminar el usuario
                user.delete()
                messages.error(request, f'❌ Error al crear empresa: {str(e)}')
                return redirect('accounts:register')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    """Vista de login (si tienes una personalizada)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'¡Bienvenido {user.username}!')
            
            # Redirigir a la página que intentaba acceder o al home
            next_url = request.GET.get('next', 'inventory:home')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    
    return render(request, 'accounts/login.html')

def user_logout(request):
    """Cerrar sesión"""
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente')
    return redirect('accounts:login')

# ========== PROFILE ==========

@login_required
def profile(request):
    """Perfil del usuario"""
    user = request.user
    
    # ✅ Filtrar por company si existe
    if hasattr(request, 'company') and request.company:
        products_created = Product.objects.filter(
            company=request.company,
            created_by=user
        ).count()
        sales_created = Sale.objects.filter(
            company=request.company,
            created_by=user
        ).count()
        total_sales_value = Sale.objects.filter(
            company=request.company,
            created_by=user
        ).aggregate(total=Sum('total'))['total'] or 0
    else:
        products_created = 0
        sales_created = 0
        total_sales_value = 0
    
    context = {
        'user': user,
        'products_created': products_created,
        'sales_created': sales_created,
        'total_sales_value': total_sales_value,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def profile_edit(request):
    """Editar perfil"""
    user = request.user
    
    if request.method == 'POST':
        try:
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.save()
            
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('accounts:profile')
        except Exception as e:
            messages.error(request, f'Error al actualizar perfil: {str(e)}')
    
    context = {'user': user}
    return render(request, 'accounts/profile_edit.html', context)

# ========== SETTINGS ==========

@login_required
def settings(request):
    """Configuración de la cuenta y del sistema"""
    user = request.user
    config = SystemConfig.get_config()
    
    if request.method == 'POST':
        try:
            # Actualizar configuración del sistema
            config.enable_credits = request.POST.get('enable_credits') == 'on'
            config.enable_categories = request.POST.get('enable_categories') == 'on'
            config.enable_expiration_alerts = request.POST.get('enable_expiration_alerts') == 'on'
            config.enable_low_stock_alerts = request.POST.get('enable_low_stock_alerts') == 'on'
            config.enable_barcode_scanner = request.POST.get('enable_barcode_scanner') == 'on'
            config.enable_reports = request.POST.get('enable_reports') == 'on'
            config.enable_customers = request.POST.get('enable_customers') == 'on'
            
            config.company_name = request.POST.get('company_name', 'StockMaster')
            config.expiration_alert_days = int(request.POST.get('expiration_alert_days', 30))
            
            config.save()
            
            messages.success(request, 'Configuración actualizada exitosamente.')
            return redirect('accounts:settings')
        except Exception as e:
            messages.error(request, f'Error al actualizar configuración: {str(e)}')
    
    # ✅ FILTRAR ESTADÍSTICAS POR COMPANY DEL USUARIO
    if hasattr(request, 'company') and request.company:
        total_products = Product.objects.filter(
            company=request.company,
            is_active=True
        ).count()
        
        total_sales = Sale.objects.filter(
            company=request.company
        ).count()
        
        # Información de la empresa
        company_name = request.company.name
        company_created = request.company.created_at
    else:
        total_products = 0
        total_sales = 0
        company_name = "Sin empresa asignada"
        company_created = None
    
    context = {
        'user': user,
        'config': config,
        'total_products': total_products,
        'total_sales': total_sales,
        'company_name': company_name,
        'company_created': company_created,
    }
    return render(request, 'accounts/settings.html', context)

# ========== USER MANAGEMENT (Solo para admins) ==========

@login_required
def user_list(request):
    """Lista de usuarios (solo admins)"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('inventory:home')
    
    users = User.objects.all()
    context = {'users': users}
    return render(request, 'accounts/user_list.html', context)

@login_required
def user_create(request):
    """Crear usuario (solo admins)"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('inventory:home')
    
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')
            is_staff = request.POST.get('is_staff') == 'on'
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'El nombre de usuario ya existe.')
                return redirect('accounts:user_create')
            
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_staff=is_staff
            )
            
            # Crear empresa para el nuevo usuario
            Company.objects.create(
                owner=user,
                name=f"Tienda de {username}"
            )
            
            messages.success(request, f'Usuario "{user.username}" creado exitosamente.')
            return redirect('accounts:user_list')
        except Exception as e:
            messages.error(request, f'Error al crear usuario: {str(e)}')
    
    return render(request, 'accounts/user_form.html')

@login_required
def user_update(request, pk):
    """Actualizar usuario (solo admins)"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('inventory:home')
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        try:
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.is_staff = request.POST.get('is_staff') == 'on'
            user.is_active = request.POST.get('is_active') == 'on'
            
            # Cambiar contraseña solo si se proporciona
            new_password = request.POST.get('password', '')
            if new_password:
                user.set_password(new_password)
            
            user.save()
            
            messages.success(request, f'Usuario "{user.username}" actualizado.')
            return redirect('accounts:user_list')
        except Exception as e:
            messages.error(request, f'Error al actualizar usuario: {str(e)}')
    
    context = {'user_obj': user, 'is_update': True}
    return render(request, 'accounts/user_form.html', context)

@login_required
def user_delete(request, pk):
    """Desactivar usuario (solo admins)"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('inventory:home')
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        if user.id == request.user.id:
            messages.error(request, 'No puedes desactivar tu propia cuenta.')
            return redirect('accounts:user_list')
        
        user.is_active = False
        user.save()
        messages.success(request, f'Usuario "{user.username}" desactivado.')
        return redirect('accounts:user_list')
    
    context = {'user_obj': user}
    return render(request, 'accounts/user_confirm_delete.html', context)

# ========== BACKUP MANAGEMENT ==========

@login_required
@staff_member_required
def backup_list(request):
    """Lista de backups disponibles"""
    backup_dir = os.path.join(django_settings.BASE_DIR, 'backups')
    
    # Crear directorio si no existe
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Obtener lista de backups (archivos .zip)
    backups = []
    zip_files = glob.glob(os.path.join(backup_dir, '*.zip'))
    
    for file in zip_files:
        try:
            file_stat = os.stat(file)
            size_mb = file_stat.st_size / (1024 * 1024)
            created = datetime.fromtimestamp(file_stat.st_ctime)
            
            backups.append({
                'filename': os.path.basename(file),
                'path': file,
                'size': f'{size_mb:.2f}',
                'created': created,
            })
        except Exception as e:
            print(f"Error procesando {file}: {e}")
            continue
    
    # Ordenar por fecha (más reciente primero)
    backups.sort(key=lambda x: x['created'], reverse=True)
    
    context = {
        'backups': backups,
        'total_backups': len(backups),
        'backup_dir': backup_dir,
    }
    return render(request, 'accounts/backup_list.html', context)

@staff_member_required
def create_backup(request):
    """Crear nuevo backup"""
    if request.method == 'POST':
        try:
            call_command('create_backup')
            messages.success(request, '✅ Backup creado exitosamente')
        except Exception as e:
            messages.error(request, f'❌ Error al crear backup: {str(e)}')
        
        return redirect('accounts:backup_list')
    
    return render(request, 'accounts/create_backup.html')

@staff_member_required
def download_backup(request, filename):
    """Descargar archivo de backup"""
    backup_dir = os.path.join(django_settings.BASE_DIR, 'backups')
    file_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(file_path):
        raise Http404('Backup no encontrado')
    
    if not file_path.startswith(backup_dir):
        raise Http404('Acceso no autorizado')
    
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@staff_member_required
def delete_backup(request, filename):
    """Eliminar backup"""
    if request.method == 'POST':
        backup_dir = os.path.join(django_settings.BASE_DIR, 'backups')
        file_path = os.path.join(backup_dir, filename)
        
        if os.path.exists(file_path) and file_path.startswith(backup_dir):
            os.remove(file_path)
            messages.success(request, f'Backup {filename} eliminado')
        else:
            messages.error(request, 'Backup no encontrado')
        
        return redirect('accounts:backup_list')
    
    return render(request, 'accounts/delete_backup.html', {'filename': filename})

@staff_member_required
def clean_old_backups(request):
    """Eliminar backups antiguos (mantener solo los últimos 10)"""
    if request.method == 'POST':
        backup_dir = os.path.join(django_settings.BASE_DIR, 'backups')
        files = sorted(
            glob.glob(os.path.join(backup_dir, 'backup_*.zip')),
            key=os.path.getctime,
            reverse=True
        )
        
        deleted = 0
        for file in files[10:]:
            os.remove(file)
            deleted += 1
        
        messages.success(request, f'✅ {deleted} backup(s) antiguos eliminados')
        return redirect('accounts:backup_list')

# ========== CHATBOT ==========

@login_required
def chatbot_view(request):
    """Vista principal del chatbot"""
    return render(request, 'chatbot/chatbot.html')

@login_required
@csrf_exempt
def chatbot_api(request):
    """API del chatbot que procesa mensajes"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Mensaje vacío'}, status=400)
        
        api_key = getattr(django_settings, 'GEMINI_API_KEY', None)
        if not api_key:
            return JsonResponse({
                'response': '⚠️ API Key no configurada',
                'status': 'success'
            })
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        context = get_system_context(request.user, request.company if hasattr(request, 'company') else None)
        
        system_prompt = f"""Eres un asistente virtual amigable de StockMaster, un sistema de gestión de inventario y ventas.

INFORMACIÓN DEL SISTEMA:
{context}

INSTRUCCIONES:
- Ayuda al usuario a usar el sistema
- Sé MUY breve (máximo 3-4 líneas)
- Usa emojis cuando sea apropiado
- Da pasos claros y concretos
- Si preguntan cómo hacer algo, explica los pasos

Responde en español y de forma amigable."""

        model = genai.GenerativeModel('models/gemini-2.5-flash')
        full_prompt = f"{system_prompt}\n\nUsuario: {user_message}\nAsistente:"
        response = model.generate_content(full_prompt)
        
        return JsonResponse({
            'response': response.text,
            'status': 'success'
        })
        
    except Exception as e:
        import traceback
        print("ERROR EN CHATBOT:")
        print(traceback.format_exc())
        
        return JsonResponse({
            'response': f'❌ Error: {str(e)}',
            'status': 'success'
        })

def get_system_context(user, company=None):
    """Obtener contexto del sistema para el chatbot"""
    context = []
    
    # ✅ Filtrar por company si existe
    if company:
        total_products = Product.objects.filter(company=company, is_active=True).count()
        low_stock = Product.objects.filter(company=company, is_active=True, stock__lte=5).count()
        recent_sales = Sale.objects.filter(company=company).count()
        top_products = Product.objects.filter(company=company, is_active=True).values_list('name', flat=True)[:10]
    else:
        total_products = Product.objects.filter(is_active=True).count()
        low_stock = Product.objects.filter(is_active=True, stock__lte=5).count()
        recent_sales = Sale.objects.count()
        top_products = Product.objects.filter(is_active=True).values_list('name', flat=True)[:10]
    
    context.append(f"- Total de productos activos: {total_products}")
    
    if low_stock > 0:
        context.append(f"- ⚠️ Hay {low_stock} productos con stock bajo")
    
    context.append(f"- Total de ventas registradas: {recent_sales}")
    
    if top_products:
        context.append(f"- Algunos productos disponibles: {', '.join(top_products)}")
    
    return '\n'.join(context)

@login_required
def search_products_for_chat(request):
    """Buscar productos para el chatbot"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'products': []})
    
    # ✅ Filtrar por company si existe
    filters = {'is_active': True, 'name__icontains': query}
    if hasattr(request, 'company') and request.company:
        filters['company'] = request.company
    
    products = Product.objects.filter(**filters)[:5]
    
    products_data = [{
        'id': p.id,
        'name': p.name,
        'barcode': p.barcode,
        'price': float(p.sale_price),
        'stock': float(p.stock),
    } for p in products]
    
    return JsonResponse({'products': products_data})