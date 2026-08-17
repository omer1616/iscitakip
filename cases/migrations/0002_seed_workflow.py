from django.db import migrations


STAGES = [
    ("Yeni Açıldı", 10, "blue", False),
    ("Evrak Bekleniyor", 20, "amber", False),
    ("Arabulucuda", 30, "purple", False),
    ("Dava Açıldı", 40, "indigo", False),
    ("Bilirkişi İncelemesinde", 50, "orange", False),
    ("Karar Bekleniyor", 60, "amber", False),
    ("Kesinleşti", 70, "green", False),
    ("Kapatıldı", 80, "slate", True),
]


def seed_workflow(apps, schema_editor):
    Stage = apps.get_model("cases", "WorkflowStage")
    Transition = apps.get_model("cases", "WorkflowTransition")
    stages = []
    for name, order, color, is_terminal in STAGES:
        stage, _ = Stage.objects.get_or_create(
            name=name,
            defaults={"order": order, "color": color, "is_terminal": is_terminal, "is_active": True},
        )
        stages.append(stage)
    for source, target in zip(stages, stages[1:]):
        Transition.objects.get_or_create(from_stage=source, to_stage=target)


def unseed_workflow(apps, schema_editor):
    # Yönetici tarafından özelleştirilmiş olabilecek süreç verisini geri dönüşte silmeyiz.
    pass


class Migration(migrations.Migration):
    dependencies = [("cases", "0001_initial")]
    operations = [migrations.RunPython(seed_workflow, unseed_workflow)]

