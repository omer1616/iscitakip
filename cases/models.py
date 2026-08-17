import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


def generate_reference_number():
    return f"DSY-{timezone.localdate():%Y}-{uuid.uuid4().hex[:6].upper()}"


class WorkflowStage(models.Model):
    class Color(models.TextChoices):
        SLATE = "slate", "Gri"
        BLUE = "blue", "Mavi"
        AMBER = "amber", "Sarı"
        ORANGE = "orange", "Turuncu"
        PURPLE = "purple", "Mor"
        INDIGO = "indigo", "Lacivert"
        GREEN = "green", "Yeşil"
        RED = "red", "Kırmızı"

    name = models.CharField("Aşama adı", max_length=100, unique=True)
    description = models.TextField("Açıklama", blank=True)
    order = models.PositiveSmallIntegerField("Sıra", default=0, db_index=True)
    color = models.CharField("Renk", max_length=20, choices=Color.choices, default=Color.SLATE)
    is_active = models.BooleanField("Aktif", default=True)
    is_terminal = models.BooleanField("Son aşama", default=False)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Süreç aşaması"
        verbose_name_plural = "Süreç aşamaları"

    def __str__(self):
        return self.name


class WorkflowTransition(models.Model):
    from_stage = models.ForeignKey(
        WorkflowStage,
        verbose_name="Başlangıç aşaması",
        on_delete=models.CASCADE,
        related_name="outgoing_transitions",
    )
    to_stage = models.ForeignKey(
        WorkflowStage,
        verbose_name="Hedef aşama",
        on_delete=models.CASCADE,
        related_name="incoming_transitions",
    )
    label = models.CharField("Geçiş adı", max_length=100, blank=True)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        ordering = ("from_stage__order", "to_stage__order")
        constraints = [
            models.UniqueConstraint(fields=("from_stage", "to_stage"), name="unique_workflow_transition"),
            models.CheckConstraint(
                condition=~models.Q(from_stage=models.F("to_stage")),
                name="workflow_transition_different_stages",
            ),
        ]
        verbose_name = "Süreç geçişi"
        verbose_name_plural = "Süreç geçişleri"

    def __str__(self):
        return self.label or f"{self.from_stage} → {self.to_stage}"


class Worker(models.Model):
    identity_number = models.CharField(
        "T.C. kimlik no",
        max_length=11,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(r"^\d{11}$", "T.C. kimlik numarası 11 rakam olmalıdır.")],
    )
    first_name = models.CharField("Ad", max_length=100)
    last_name = models.CharField("Soyad", max_length=100)
    birth_date = models.DateField("Doğum tarihi", null=True, blank=True)
    phone = models.CharField("Telefon", max_length=30, blank=True)
    email = models.EmailField("E-posta", blank=True)
    address = models.TextField("Adres", blank=True)
    city = models.CharField("Şehir", max_length=100, blank=True)
    job_title = models.CharField("Görevi / unvanı", max_length=150, blank=True)
    employment_start = models.DateField("İşe giriş tarihi", null=True, blank=True)
    employment_end = models.DateField("İşten çıkış tarihi", null=True, blank=True)
    notes = models.TextField("Genel notlar", blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    updated_at = models.DateTimeField("Güncellenme", auto_now=True)

    class Meta:
        ordering = ("last_name", "first_name")
        verbose_name = "İşçi"
        verbose_name_plural = "İşçiler"

    def clean(self):
        if self.employment_start and self.employment_end and self.employment_end < self.employment_start:
            raise ValidationError({"employment_end": "İşten çıkış tarihi işe giriş tarihinden önce olamaz."})

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name


class OpposingParty(models.Model):
    class PartyType(models.TextChoices):
        EMPLOYER = "employer", "İşveren"
        COMPANY = "company", "Şirket"
        PERSON = "person", "Gerçek kişi"
        PUBLIC = "public", "Kamu kurumu"
        OTHER = "other", "Diğer"

    party_type = models.CharField("Taraf türü", max_length=20, choices=PartyType.choices, default=PartyType.EMPLOYER)
    name = models.CharField("Ad / unvan", max_length=255)
    tax_identity_number = models.CharField("Vergi / kimlik no", max_length=30, blank=True)
    contact_name = models.CharField("İrtibat kişisi", max_length=150, blank=True)
    phone = models.CharField("Telefon", max_length=30, blank=True)
    email = models.EmailField("E-posta", blank=True)
    address = models.TextField("Adres", blank=True)
    lawyer_info = models.TextField("Vekil bilgisi", blank=True)
    notes = models.TextField("Notlar", blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Karşı taraf"
        verbose_name_plural = "Karşı taraflar"

    def __str__(self):
        return self.name


class CaseFile(models.Model):
    class CaseType(models.TextChoices):
        LABOR = "labor", "İşçilik alacağı"
        REINSTATEMENT = "reinstatement", "İşe iade"
        MEDIATION = "mediation", "Arabuluculuk"
        ENFORCEMENT = "enforcement", "İcra"
        OTHER = "other", "Diğer"

    reference_number = models.CharField(
        "Dosya no", max_length=30, unique=True, default=generate_reference_number, editable=False
    )
    worker = models.ForeignKey(Worker, verbose_name="İşçi", on_delete=models.PROTECT, related_name="case_files")
    opposing_parties = models.ManyToManyField(OpposingParty, verbose_name="Karşı taraflar", related_name="case_files")
    responsible_lawyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Sorumlu avukat",
        on_delete=models.PROTECT,
        related_name="responsible_case_files",
        limit_choices_to={"is_staff": True, "is_active": True},
    )
    current_stage = models.ForeignKey(
        WorkflowStage,
        verbose_name="Güncel aşama",
        on_delete=models.PROTECT,
        related_name="case_files",
    )
    subject = models.CharField("Dosya konusu", max_length=255)
    case_type = models.CharField("Dosya türü", max_length=30, choices=CaseType.choices, default=CaseType.LABOR)
    court = models.CharField("Mahkeme / merci", max_length=255, blank=True)
    court_file_number = models.CharField("Mahkeme dosya no", max_length=100, blank=True)
    opening_date = models.DateField("Açılış tarihi", default=timezone.localdate)
    next_deadline = models.DateField("Sonraki kritik tarih", null=True, blank=True, db_index=True)
    closing_date = models.DateField("Kapanış tarihi", null=True, blank=True)
    summary = models.TextField("Dosya özeti", blank=True)

    agreed_monthly_wage = models.DecimalField("Aylık ücret", max_digits=14, decimal_places=2, null=True, blank=True)
    severance_amount = models.DecimalField("Kıdem tazminatı", max_digits=14, decimal_places=2, null=True, blank=True)
    notice_amount = models.DecimalField("İhbar tazminatı", max_digits=14, decimal_places=2, null=True, blank=True)
    other_receivables = models.DecimalField("Diğer alacaklar", max_digits=14, decimal_places=2, null=True, blank=True)
    financial_notes = models.TextField("Finansal notlar", blank=True)

    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    updated_at = models.DateTimeField("Güncellenme", auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "İşçi dosyası"
        verbose_name_plural = "İşçi dosyaları"
        permissions = [
            ("view_financial_data", "Finansal bilgileri görüntüleyebilir"),
            ("change_financial_data", "Finansal bilgileri değiştirebilir"),
            ("view_all_casefiles", "Tüm avukatların dosyalarını görüntüleyebilir"),
            ("transition_casefile", "Dosya aşamasını değiştirebilir"),
        ]

    def clean(self):
        if self.closing_date and self.closing_date < self.opening_date:
            raise ValidationError({"closing_date": "Kapanış tarihi açılış tarihinden önce olamaz."})

    @property
    def total_receivables(self):
        values = (self.severance_amount, self.notice_amount, self.other_receivables)
        return sum(value for value in values if value is not None)

    def __str__(self):
        return f"{self.reference_number} · {self.worker}"


class CaseStageHistory(models.Model):
    case_file = models.ForeignKey(CaseFile, verbose_name="Dosya", on_delete=models.CASCADE, related_name="stage_history")
    from_stage = models.ForeignKey(
        WorkflowStage,
        verbose_name="Önceki aşama",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="history_as_source",
    )
    to_stage = models.ForeignKey(
        WorkflowStage,
        verbose_name="Yeni aşama",
        on_delete=models.PROTECT,
        related_name="history_as_target",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Değiştiren",
        on_delete=models.SET_NULL,
        null=True,
        related_name="case_stage_changes",
    )
    note = models.TextField("Geçiş notu", blank=True)
    changed_at = models.DateTimeField("Değişiklik zamanı", auto_now_add=True)

    class Meta:
        ordering = ("-changed_at",)
        verbose_name = "Aşama geçmişi"
        verbose_name_plural = "Aşama geçmişi"

    def __str__(self):
        return f"{self.case_file.reference_number}: {self.from_stage or 'Başlangıç'} → {self.to_stage}"


class CaseNote(models.Model):
    case_file = models.ForeignKey(CaseFile, verbose_name="Dosya", on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Yazan", on_delete=models.PROTECT)
    text = models.TextField("Not")
    is_private = models.BooleanField("Yalnızca sorumlu avukat ve yöneticiler", default=False)
    created_at = models.DateTimeField("Eklenme", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Dosya notu"
        verbose_name_plural = "Dosya notları"

    def __str__(self):
        return f"{self.case_file.reference_number} · {self.author}"


def document_upload_path(instance, filename):
    return f"case-files/{instance.case_file.reference_number}/{filename}"


class CaseDocument(models.Model):
    class DocumentType(models.TextChoices):
        PETITION = "petition", "Dilekçe"
        EVIDENCE = "evidence", "Delil / belge"
        DECISION = "decision", "Karar"
        EXPERT = "expert", "Bilirkişi raporu"
        CORRESPONDENCE = "correspondence", "Yazışma"
        OTHER = "other", "Diğer"

    case_file = models.ForeignKey(CaseFile, verbose_name="Dosya", on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField("Belge türü", max_length=30, choices=DocumentType.choices, default=DocumentType.OTHER)
    title = models.CharField("Başlık", max_length=200)
    file = models.FileField("Dosya", upload_to=document_upload_path)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Yükleyen", on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField("Yüklenme", auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)
        verbose_name = "Dosya belgesi"
        verbose_name_plural = "Dosya belgeleri"

    def __str__(self):
        return self.title

