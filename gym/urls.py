from django.urls import path

from . import api_views

urlpatterns = [
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
    path("api/presets/<int:preset_id>/quick-log/", api_views.preset_quick_log, name="api_preset_quick_log"),
    path("api/leaderboard/", api_views.leaderboard, name="api_leaderboard"),
    path("api/leaderboard/exercise/<int:exercise_id>/", api_views.leaderboard_exercise, name="api_leaderboard_exercise"),
    path("api/chat/", api_views.chat_list_create, name="api_chat"),
    path("api/coach/", api_views.coach_chat, name="api_coach"),
]
