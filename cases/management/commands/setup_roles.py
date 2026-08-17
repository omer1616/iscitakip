from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


ROLE_PERMISSIONS = {
    "Avukat": {
        "view_casefile",
        "add_casefile",
        "change_casefile",
        "transition_casefile",
        "view_worker",
        "add_worker",
        "change_worker",
        "view_opposingparty",
        "add_opposingparty",
        "change_opposingparty",
        "view_casenote",
        "add_casenote",
        "change_casenote",
        "delete_casenote",
        "view_casedocument",
        "add_casedocument",
        "change_casedocument",
        "delete_casedocument",
        "view_casestagehistory",
        "view_workflowstage",
        "view_workflowtransition",
    },
    "Finans Yetkilisi": {"view_financial_data", "change_financial_data"},
    "Dosya Yöneticisi": {
        "view_casefile",
        "add_casefile",
        "change_casefile",
        "delete_casefile",
        "view_all_casefiles",
        "transition_casefile",
        "view_financial_data",
        "change_financial_data",
        "view_worker",
        "add_worker",
        "change_worker",
        "view_opposingparty",
        "add_opposingparty",
        "change_opposingparty",
        "view_casenote",
        "add_casenote",
        "change_casenote",
        "delete_casenote",
        "view_casedocument",
        "add_casedocument",
        "change_casedocument",
        "delete_casedocument",
        "view_casestagehistory",
        "view_workflowstage",
        "view_workflowtransition",
    },
}


class Command(BaseCommand):
    help = "Avukat, Finans Yetkilisi ve Dosya Yöneticisi rollerini oluşturur/günceller."

    def handle(self, *args, **options):
        case_permissions = Permission.objects.filter(content_type__app_label="cases")
        for role_name, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            selected = list(case_permissions.filter(codename__in=codenames))
            group.permissions.set(selected)
            missing = codenames - {permission.codename for permission in selected}
            if missing:
                self.stderr.write(self.style.WARNING(f"{role_name}: bulunamayan izinler: {', '.join(sorted(missing))}"))
            self.stdout.write(self.style.SUCCESS(f"{role_name}: {len(selected)} izin atandı."))
