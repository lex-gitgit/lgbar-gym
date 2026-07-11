from django.urls import path

from . import api_views, views

urlpatterns = [
    # Template-based views (existing)
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("exercises/", views.exercise_list, name="exercise_list"),
    path("exercises/<int:exercise_id>/delete/", views.exercise_delete, name="exercise_delete"),
    path("day/new/", views.day_create, name="day_create"),
    path("day/<int:day_id>/", views.day_detail, name="day_detail"),
    path("day/<int:day_id>/add-exercise/", views.day_add_exercise, name="day_add_exercise"),
    path("day/<int:day_id>/remove-exercise/<int:we_id>/", views.day_remove_exercise, name="day_remove_exercise"),
    path("day/<int:day_id>/delete/", views.day_delete, name="day_delete"),
    path("sets/add/<int:we_id>/", views.set_add, name="set_add"),
    path("sets/<int:set_id>/delete/", views.set_delete, name="set_delete"),
    path("presets/", views.preset_list, name="preset_list"),
    path("presets/new/", views.preset_create, name="preset_create"),
    path("presets/<int:preset_id>/", views.preset_detail, name="preset_detail"),
    path("presets/<int:preset_id>/edit/", views.preset_edit, name="preset_edit"),
    path("presets/<int:preset_id>/delete/", views.preset_delete, name="preset_delete"),
    # API views
    path("api/csrf/", api_views.csrf_token, name="api_csrf"),
    path("api/login/", api_views.login_view, name="api_login"),
    path("api/logout/", api_views.logout_view, name="api_logout"),
    path("api/me/", api_views.me_view, name="api_me"),
    path("api/exercises/", api_views.exercise_list, name="api_exercise_list"),
    path("api/exercises/<int:exercise_id>/", api_views.exercise_delete, name="api_exercise_delete"),
    path("api/days/", api_views.day_list_create, name="api_day_list_create"),
    path("api/days/<int:day_id>/", api_views.day_detail, name="api_day_detail"),
    path("api/days/<int:day_id>/add-exercise/", api_views.day_add_exercise, name="api_day_add_exercise"),
    path("api/days/<int:day_id>/remove-exercise/<int:we_id>/", api_views.day_remove_exercise, name="api_day_remove_exercise"),
    path("api/sets/<int:we_id>/add/", api_views.set_add, name="api_set_add"),
    path("api/sets/<int:set_id>/delete/", api_views.set_delete, name="api_set_delete"),
    path("api/presets/", api_views.preset_list_create, name="api_preset_list_create"),
    path("api/presets/<int:preset_id>/", api_views.preset_detail, name="api_preset_detail"),
]
