from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Setup inicial de la aplicación'

    def handle(self, *args, **kwargs):
        # Crear superusuario si no existe
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='tupassword123'
            )
            self.stdout.write(self.style.SUCCESS('✅ Superusuario creado'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ Superusuario ya existe'))