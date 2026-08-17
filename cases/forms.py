from django import forms

from .models import CaseFile


class CaseFileAdminForm(forms.ModelForm):
    transition_note = forms.CharField(
        label="Aşama değişikliği notu",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Aşama değişirse bu açıklama süreç geçmişine eklenir.",
    )

    class Meta:
        model = CaseFile
        fields = "__all__"

