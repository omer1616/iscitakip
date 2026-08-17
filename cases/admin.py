from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .forms import CaseFileAdminForm
from .models import (
    CaseDocument,
    CaseFile,
    CaseNote,
    CaseStageHistory,
    OpposingParty,
    Worker,
    WorkflowStage,
    WorkflowTransition,
)


FINANCIAL_FIELDS = (
    "agreed_monthly_wage",
    "severance_amount",
    "notice_amount",
    "other_receivables",
    "total_receivables_display",
    "financial_notes",
)

STAGE_COLORS = {
    "slate": "#64748b",
    "blue": "#2563eb",
    "amber": "#d97706",
    "orange": "#ea580c",
    "purple": "#9333ea",
    "indigo": "#4f46e5",
    "green": "#16a34a",
    "red": "#dc2626",
}


class ScopedCaseAdminMixin:
    """Avukatları kendi dosyalarıyla sınırlar; yöneticiler tüm kayıtları görür."""

    def user_can_view_all_cases(self, request):
        return request.user.is_superuser or request.user.has_perm("cases.view_all_casefiles")

    def scope_case_queryset(self, request, queryset, lookup="responsible_lawyer"):
        if self.user_can_view_all_cases(request):
            return queryset
        return queryset.filter(**{lookup: request.user})


class CaseStageHistoryInline(TabularInline):
    model = CaseStageHistory
    extra = 0
    can_delete = False
    fields = ("from_stage", "to_stage", "changed_by", "note", "changed_at")
    readonly_fields = fields
    tab = True

    def has_add_permission(self, request, obj=None):
        return False


class CaseNoteInline(TabularInline):
    model = CaseNote
    extra = 0
    fields = ("text", "is_private", "author", "created_at")
    readonly_fields = ("author", "created_at")
    tab = True


class CaseDocumentInline(TabularInline):
    model = CaseDocument
    extra = 0
    fields = ("document_type", "title", "file", "uploaded_by", "uploaded_at")
    readonly_fields = ("uploaded_by", "uploaded_at")
    tab = True


@admin.register(CaseFile)
class CaseFileAdmin(ScopedCaseAdminMixin, ModelAdmin):
    form = CaseFileAdminForm
    inlines = (CaseNoteInline, CaseDocumentInline, CaseStageHistoryInline)
    list_display = (
        "reference_number",
        "worker_link",
        "stage_badge",
        "responsible_lawyer",
        "case_type",
        "deadline_badge",
        "updated_at",
    )
    list_filter = ("current_stage", "case_type", "responsible_lawyer", "opening_date", "next_deadline")
    search_fields = (
        "reference_number",
        "subject",
        "worker__first_name",
        "worker__last_name",
        "worker__identity_number",
        "opposing_parties__name",
        "court_file_number",
    )
    autocomplete_fields = ("worker", "opposing_parties", "responsible_lawyer")
    list_select_related = ("worker", "current_stage", "responsible_lawyer")
    filter_horizontal = ("opposing_parties",)
    date_hierarchy = "opening_date"
    list_per_page = 30
    compressed_fields = True
    warn_unsaved_form = True

    core_fieldsets = (
        (
            "Dosya",
            {
                "fields": (
                    ("reference_number", "case_type"),
                    "subject",
                    ("worker", "responsible_lawyer"),
                    "opposing_parties",
                )
            },
        ),
        (
            "Süreç",
            {
                "fields": (
                    ("current_stage", "transition_note"),
                    ("opening_date", "next_deadline", "closing_date"),
                )
            },
        ),
        (
            "Yargılama bilgileri",
            {"fields": (("court", "court_file_number"), "summary")},
        ),
        (
            "Kayıt bilgileri",
            {"fields": (("created_at", "updated_at"),), "classes": ("collapse",)},
        ),
    )
    financial_fieldset = (
        "Finansal bilgiler",
        {
            "fields": (
                ("agreed_monthly_wage", "severance_amount"),
                ("notice_amount", "other_receivables"),
                "total_receivables_display",
                "financial_notes",
            ),
            "description": "Bu bölüm yalnızca finansal bilgi yetkisi olan kullanıcılara gösterilir.",
        },
    )

    def get_urls(self):
        return [
            path("kanban/", self.admin_site.admin_view(self.kanban_view), name="cases_casefile_kanban"),
        ] + super().get_urls()

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("worker", "current_stage", "responsible_lawyer")
        return self.scope_case_queryset(request, queryset).distinct()

    def has_view_permission(self, request, obj=None):
        allowed = super().has_view_permission(request, obj)
        if not allowed or obj is None or self.user_can_view_all_cases(request):
            return allowed
        return obj.responsible_lawyer_id == request.user.id

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed or obj is None or self.user_can_view_all_cases(request):
            return allowed
        return obj.responsible_lawyer_id == request.user.id

    def has_delete_permission(self, request, obj=None):
        allowed = super().has_delete_permission(request, obj)
        if not allowed or obj is None or self.user_can_view_all_cases(request):
            return allowed
        return obj.responsible_lawyer_id == request.user.id

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(self.core_fieldsets)
        if request.user.is_superuser or request.user.has_perm("cases.view_financial_data"):
            fieldsets.insert(3, self.financial_fieldset)
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        fields = ["reference_number", "created_at", "updated_at", "total_receivables_display"]
        if obj and not (request.user.is_superuser or request.user.has_perm("cases.transition_casefile")):
            fields.append("current_stage")
        if not (request.user.is_superuser or request.user.has_perm("cases.change_financial_data")):
            fields.extend(field for field in FINANCIAL_FIELDS if field not in fields)
        return tuple(fields)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        stage_field = form.base_fields.get("current_stage")
        if stage_field is not None:
            active_stages = WorkflowStage.objects.filter(is_active=True)
            if obj and WorkflowTransition.objects.filter(is_active=True).exists():
                target_ids = WorkflowTransition.objects.filter(
                    from_stage=obj.current_stage,
                    is_active=True,
                    to_stage__is_active=True,
                ).values_list("to_stage_id", flat=True)
                active_stages = WorkflowStage.objects.filter(Q(pk=obj.current_stage_id) | Q(pk__in=target_ids))
            stage_field.queryset = active_stages.order_by("order", "name")
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "responsible_lawyer":
            queryset = User.objects.filter(is_active=True, is_staff=True)
            if not self.user_can_view_all_cases(request):
                queryset = queryset.filter(pk=request.user.pk)
            kwargs["queryset"] = queryset
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        previous_stage_id = None
        if change:
            previous_stage_id = CaseFile.objects.select_for_update().values_list("current_stage_id", flat=True).get(pk=obj.pk)
            if previous_stage_id != obj.current_stage_id and not (
                request.user.is_superuser or request.user.has_perm("cases.transition_casefile")
            ):
                raise PermissionDenied("Dosya aşamasını değiştirme yetkiniz yok.")

        super().save_model(request, obj, form, change)

        if not change or previous_stage_id != obj.current_stage_id:
            CaseStageHistory.objects.create(
                case_file=obj,
                from_stage_id=previous_stage_id,
                to_stage=obj.current_stage,
                changed_by=request.user,
                note=form.cleaned_data.get("transition_note", ""),
            )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for deleted in formset.deleted_objects:
            deleted.delete()
        for instance in instances:
            if isinstance(instance, CaseNote) and not instance.author_id:
                instance.author = request.user
            if isinstance(instance, CaseDocument) and not instance.uploaded_by_id:
                instance.uploaded_by = request.user
            instance.save()
        formset.save_m2m()

    @admin.display(description="İşçi", ordering="worker__last_name")
    def worker_link(self, obj):
        url = reverse("admin:cases_worker_change", args=(obj.worker_id,))
        return format_html('<a href="{}">{}</a>', url, obj.worker.full_name)

    @admin.display(description="Aşama", ordering="current_stage__order")
    def stage_badge(self, obj):
        color = STAGE_COLORS.get(obj.current_stage.color, STAGE_COLORS["slate"])
        return format_html('<span class="stage-badge" style="--stage-color:{}">{}</span>', color, obj.current_stage.name)

    @admin.display(description="Kritik tarih", ordering="next_deadline")
    def deadline_badge(self, obj):
        if not obj.next_deadline:
            return "—"
        remaining = (obj.next_deadline - timezone.localdate()).days
        css_class = "deadline-overdue" if remaining < 0 else "deadline-soon" if remaining <= 7 else ""
        return format_html('<span class="{}">{:%d.%m.%Y}</span>', css_class, obj.next_deadline)

    @admin.display(description="Toplam alacak")
    def total_receivables_display(self, obj):
        if not obj:
            return "—"
        return f"{obj.total_receivables:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")

    def kanban_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        queryset = self.get_queryset(request).filter(current_stage__is_active=True)
        stages = list(WorkflowStage.objects.filter(is_active=True))
        columns = [{"stage": stage, "cases": queryset.filter(current_stage=stage)[:100]} for stage in stages]
        context = {
            **self.admin_site.each_context(request),
            "title": "Dosya Kanban Görünümü",
            "columns": columns,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/cases/casefile/kanban.html", context)


@admin.register(Worker)
class WorkerAdmin(ModelAdmin):
    list_display = ("full_name_display", "identity_number", "phone", "city", "job_title", "updated_at")
    search_fields = ("first_name", "last_name", "identity_number", "phone", "email")
    list_filter = ("city", "employment_start", "employment_end")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Kimlik bilgileri", {"fields": (("first_name", "last_name"), ("identity_number", "birth_date"))}),
        ("İletişim", {"fields": (("phone", "email"), ("city",), "address")}),
        ("Çalışma", {"fields": ("job_title", ("employment_start", "employment_end"))}),
        ("Notlar", {"fields": ("notes",)}),
        ("Kayıt bilgileri", {"fields": (("created_at", "updated_at"),), "classes": ("collapse",)}),
    )

    @admin.display(description="Ad soyad", ordering="last_name")
    def full_name_display(self, obj):
        return obj.full_name


@admin.register(OpposingParty)
class OpposingPartyAdmin(ModelAdmin):
    list_display = ("name", "party_type", "contact_name", "phone", "email")
    list_filter = ("party_type",)
    search_fields = ("name", "tax_identity_number", "contact_name", "phone", "email")
    readonly_fields = ("created_at",)


@admin.register(WorkflowStage)
class WorkflowStageAdmin(ModelAdmin):
    list_display = ("name", "colored_stage", "order", "is_active", "is_terminal", "case_count")
    list_editable = ("order", "is_active", "is_terminal")
    list_filter = ("is_active", "is_terminal", "color")
    search_fields = ("name", "description")

    @admin.display(description="Görünüm")
    def colored_stage(self, obj):
        color = STAGE_COLORS.get(obj.color, STAGE_COLORS["slate"])
        return format_html('<span class="stage-badge" style="--stage-color:{}">{}</span>', color, obj.name)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_case_count=Count("case_files"))

    @admin.display(description="Dosya sayısı", ordering="_case_count")
    def case_count(self, obj):
        return obj._case_count


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(ModelAdmin):
    list_display = ("from_stage", "arrow", "to_stage", "label", "is_active")
    list_editable = ("is_active",)
    list_filter = ("is_active", "from_stage", "to_stage")
    autocomplete_fields = ("from_stage", "to_stage")

    @admin.display(description="")
    def arrow(self, obj):
        return "→"


@admin.register(CaseNote)
class CaseNoteAdmin(ScopedCaseAdminMixin, ModelAdmin):
    list_display = ("case_file", "author", "short_text", "is_private", "created_at")
    list_filter = ("is_private", "created_at", "author")
    search_fields = ("case_file__reference_number", "case_file__worker__first_name", "case_file__worker__last_name", "text")
    autocomplete_fields = ("case_file",)
    readonly_fields = ("author", "created_at")

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("case_file", "author")
        return self.scope_case_queryset(request, queryset, "case_file__responsible_lawyer")

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Not")
    def short_text(self, obj):
        return obj.text[:80]


@admin.register(CaseDocument)
class CaseDocumentAdmin(ScopedCaseAdminMixin, ModelAdmin):
    list_display = ("title", "case_file", "document_type", "uploaded_by", "uploaded_at")
    list_filter = ("document_type", "uploaded_at")
    search_fields = ("title", "case_file__reference_number", "case_file__worker__first_name", "case_file__worker__last_name")
    autocomplete_fields = ("case_file",)
    readonly_fields = ("uploaded_by", "uploaded_at")

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("case_file", "uploaded_by")
        return self.scope_case_queryset(request, queryset, "case_file__responsible_lawyer")

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CaseStageHistory)
class CaseStageHistoryAdmin(ScopedCaseAdminMixin, ModelAdmin):
    list_display = ("case_file", "from_stage", "to_stage", "changed_by", "changed_at")
    list_filter = ("from_stage", "to_stage", "changed_at", "changed_by")
    search_fields = ("case_file__reference_number", "case_file__worker__first_name", "case_file__worker__last_name", "note")
    readonly_fields = ("case_file", "from_stage", "to_stage", "changed_by", "note", "changed_at")

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("case_file", "from_stage", "to_stage", "changed_by")
        return self.scope_case_queryset(request, queryset, "case_file__responsible_lawyer")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


admin.site.site_header = "İşçi Dosya Yönetimi"
admin.site.site_title = "Dosya Yönetimi"
admin.site.index_title = "Genel Bakış"
