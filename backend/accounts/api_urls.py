"""accounts.api_urls

Frontend JavaScript calls a set of JSON endpoints from `dashboard.html`.
This module wires those paths to view functions.
"""

from django.urls import path

from . import views

urlpatterns = [
    # Notifications (received requests)
    path("notifications/", views.notifications_view, name="notifications"),

    # Interest flow (send/toggle, accept, decline)
    path("interest/<str:profile_id>/", views.interest_toggle_view, name="interest_toggle"),
    path(
        "interest/accept/<str:profile_id>/",
        views.interest_accept_view,
        name="interest_accept",
    ),
    path(
        "interest/decline/<str:profile_id>/",
        views.interest_decline_view,
        name="interest_decline",
    ),

    # Pinned connections (accepted requests)
    path("pinned/", views.pinned_view, name="pinned"),

    # Profile details for modal
    path("profile/<str:profile_id>/", views.profile_detail_view, name="profile_detail"),

    # Connection status (for main-grid button sync)
    path(
        "connection-status/<str:profile_id>/",
        views.connection_status_view,
        name="connection_status",
    ),

    # Wishlist / shortlist
    path("wishlist/toggle/<str:profile_id>/", views.wishlist_toggle_view, name="wishlist_toggle"),
    path("wishlist/count/", views.wishlist_count_view, name="wishlist_count"),
    path("wishlist/", views.wishlist_list_view, name="wishlist_list"),

    # Conversations + messages
    path("conversations/", views.conversations_view, name="conversations"),
    path("messages/<str:partner_id>/", views.messages_thread_view, name="messages_thread"),
    path("messages/send/<str:partner_id>/", views.messages_send_view, name="messages_send"),
]



