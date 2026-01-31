# accounts/management/commands/create_backup.py
# Crear esta estructura de carpetas:
# accounts/
#   management/
#     __init__.py
#     commands/
#       __init__.py
#       create_backup.py

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import os
import shutil
import zipfile

class Command(BaseCommand):
    help = 'Crear backup completo de la base de datos y archivos media'

    def handle(self, *args, **options):
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        
        # Crear directorio de backups si no existe
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backup_name = f'backup_{timestamp}'
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            # Crear carpeta temporal del backup
            os.makedirs(backup_path)
            
            # 1. Copiar base de datos SQLite
            db_path = settings.DATABASES['default']['NAME']
            if os.path.exists(db_path):
                shutil.copy2(db_path, os.path.join(backup_path, 'db.sqlite3'))
                self.stdout.write(self.style.SUCCESS('✓ Base de datos copiada'))
            
            # 2. Copiar carpeta media (imágenes de productos)
            media_root = settings.MEDIA_ROOT
            if os.path.exists(media_root):
                media_backup = os.path.join(backup_path, 'media')
                shutil.copytree(media_root, media_backup)
                self.stdout.write(self.style.SUCCESS('✓ Archivos media copiados'))
            
            # 3. Crear archivo ZIP
            zip_path = f'{backup_path}.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, backup_path)
                        zipf.write(file_path, arcname)
            
            # 4. Eliminar carpeta temporal
            shutil.rmtree(backup_path)
            
            # 5. Calcular tamaño
            size_mb = os.path.getsize(zip_path) / (1024 * 1024)
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Backup creado exitosamente!'
                f'\n📦 Archivo: {backup_name}.zip'
                f'\n💾 Tamaño: {size_mb:.2f} MB'
                f'\n📍 Ubicación: backups/'
            ))
            
            return zip_path
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            return None