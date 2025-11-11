"""
Comando de diagnóstico para verificar la configuración de Cloudinary
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Diagnóstico de configuración de Cloudinary'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("🔍 DIAGNÓSTICO DE CLOUDINARY"))
        self.stdout.write("="*60 + "\n")

        # 1. Verificar variables de entorno
        self.stdout.write(self.style.WARNING("1. Variables de Entorno:"))
        cloudinary_url = os.getenv('CLOUDINARY_URL')
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        api_key = os.getenv('CLOUDINARY_API_KEY')
        api_secret = os.getenv('CLOUDINARY_API_SECRET')

        if cloudinary_url:
            # Censurar la parte secreta
            parts = cloudinary_url.split('@')
            if len(parts) == 2:
                masked = f"cloudinary://***:***@{parts[1]}"
            else:
                masked = "cloudinary://*** (formato incorrecto)"
            self.stdout.write(f"   CLOUDINARY_URL: {masked}")
        else:
            self.stdout.write(self.style.ERROR("   ❌ CLOUDINARY_URL: NO CONFIGURADA"))

        if cloud_name:
            self.stdout.write(f"   CLOUDINARY_CLOUD_NAME: {cloud_name}")
        else:
            self.stdout.write(self.style.ERROR("   ❌ CLOUDINARY_CLOUD_NAME: NO CONFIGURADA"))

        if api_key:
            self.stdout.write(f"   CLOUDINARY_API_KEY: {api_key[:5]}***")
        else:
            self.stdout.write(self.style.ERROR("   ❌ CLOUDINARY_API_KEY: NO CONFIGURADA"))

        if api_secret:
            self.stdout.write(f"   CLOUDINARY_API_SECRET: {api_secret[:3]}***")
        else:
            self.stdout.write(self.style.ERROR("   ❌ CLOUDINARY_API_SECRET: NO CONFIGURADA"))

        # 2. Verificar configuración de Django
        self.stdout.write("\n" + self.style.WARNING("2. Configuración de Django:"))
        use_cloudinary = getattr(settings, 'USE_CLOUDINARY', False)
        
        if use_cloudinary:
            self.stdout.write(self.style.SUCCESS("   ✅ USE_CLOUDINARY: True"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ USE_CLOUDINARY: False"))
            self.stdout.write("      → Usando almacenamiento LOCAL (no funciona en Render)")

        # 3. Verificar DEFAULT_FILE_STORAGE
        default_storage = getattr(settings, 'DEFAULT_FILE_STORAGE', 'django.core.files.storage.FileSystemStorage')
        self.stdout.write(f"   DEFAULT_FILE_STORAGE: {default_storage}")
        
        if 'cloudinary' in default_storage.lower():
            self.stdout.write(self.style.SUCCESS("      ✅ Configurado para Cloudinary"))
        else:
            self.stdout.write(self.style.ERROR("      ❌ NO está usando Cloudinary"))

        # 4. Verificar MEDIA_URL y MEDIA_ROOT
        self.stdout.write("\n" + self.style.WARNING("3. Rutas de Media:"))
        self.stdout.write(f"   MEDIA_URL: {settings.MEDIA_URL}")
        
        media_root = getattr(settings, 'MEDIA_ROOT', 'N/A')
        if media_root != 'N/A':
            self.stdout.write(f"   MEDIA_ROOT: {media_root}")
            if use_cloudinary:
                self.stdout.write(self.style.WARNING("      ⚠️ MEDIA_ROOT no debería estar configurado con Cloudinary"))
        else:
            self.stdout.write("   MEDIA_ROOT: No configurado (correcto con Cloudinary)")

        # 5. Verificar INSTALLED_APPS
        self.stdout.write("\n" + self.style.WARNING("4. Apps Instaladas:"))
        installed_apps = settings.INSTALLED_APPS
        
        if 'cloudinary_storage' in installed_apps:
            pos = installed_apps.index('cloudinary_storage')
            self.stdout.write(self.style.SUCCESS(f"   ✅ cloudinary_storage: Instalado (posición {pos})"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ cloudinary_storage: NO INSTALADO"))

        if 'cloudinary' in installed_apps:
            pos = installed_apps.index('cloudinary')
            self.stdout.write(self.style.SUCCESS(f"   ✅ cloudinary: Instalado (posición {pos})"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ cloudinary: NO INSTALADO"))

        # Verificar orden correcto
        if 'cloudinary_storage' in installed_apps and 'django.contrib.staticfiles' in installed_apps:
            pos_cloudinary = installed_apps.index('cloudinary_storage')
            pos_staticfiles = installed_apps.index('django.contrib.staticfiles')
            if pos_cloudinary < pos_staticfiles:
                self.stdout.write(self.style.SUCCESS("   ✅ Orden correcto: cloudinary_storage antes de staticfiles"))
            else:
                self.stdout.write(self.style.ERROR("   ❌ ORDEN INCORRECTO: cloudinary_storage debe ir ANTES de staticfiles"))

        # 6. Intentar importar cloudinary
        self.stdout.write("\n" + self.style.WARNING("5. Test de Importación:"))
        try:
            import cloudinary
            self.stdout.write(self.style.SUCCESS("   ✅ Módulo cloudinary importado correctamente"))
            self.stdout.write(f"   Versión: {cloudinary.__version__}")
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error importando cloudinary: {e}"))

        try:
            import cloudinary_storage
            self.stdout.write(self.style.SUCCESS("   ✅ Módulo cloudinary_storage importado correctamente"))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error importando cloudinary_storage: {e}"))

        # 7. Test de conexión a Cloudinary (solo si está configurado)
        if use_cloudinary and cloudinary_url:
            self.stdout.write("\n" + self.style.WARNING("6. Test de Conexión:"))
            try:
                import cloudinary
                import cloudinary.api
                
                # Intentar obtener info de la cuenta
                result = cloudinary.api.ping()
                self.stdout.write(self.style.SUCCESS("   ✅ Conexión exitosa a Cloudinary"))
                self.stdout.write(f"   Status: {result.get('status', 'ok')}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error de conexión: {e}"))
                self.stdout.write("      → Verifica que las credenciales sean correctas")

        # Resumen final
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("📊 RESUMEN"))
        self.stdout.write("="*60)

        all_ok = True
        issues = []

        if not cloudinary_url:
            all_ok = False
            issues.append("❌ CLOUDINARY_URL no configurada")

        if not use_cloudinary:
            all_ok = False
            issues.append("❌ Cloudinary no está activo (USE_CLOUDINARY=False)")

        if 'cloudinary' not in default_storage.lower():
            all_ok = False
            issues.append("❌ DEFAULT_FILE_STORAGE no apunta a Cloudinary")

        if 'cloudinary_storage' not in installed_apps:
            all_ok = False
            issues.append("❌ cloudinary_storage no está en INSTALLED_APPS")

        if all_ok:
            self.stdout.write(self.style.SUCCESS("\n✅ TODO ESTÁ CONFIGURADO CORRECTAMENTE"))
            self.stdout.write("\nSi las imágenes no aparecen:")
            self.stdout.write("1. Asegúrate de subir NUEVAS imágenes (no usar antiguas)")
            self.stdout.write("2. Verifica en el navegador que la URL sea res.cloudinary.com")
            self.stdout.write("3. Revisa los logs de Render por errores al subir")
        else:
            self.stdout.write(self.style.ERROR("\n❌ SE ENCONTRARON PROBLEMAS:\n"))
            for issue in issues:
                self.stdout.write(f"   {issue}")
            self.stdout.write("\n💡 SOLUCIÓN:")
            self.stdout.write("   1. Configura las variables de entorno en Render")
            self.stdout.write("   2. Redespliega la aplicación")
            self.stdout.write("   3. Ejecuta este comando de nuevo para verificar")

        self.stdout.write("\n" + "="*60 + "\n")
