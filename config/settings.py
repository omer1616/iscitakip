import os
from pathlib import Path

from django.templatetags.static import static
from django.urls import reverse_lazy


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "development-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1,.ngrok-free.app,.ngrok-free.dev" if DEBUG else "localhost,127.0.0.1",
    ).split(",")
    if host
]
CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://*.ngrok-free.app,https://*.ngrok-free.dev" if DEBUG else "",
    ).split(",")
    if origin
]

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cases",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("DB_NAME", BASE_DIR / "db.sqlite3"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr-tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = reverse_lazy("admin:login")

# Üretim güvenlik varsayılanları DJANGO_DEBUG=0 ile etkinleşir.
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

UNFOLD = {
    "SITE_TITLE": "İşçi Dosya Takip",
    "SITE_HEADER": "Dosya Yönetimi",
    "SITE_SUBHEADER": "Hukuki süreç ve evrak takibi",
    "SITE_SYMBOL": "folder_managed",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "DASHBOARD_CALLBACK": "cases.dashboard.dashboard_callback",
    "STYLES": [lambda request: static("css/admin.css")],
    "COLORS": {
        "primary": {
            "50": "oklch(97.7% .014 178)",
            "100": "oklch(94.8% .038 178)",
            "200": "oklch(89.5% .074 178)",
            "300": "oklch(81.5% .12 178)",
            "400": "oklch(70.5% .15 178)",
            "500": "oklch(60% .14 178)",
            "600": "oklch(50% .12 178)",
            "700": "oklch(42% .10 178)",
            "800": "oklch(35% .08 178)",
            "900": "oklch(29% .06 178)",
            "950": "oklch(20% .04 178)",
        }
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Dosya Yönetimi",
                "separator": True,
                "items": [
                    {"title": "Genel Bakış", "icon": "dashboard", "link": reverse_lazy("admin:index")},
                    {"title": "Dosyalar", "icon": "folder_open", "link": reverse_lazy("admin:cases_casefile_changelist")},
                    {"title": "Kanban", "icon": "view_kanban", "link": reverse_lazy("admin:cases_casefile_kanban")},
                    {"title": "İşçiler", "icon": "badge", "link": reverse_lazy("admin:cases_worker_changelist")},
                    {"title": "Karşı Taraflar", "icon": "domain", "link": reverse_lazy("admin:cases_opposingparty_changelist")},
                ],
            },
            {
                "title": "Süreç Ayarları",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Aşamalar", "icon": "account_tree", "link": reverse_lazy("admin:cases_workflowstage_changelist")},
                    {"title": "Geçiş Kuralları", "icon": "route", "link": reverse_lazy("admin:cases_workflowtransition_changelist")},
                ],
            },
            {
                "title": "Yetkilendirme",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Kullanıcılar", "icon": "person", "link": reverse_lazy("admin:auth_user_changelist")},
                    {"title": "Roller / Gruplar", "icon": "group", "link": reverse_lazy("admin:auth_group_changelist")},
                ],
            },
        ],
    },
}
