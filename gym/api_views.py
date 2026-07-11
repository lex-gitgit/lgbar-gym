import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max, Q
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from .models import (
    ChatMessage,
    DayPreset,
    DayPresetExercise,
    Exercise,
    WorkoutDay,
    WorkoutExercise,
    WorkoutSet,
)
from .serializers import (
    ChatMessageSerializer,
    DayPresetDetailSerializer,
    DayPresetSerializer,
    ExerciseSerializer,
    WorkoutDayDetailSerializer,
    WorkoutDayListSerializer,
)


# --- CSRF ---

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def csrf_token(request):
    get_token(request)
    return Response({"ok": True})


# --- Auth ---

@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({"username": user.username})
    return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response({"ok": True})


@api_view(["GET"])
def me_view(request):
    return Response({"username": request.user.username})


# --- Exercises ---

@api_view(["GET", "POST"])
def exercise_list(request):
    if request.method == "POST":
        name = request.data.get("name", "").strip()
        body_part = request.data.get("body_part", "chest")
        if name:
            Exercise.objects.get_or_create(name=name, defaults={"body_part": body_part})
        return Response({"ok": True})
    qs = Exercise.objects.all()
    search = request.query_params.get("search", "")
    if search:
        qs = qs.filter(name__icontains=search)
    body_part = request.query_params.get("body_part", "")
    if body_part:
        qs = qs.filter(body_part=body_part)
    qs = qs.order_by("body_part", "name")
    return Response(ExerciseSerializer(qs, many=True).data)


@api_view(["DELETE"])
def exercise_delete(request, exercise_id):
    exercise = get_object_or_404(Exercise, id=exercise_id)
    if WorkoutExercise.objects.filter(exercise=exercise).exists():
        return Response(
            {"error": "This exercise is logged in workout history and can't be deleted."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if DayPresetExercise.objects.filter(exercise=exercise).exists():
        return Response(
            {"error": "This exercise is used in a preset and can't be deleted."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    exercise.delete()
    return Response({"ok": True})


# --- Workout Days ---

@api_view(["GET", "POST"])
def day_list_create(request):
    if request.method == "POST":
        day_date = request.data.get("date")
        preset_id = request.data.get("preset") or None
        notes = request.data.get("notes", "")
        exercise_ids = request.data.get("exercises", "")

        if not day_date or not exercise_ids:
            return Response(
                {"error": "Please fill in all fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        preset = (
            DayPreset.objects.filter(id=preset_id, user=request.user).first()
            if preset_id
            else None
        )
        ids = [int(x.strip()) for x in exercise_ids.split(",") if x.strip()]

        with transaction.atomic():
            day = WorkoutDay.objects.create(
                date=day_date, preset=preset, notes=notes, user=request.user
            )
            for i, eid in enumerate(ids):
                exercise = get_object_or_404(Exercise, id=eid)
                WorkoutExercise.objects.create(workout_day=day, exercise=exercise, order=i)

        return Response({"id": day.id})

    days = WorkoutDay.objects.filter(user=request.user)[:20]
    return Response(WorkoutDayListSerializer(days, many=True).data)


@api_view(["GET", "DELETE"])
def day_detail(request, day_id):
    try:
        day = WorkoutDay.objects.prefetch_related(
            "exercises__exercise", "exercises__sets"
        ).get(id=day_id, user=request.user)
    except WorkoutDay.DoesNotExist:
        raise NotFound()

    if request.method == "DELETE":
        day.delete()
        return Response({"ok": True})

    return Response(WorkoutDayDetailSerializer(day).data)


@api_view(["POST"])
def day_add_exercise(request, day_id):
    day = get_object_or_404(WorkoutDay, id=day_id, user=request.user)
    exercise_id = request.data.get("exercise_id")
    if exercise_id:
        exercise = get_object_or_404(Exercise, id=exercise_id)
        max_order = day.exercises.aggregate(Max("order"))["order__max"]
        if max_order is None:
            max_order = -1
        WorkoutExercise.objects.create(
            workout_day=day, exercise=exercise, order=max_order + 1
        )
    return Response({"ok": True})


@api_view(["DELETE"])
def day_remove_exercise(request, day_id, we_id):
    we = get_object_or_404(
        WorkoutExercise, id=we_id, workout_day_id=day_id, workout_day__user=request.user
    )
    we.delete()
    return Response({"ok": True})


# --- Sets ---

@api_view(["POST"])
def set_add(request, we_id):
    we = get_object_or_404(WorkoutExercise, id=we_id, workout_day__user=request.user)
    weight = request.data.get("weight")
    weight_unit = request.data.get("weight_unit", "kg")
    reps = request.data.get("reps")
    if weight and reps:
        max_set = we.sets.aggregate(Max("set_number"))["set_number__max"] or 0
        WorkoutSet.objects.create(
            workout_exercise=we,
            set_number=max_set + 1,
            weight=weight,
            weight_unit=weight_unit,
            reps=reps,
        )
    return Response({"ok": True})


@api_view(["DELETE"])
def set_delete(request, set_id):
    s = get_object_or_404(
        WorkoutSet, id=set_id, workout_exercise__workout_day__user=request.user
    )
    s.delete()
    return Response({"ok": True})


# --- Presets ---

@api_view(["GET", "POST"])
def preset_list_create(request):
    if request.method == "POST":
        name = request.data.get("name", "").strip()
        exercise_ids = request.data.get("exercises", "")
        if not name or not exercise_ids:
            return Response(
                {"error": "Please provide a name and select exercises."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if DayPreset.objects.filter(user=request.user, name=name).exists():
            return Response(
                {"error": "You already have a preset with this name."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ids = [int(x.strip()) for x in exercise_ids.split(",") if x.strip()]
        with transaction.atomic():
            preset = DayPreset.objects.create(name=name, user=request.user)
            for i, eid in enumerate(ids):
                DayPresetExercise.objects.create(preset=preset, exercise_id=eid, order=i)
        return Response({"id": preset.id})

    presets = DayPreset.objects.filter(user=request.user)
    return Response(DayPresetSerializer(presets, many=True).data)


@api_view(["GET", "PUT", "DELETE"])
def preset_detail(request, preset_id):
    try:
        preset = DayPreset.objects.prefetch_related("exercises__exercise").get(
            id=preset_id, user=request.user
        )
    except DayPreset.DoesNotExist:
        raise NotFound()

    if request.method == "PUT":
        name = request.data.get("name", "").strip()
        exercise_ids = request.data.get("exercises", "")
        if not name or not exercise_ids:
            return Response(
                {"error": "Please provide a name and select exercises."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            DayPreset.objects.filter(user=request.user, name=name)
            .exclude(id=preset.id)
            .exists()
        ):
            return Response(
                {"error": "You already have a preset with this name."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ids = [int(x.strip()) for x in exercise_ids.split(",") if x.strip()]
        with transaction.atomic():
            preset.name = name
            preset.save()
            preset.exercises.all().delete()
            for i, eid in enumerate(ids):
                DayPresetExercise.objects.create(preset=preset, exercise_id=eid, order=i)
        return Response(DayPresetDetailSerializer(preset).data)

    if request.method == "DELETE":
        preset.delete()
        return Response({"ok": True})

    return Response(DayPresetDetailSerializer(preset).data)


@api_view(["POST"])
def preset_quick_log(request, preset_id):
    """Create a new WorkoutDay from a preset in one tap, pre-filling each
    exercise with the sets from the last time it was logged (regardless of
    which day/preset that was), so the user only has to edit what changed."""
    preset = get_object_or_404(DayPreset, id=preset_id, user=request.user)
    preset_exercises = list(preset.exercises.select_related("exercise"))
    if not preset_exercises:
        return Response(
            {"error": "This preset has no exercises."}, status=status.HTTP_400_BAD_REQUEST
        )

    day_date = request.data.get("date") or date.today().isoformat()

    with transaction.atomic():
        day = WorkoutDay.objects.create(
            date=day_date, preset=preset, notes="", user=request.user
        )
        for dpe in preset_exercises:
            we = WorkoutExercise.objects.create(
                workout_day=day, exercise=dpe.exercise, order=dpe.order
            )
            last_we = (
                WorkoutExercise.objects.filter(
                    exercise=dpe.exercise, workout_day__user=request.user
                )
                .exclude(workout_day_id=day.id)
                .annotate(set_count=Count("sets"))
                .filter(set_count__gt=0)
                .order_by("-workout_day__date", "-workout_day__created_at", "-id")
                .prefetch_related("sets")
                .first()
            )
            if last_we:
                for s in last_we.sets.all():
                    WorkoutSet.objects.create(
                        workout_exercise=we,
                        set_number=s.set_number,
                        reps=s.reps,
                        weight=s.weight,
                        weight_unit=s.weight_unit,
                    )

    return Response({"id": day.id})


# --- Leaderboard ---

BIG_LIFTS = ["Bench Press", "Squat", "Deadlift", "Overhead Press"]
LB_TO_KG = Decimal("0.453592")


def _to_kg(weight, weight_unit):
    return weight if weight_unit == WorkoutSet.KG else weight * LB_TO_KG


def _best_prs(exercise_ids, user_ids):
    """All-time best estimated 1RM (Epley) per user per exercise, among the
    given exercises/users. Returns {user_id: {exercise_name: {weight_kg, reps, e1rm}}}
    with Decimal values — callers convert to float/round at the response boundary."""
    sets = WorkoutSet.objects.filter(
        workout_exercise__exercise_id__in=exercise_ids,
        workout_exercise__workout_day__user_id__in=user_ids,
    ).select_related("workout_exercise__exercise", "workout_exercise__workout_day")

    pr_by_user = defaultdict(dict)
    for s in sets:
        uid = s.workout_exercise.workout_day.user_id
        name = s.workout_exercise.exercise.name
        kg = _to_kg(s.weight, s.weight_unit)
        e1rm = kg * (Decimal("1") + Decimal(s.reps) / Decimal("30"))
        current = pr_by_user[uid].get(name)
        if current is None or e1rm > current["e1rm"]:
            pr_by_user[uid][name] = {"weight_kg": kg, "reps": s.reps, "e1rm": e1rm}
    return pr_by_user


@api_view(["GET"])
def leaderboard(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    users = list(
        User.objects.filter(is_active=True, is_superuser=False).annotate(
            week_count=Count(
                "workout_days", filter=Q(workout_days__date__gte=week_start), distinct=True
            ),
            month_count=Count(
                "workout_days", filter=Q(workout_days__date__gte=month_start), distinct=True
            ),
        )
    )
    user_ids = [u.id for u in users]

    # Volume this week (kg), normalized across weight units.
    week_sets = WorkoutSet.objects.filter(
        workout_exercise__workout_day__user_id__in=user_ids,
        workout_exercise__workout_day__date__gte=week_start,
    ).select_related("workout_exercise__workout_day")

    volume_by_user = defaultdict(Decimal)
    for s in week_sets:
        uid = s.workout_exercise.workout_day.user_id
        volume_by_user[uid] += _to_kg(s.weight, s.weight_unit) * s.reps

    # All-time best estimated 1RM (Epley) per user per big lift.
    big_lift_ids = Exercise.objects.filter(name__in=BIG_LIFTS).values_list("id", flat=True)
    pr_by_user = _best_prs(big_lift_ids, user_ids)

    # Longest current streak of consecutive weeks (including this week) with a workout.
    weeks_by_user = defaultdict(set)
    for uid, day_date in WorkoutDay.objects.filter(user_id__in=user_ids).values_list(
        "user_id", "date"
    ):
        weeks_by_user[uid].add(day_date - timedelta(days=day_date.weekday()))

    def streak_for(uid):
        streak = 0
        cursor = week_start
        while cursor in weeks_by_user.get(uid, ()):
            streak += 1
            cursor -= timedelta(days=7)
        return streak

    entries = [
        {
            "username": u.username,
            "week_count": u.week_count,
            "month_count": u.month_count,
            "week_volume_kg": round(float(volume_by_user.get(u.id, 0)), 1),
            "streak_weeks": streak_for(u.id),
            "prs": {
                name: {
                    "weight_kg": round(float(pr["weight_kg"]), 1),
                    "reps": pr["reps"],
                    "e1rm": round(float(pr["e1rm"]), 1),
                }
                for name, pr in pr_by_user.get(u.id, {}).items()
            },
        }
        for u in users
    ]
    entries.sort(key=lambda e: (-e["week_count"], -e["month_count"], e["username"]))

    return Response(
        {
            "week_start": week_start,
            "month_start": month_start,
            "big_lifts": BIG_LIFTS,
            "entries": entries,
        }
    )


@api_view(["GET"])
def leaderboard_exercise(request, exercise_id):
    try:
        exercise = Exercise.objects.get(id=exercise_id)
    except Exercise.DoesNotExist:
        raise NotFound()

    user_ids = list(
        User.objects.filter(is_active=True, is_superuser=False).values_list("id", flat=True)
    )
    pr_by_user = _best_prs([exercise.id], user_ids)
    usernames = dict(User.objects.filter(id__in=pr_by_user.keys()).values_list("id", "username"))

    entries = [
        {
            "username": usernames[uid],
            "weight_kg": round(float(prs[exercise.name]["weight_kg"]), 1),
            "reps": prs[exercise.name]["reps"],
            "e1rm": round(float(prs[exercise.name]["e1rm"]), 1),
        }
        for uid, prs in pr_by_user.items()
    ]
    entries.sort(key=lambda e: -e["e1rm"])

    return Response({"exercise": {"id": exercise.id, "name": exercise.name}, "entries": entries})


# --- Chat ---

@api_view(["GET", "POST"])
def chat_list_create(request):
    if request.method == "POST":
        text = str(request.data.get("text", "")).strip()
        if not text:
            return Response(
                {"error": "Message cannot be empty."}, status=status.HTTP_400_BAD_REQUEST
            )
        if len(text) > 1000:
            return Response(
                {"error": "Message too long (max 1000 characters)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        msg = ChatMessage.objects.create(user=request.user, text=text)
        return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    qs = ChatMessage.objects.select_related("user")
    after = request.query_params.get("after")
    if after and after.isdigit():
        messages = list(qs.filter(id__gt=int(after))[:200])
    else:
        messages = list(reversed(qs.order_by("-id")[:50]))
    return Response(ChatMessageSerializer(messages, many=True).data)


def get_object_or_404(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        raise NotFound()
