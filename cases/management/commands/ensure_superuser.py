import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError


class Command(BaseCommand):
    help = (
        "Ortam değişkenlerinden superuser oluşturur veya günceller. "
        "DJANGO_SUPERUSER_USERNAME ve DJANGO_SUPERUSER_PASSWORD tanımlı değilse hiçbir şey yapmaz."
    )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        update_password = os.environ.get("DJANGO_SUPERUSER_UPDATE_PASSWORD", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        if not username or not password:
            self.stdout.write(
                "DJANGO_SUPERUSER_USERNAME/DJANGO_SUPERUSER_PASSWORD tanımlı değil, superuser adımı atlandı."
            )
            return

        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD
        user = user_model.objects.filter(**{username_field: username}).first()

        if user is None:
            try:
                user_model.objects.create_superuser(
                    **{username_field: username, "email": email, "password": password}
                )
            except IntegrityError:
                # Aynı anda başlayan ikinci bir konteyner kullanıcıyı oluşturmuş olabilir.
                self.stdout.write(self.style.WARNING(f"'{username}' zaten oluşturulmuş, atlandı."))
                return
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' oluşturuldu."))
            return

        changed = []
        if not user.is_staff or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            changed.append("yetkiler")
        if email and user.email != email:
            user.email = email
            changed.append("e-posta")
        if update_password:
            user.set_password(password)
            changed.append("parola")

        if changed:
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' güncellendi ({', '.join(changed)})."))
        else:
            self.stdout.write(f"Superuser '{username}' zaten mevcut, değişiklik yapılmadı.")