from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import datetime, timedelta
from inventory.models import Category, Product
from sales.models import Customer, Sale, SaleItem

class Command(BaseCommand):
    help = 'Carga datos de prueba en la base de datos'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('🚀 Iniciando carga de datos de prueba...'))
        
        # Obtener o crear usuario
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write(self.style.SUCCESS('✅ Usuario admin creado'))
        
        # Crear Categorías
        self.stdout.write('📁 Creando categorías...')
        categories_data = [
            {'name': 'Bebidas', 'description': 'Gaseosas, jugos, agua'},
            {'name': 'Snacks', 'description': 'Papas fritas, galletitas, golosinas'},
            {'name': 'Lácteos', 'description': 'Leche, yogurt, queso'},
            {'name': 'Almacén', 'description': 'Arroz, fideos, enlatados'},
            {'name': 'Limpieza', 'description': 'Detergente, lavandina, jabón'},
            {'name': 'Panadería', 'description': 'Pan, facturas, galletas'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat.name] = cat
            if created:
                self.stdout.write(f'  ✓ {cat.name}')
        
        # Crear Productos
        self.stdout.write('📦 Creando productos...')
        products_data = [
            # Bebidas
            {'barcode': '7790001001', 'name': 'Coca-Cola 500ml', 'category': 'Bebidas', 'cost': 450, 'price': 600, 'stock': 24},
            {'barcode': '7790001002', 'name': 'Coca-Cola 1.5L', 'category': 'Bebidas', 'cost': 850, 'price': 1200, 'stock': 12},
            {'barcode': '7790001003', 'name': 'Sprite 500ml', 'category': 'Bebidas', 'cost': 420, 'price': 580, 'stock': 18},
            {'barcode': '7790001004', 'name': 'Agua Mineral 500ml', 'category': 'Bebidas', 'cost': 250, 'price': 400, 'stock': 30},
            {'barcode': '7790001005', 'name': 'Jugo Baggio 1L', 'category': 'Bebidas', 'cost': 380, 'price': 550, 'stock': 15},
            
            # Snacks
            {'barcode': '7790002001', 'name': 'Papas Lays 150g', 'category': 'Snacks', 'cost': 420, 'price': 650, 'stock': 20},
            {'barcode': '7790002002', 'name': 'Doritos 100g', 'category': 'Snacks', 'cost': 380, 'price': 600, 'stock': 15},
            {'barcode': '7790002003', 'name': 'Oreo 118g', 'category': 'Snacks', 'cost': 320, 'price': 500, 'stock': 25},
            {'barcode': '7790002004', 'name': 'Chocolinas 170g', 'category': 'Snacks', 'cost': 280, 'price': 450, 'stock': 18},
            {'barcode': '7790002005', 'name': 'Alfajor Jorgito', 'category': 'Snacks', 'cost': 180, 'price': 300, 'stock': 40},
            
            # Lácteos
            {'barcode': '7790003001', 'name': 'Leche La Serenísima 1L', 'category': 'Lácteos', 'cost': 550, 'price': 800, 'stock': 20, 'days': 7},
            {'barcode': '7790003002', 'name': 'Yogurt Sancor 190g', 'category': 'Lácteos', 'cost': 280, 'price': 450, 'stock': 30, 'days': 10},
            {'barcode': '7790003003', 'name': 'Queso Cremoso 200g', 'category': 'Lácteos', 'cost': 650, 'price': 950, 'stock': 10, 'days': 15},
            
            # Almacén
            {'barcode': '7790004001', 'name': 'Arroz Gallo Oro 1kg', 'category': 'Almacén', 'cost': 850, 'price': 1200, 'stock': 15},
            {'barcode': '7790004002', 'name': 'Fideos Matarazzo 500g', 'category': 'Almacén', 'cost': 420, 'price': 650, 'stock': 25},
            {'barcode': '7790004003', 'name': 'Aceite Cocinero 900ml', 'category': 'Almacén', 'cost': 1200, 'price': 1800, 'stock': 8},
            {'barcode': '7790004004', 'name': 'Azúcar Ledesma 1kg', 'category': 'Almacén', 'cost': 680, 'price': 1000, 'stock': 12},
            {'barcode': '7790004005', 'name': 'Yerba Playadito 1kg', 'category': 'Almacén', 'cost': 1500, 'price': 2200, 'stock': 10},
            
            # Limpieza
            {'barcode': '7790005001', 'name': 'Detergente Magistral 500ml', 'category': 'Limpieza', 'cost': 380, 'price': 600, 'stock': 15},
            {'barcode': '7790005002', 'name': 'Lavandina Ayudín 1L', 'category': 'Limpieza', 'cost': 420, 'price': 650, 'stock': 12},
            {'barcode': '7790005003', 'name': 'Jabón Dove 90g', 'category': 'Limpieza', 'cost': 280, 'price': 450, 'stock': 20},
            
            # Panadería
            {'barcode': '7790006001', 'name': 'Pan Lactal Bimbo', 'category': 'Panadería', 'cost': 850, 'price': 1300, 'stock': 10, 'days': 5},
            {'barcode': '7790006002', 'name': 'Medialunas x6', 'category': 'Panadería', 'cost': 550, 'price': 900, 'stock': 15, 'days': 2},
        ]
        
        products_created = []
        for prod_data in products_data:
            category = categories.get(prod_data['category'])
            
            # Fecha de vencimiento si aplica
            expiration = None
            if 'days' in prod_data:
                expiration = datetime.now().date() + timedelta(days=prod_data['days'])
            
            prod, created = Product.objects.get_or_create(
                barcode=prod_data['barcode'],
                defaults={
                    'name': prod_data['name'],
                    'category': category,
                    'cost_price': Decimal(str(prod_data['cost'])),
                    'sale_price': Decimal(str(prod_data['price'])),
                    'stock': Decimal(str(prod_data['stock'])),
                    'min_stock': Decimal('5'),
                    'expiration_date': expiration,
                    'created_by': user,
                }
            )
            if created:
                products_created.append(prod)
                self.stdout.write(f'  ✓ {prod.name}')
        
        # Crear Clientes
        self.stdout.write('👥 Creando clientes...')
        customers_data = [
            {'name': 'Juan Pérez', 'phone': '11-2345-6789', 'credit_limit': 10000},
            {'name': 'María González', 'phone': '11-3456-7890', 'credit_limit': 15000},
            {'name': 'Carlos Rodríguez', 'phone': '11-4567-8901', 'credit_limit': 8000},
            {'name': 'Ana Martínez', 'phone': '11-5678-9012', 'credit_limit': 12000},
            {'name': 'Luis Fernández', 'phone': '11-6789-0123', 'credit_limit': 5000},
        ]
        
        customers = []
        for cust_data in customers_data:
            cust, created = Customer.objects.get_or_create(
                name=cust_data['name'],
                defaults={
                    'phone': cust_data['phone'],
                    'credit_limit': Decimal(str(cust_data['credit_limit'])),
                }
            )
            if created:
                customers.append(cust)
                self.stdout.write(f'  ✓ {cust.name}')
        
        # Crear Ventas
        self.stdout.write('💰 Creando ventas...')
        if products_created and customers:
            # Venta 1: Normal - Efectivo
            sale1 = Sale.objects.create(
                payment_method='CASH',
                is_paid=True,
                created_by=user
            )
            SaleItem.objects.create(
                sale=sale1,
                product=products_created[0],
                quantity=Decimal('2'),
                unit_price=products_created[0].sale_price
            )
            SaleItem.objects.create(
                sale=sale1,
                product=products_created[5],
                quantity=Decimal('1'),
                unit_price=products_created[5].sale_price
            )
            sale1.calculate_totals()
            self.stdout.write(f'  ✓ Venta #{sale1.id} - Efectivo')
            
            # Venta 2: Fiada - Con pago parcial
            sale2 = Sale.objects.create(
                customer=customers[0],
                payment_method='CREDIT',
                is_paid=False,
                created_by=user
            )
            SaleItem.objects.create(
                sale=sale2,
                product=products_created[1],
                quantity=Decimal('3'),
                unit_price=products_created[1].sale_price
            )
            SaleItem.objects.create(
                sale=sale2,
                product=products_created[13],
                quantity=Decimal('1'),
                unit_price=products_created[13].sale_price
            )
            sale2.calculate_totals()
            # Agregar pago parcial
            from sales.models import Payment
            Payment.objects.create(
                sale=sale2,
                amount=Decimal('2000'),
                payment_method='CASH',
                created_by=user
            )
            self.stdout.write(f'  ✓ Venta #{sale2.id} - Fiada (pago parcial)')
            
            # Venta 3: Tarjeta
            sale3 = Sale.objects.create(
                payment_method='CARD',
                is_paid=True,
                created_by=user
            )
            SaleItem.objects.create(
                sale=sale3,
                product=products_created[9],
                quantity=Decimal('5'),
                unit_price=products_created[9].sale_price
            )
            sale3.calculate_totals()
            self.stdout.write(f'  ✓ Venta #{sale3.id} - Tarjeta')
        
        self.stdout.write(self.style.SUCCESS('\n✨ ¡Datos de prueba cargados exitosamente!'))
        self.stdout.write(self.style.SUCCESS(f'✅ {len(categories)} categorías'))
        self.stdout.write(self.style.SUCCESS(f'✅ {len(products_created)} productos'))
        self.stdout.write(self.style.SUCCESS(f'✅ {len(customers)} clientes'))
        self.stdout.write(self.style.SUCCESS(f'✅ 3 ventas de ejemplo'))