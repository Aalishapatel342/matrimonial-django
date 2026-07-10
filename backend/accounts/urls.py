from django.urls import path, include

from . import views
from .api_urls import urlpatterns as api_urlpatterns

urlpatterns = [
    # Root should not be the login target; it causes redirect loops when session is missing.
    # Use the real login route for redirect("login").
    path("", views.dashboard_view, name="dashboard_root"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),

    path("dashboard-test/", views.dashboard_view, name="dashboard_test"),
    path("settings/", views.settings_view, name="settings"),
    path("debug/session/", views.debug_session_view, name="debug_session"),
    path("edit-profile/", views.edit_profile_view, name="edit_profile"),
    path("", views.edit_profile_view, name="edit_profile_root"),
    path("", include(api_urlpatterns)),
]




