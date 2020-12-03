import os
import sys

import django
from django.core import management


def pytest_addoption(parser):
    parser.addoption(
        "--no-pkgroot",
        action="store_true",
        default=False,
        help="Remove package root directory from sys.path, ensuring that "
        "django_cloud_tasks is imported from the installed site-packages. "
        "Used for testing the distribution.",
    )
    parser.addoption(
        "--staticfiles",
        action="store_true",
        default=False,
        help="Run tests with static files collection, using manifest "
        "staticfiles storage. Used for testing the distribution.",
    )


def pytest_configure(config):
    from django.conf import settings

    PROJECT_ID = os.environ["DJANGO_CLOUD_TASKS_PROJECT_ID"]

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
        },
        SITE_ID=1,
        SECRET_KEY="not very secret in tests",
        USE_I18N=True,
        USE_L10N=True,
        STATIC_URL="/static/",
        ROOT_URLCONF="tests.urls",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {"debug": True,},  # We want template errors to raise
            },
        ],
        MIDDLEWARE=(
            "django.middleware.common.CommonMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ),
        INSTALLED_APPS=(
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.sites",
            "django.contrib.staticfiles",
            "django_cloud_tasks",
        ),
        PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",),
        DJANGO_CLOUD_TASKS={
            "project_location_name": f"projects/{PROJECT_ID}/locations/us-central1",
            "task_handler_uri": "/api/_tasks/",
            "task_handler_root_url": f"https://jg.local.me:8000/api/_tasks/",
        },
        DJANGO_CLOUD_TASKS_PROJECT_ID=PROJECT_ID,
        SERVICE_ACCOUNT_EMAIL=f"{PROJECT_ID}@appspot.gserviceaccount.com",
        GOOGLE_PROJECT_LOCATION = "us-central1",
        DJANGO_CLOUD_TASKS_EXECUTE_LOCALLY=False,
        DJANGO_CLOUD_TASKS_BLOCK_REMOTE_TASKS=True,
        DJANGO_CLOUD_TASKS_CREDENTIALS=None,
    )

    if config.getoption("--no-pkgroot"):
        sys.path.pop(0)

        # import django_cloud_tasks before pytest re-adds the package root directory.
        import django_cloud_tasks

        package_dir = os.path.join(os.getcwd(), "django_cloud_tasks")
        assert not django_cloud_tasks.__file__.startswith(package_dir)

    # Manifest storage will raise an exception if static files are not present (ie, a packaging failure).
    if config.getoption("--staticfiles"):
        import django_cloud_tasks

        settings.STATIC_ROOT = os.path.join(
            os.path.dirname(django_cloud_tasks.__file__), "static-root"
        )
        settings.STATICFILES_STORAGE = (
            "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
        )

    django.setup()

    if config.getoption("--staticfiles"):
        management.call_command("collectstatic", verbosity=0, interactive=False)
