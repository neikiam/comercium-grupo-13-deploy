from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress


class Command(BaseCommand):
    help = 'Crea un usuario de prueba con EmailAddress para allauth'

    def handle(self, *args, **options):
        username = 'testuser'
        email = 'test@example.com'
        password = 'test123'
        
        # Eliminar usuario si existe
        User.objects.filter(username=username).delete()
        
        # Crear usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        user.is_active = True
        user.save()
        
        # Crear EmailAddress para allauth
        EmailAddress.objects.create(
            user=user,
            email=email,
            verified=True,
            primary=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Usuario creado exitosamente:\n'
                f'  Username: {username}\n'
                f'  Email: {email}\n'
                f'  Password: {password}\n'
                f'  Puede hacer login en /accounts/login/'
            )
        )
