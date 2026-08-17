from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .models import CaseFile, WorkflowStage


def dashboard_callback(request, context):
    cases = CaseFile.objects.select_related("current_stage", "worker", "responsible_lawyer")
    if not (request.user.is_superuser or request.user.has_perm("cases.view_all_casefiles")):
        cases = cases.filter(responsible_lawyer=request.user)

    today = timezone.localdate()
    active_cases = cases.filter(current_stage__is_terminal=False)
    context.update(
        {
            "case_total": cases.count(),
            "active_case_total": active_cases.count(),
            "overdue_total": active_cases.filter(next_deadline__lt=today).count(),
            "upcoming_total": active_cases.filter(next_deadline__range=(today, today + timedelta(days=14))).count(),
            "stage_summary": WorkflowStage.objects.filter(is_active=True)
            .annotate(case_total=Count("case_files", filter=Q_for_user(request)))
            .order_by("order", "name"),
            "recent_cases": cases.order_by("-updated_at")[:8],
        }
    )
    return context


def Q_for_user(request):
    from django.db.models import Q

    if request.user.is_superuser or request.user.has_perm("cases.view_all_casefiles"):
        return Q()
    return Q(case_files__responsible_lawyer=request.user)

