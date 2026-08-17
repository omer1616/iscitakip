from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission, User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from cases.admin import CaseFileAdmin
from cases.models import CaseFile, CaseStageHistory, Worker, WorkflowStage, WorkflowTransition


class CaseFileAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.stage_new = WorkflowStage.objects.get(name="Yeni Açıldı")
        cls.stage_documents = WorkflowStage.objects.get(name="Evrak Bekleniyor")
        cls.lawyer_one = User.objects.create_user("lawyer-one", password="test", is_staff=True)
        cls.lawyer_two = User.objects.create_user("lawyer-two", password="test", is_staff=True)
        cls.superuser = User.objects.create_superuser("root", "root@example.test", "test")
        cls.worker = Worker.objects.create(first_name="Ayşe", last_name="Yılmaz")
        cls.case_one = CaseFile.objects.create(
            worker=cls.worker,
            responsible_lawyer=cls.lawyer_one,
            current_stage=cls.stage_new,
            subject="İşçilik alacağı",
            severance_amount="1000.00",
        )
        cls.case_two = CaseFile.objects.create(
            worker=cls.worker,
            responsible_lawyer=cls.lawyer_two,
            current_stage=cls.stage_new,
            subject="İşe iade",
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = CaseFileAdmin(CaseFile, AdminSite())

    def request_for(self, user):
        request = self.factory.get("/admin/cases/casefile/")
        request.user = user
        return request

    def test_lawyer_only_sees_assigned_cases(self):
        request = self.request_for(self.lawyer_one)
        self.assertQuerySetEqual(self.model_admin.get_queryset(request), [self.case_one])

    def test_view_all_permission_exposes_all_cases(self):
        permission = Permission.objects.get(codename="view_all_casefiles")
        self.lawyer_one.user_permissions.add(permission)
        request = self.request_for(User.objects.get(pk=self.lawyer_one.pk))
        self.assertEqual(self.model_admin.get_queryset(request).count(), 2)

    def test_financial_fieldset_is_hidden_without_permission(self):
        request = self.request_for(self.lawyer_one)
        flattened = str(self.model_admin.get_fieldsets(request, self.case_one))
        self.assertNotIn("severance_amount", flattened)

    def test_financial_fieldset_is_readonly_with_view_only_permission(self):
        permission = Permission.objects.get(codename="view_financial_data")
        self.lawyer_one.user_permissions.add(permission)
        lawyer = User.objects.get(pk=self.lawyer_one.pk)
        request = self.request_for(lawyer)
        self.assertIn("severance_amount", str(self.model_admin.get_fieldsets(request, self.case_one)))
        self.assertIn("severance_amount", self.model_admin.get_readonly_fields(request, self.case_one))

    def test_admin_stage_change_creates_audit_history(self):
        request = self.request_for(self.superuser)
        self.case_one.current_stage = self.stage_documents
        form = SimpleNamespace(cleaned_data={"transition_note": "Evrak talep edildi."})
        self.model_admin.save_model(request, self.case_one, form, change=True)
        history = CaseStageHistory.objects.get(case_file=self.case_one)
        self.assertEqual(history.from_stage, self.stage_new)
        self.assertEqual(history.to_stage, self.stage_documents)
        self.assertEqual(history.changed_by, self.superuser)
        self.assertEqual(history.note, "Evrak talep edildi.")

    def test_transition_rules_limit_stage_choices(self):
        WorkflowTransition.objects.exclude(from_stage=self.stage_new, to_stage=self.stage_documents).delete()
        request = self.request_for(self.superuser)
        form_class = self.model_admin.get_form(request, self.case_one)
        choices = set(form_class.base_fields["current_stage"].queryset.values_list("name", flat=True))
        self.assertEqual(choices, {"Yeni Açıldı", "Evrak Bekleniyor"})

    def test_financial_inputs_are_not_rendered_for_unauthorized_lawyer(self):
        permissions = Permission.objects.filter(codename__in=("view_casefile", "change_casefile"))
        self.lawyer_one.user_permissions.add(*permissions)
        self.client.force_login(self.lawyer_one)
        response = self.client.get(reverse("admin:cases_casefile_change", args=(self.case_one.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="severance_amount"')

    def test_dashboard_and_kanban_render(self):
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:cases_casefile_kanban")).status_code, 200)
