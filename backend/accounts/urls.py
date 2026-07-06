from django.urls import path
from . import views

urlpatterns = [
    # Root should show login page (not dashboard) to avoid redirect loops
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login_alt"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/<str:profile_id>/", views.profile_detail, name="profile_detail"),
    path("interest/<str:profile_id>/", views.toggle_interest, name="toggle_interest"),

    # Notifications + Requests + Chat
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("interest/accept/<str:profile_id>/", views.interest_accept, name="interest_accept"),
    path("interest/decline/<str:profile_id>/", views.interest_decline, name="interest_decline"),
    path("conversations/", views.conversations_list, name="conversations_list"),
    path("messages/<str:partner_id>/", views.messages_list, name="messages_list"),
    path("messages/send/<str:partner_id>/", views.messages_send, name="messages_send"),

    path("edit-profile/", views.edit_profile_view, name="edit_profile"),
    path("settings/", views.settings_view, name="settings"),
]

