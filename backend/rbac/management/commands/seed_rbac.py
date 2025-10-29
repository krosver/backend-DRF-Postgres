# scripts/seed_rbac.py
from django.core.management.base import BaseCommand
from rbac.fixtures import load as load_rbac

class Command(BaseCommand):
    help = "Инициализация RBAC: роли, ресурсы, правила"

    def handle(self, *args, **options):
        load_rbac()
        self.stdout.write(self.style.SUCCESS("RBAC seeded"))
