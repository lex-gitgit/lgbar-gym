import json
from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Max
from django.middleware.csrf import get_token
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from .models import (
    DayPreset,
    DayPresetExercise,
    Exercise,
    WorkoutDay,
    WorkoutExercise,
    WorkoutSet,
)
from .serializers import (
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

        preset = DayPreset.objects.filter(id=preset_id).first() if preset_id else None
        ids = [int(x.strip()) for x in exercise_ids.split(",") if x.strip()]

        with transaction.atomic():
            day = WorkoutDay.objects.create(date=day_date, preset=preset, notes=notes)
            for i, eid in enumerate(ids):
                exercise = get_object_or_404(Exercise, id=eid)
                WorkoutExercise.objects.create(workout_day=day, exercise=exercise, order=i)

        return Response({"id": day.id})

    days = WorkoutDay.objects.all()[:20]
    return Response(WorkoutDayListSerializer(days, many=True).data)


@api_view(["GET", "DELETE"])
def day_detail(request, day_id):
    try:
        day = WorkoutDay.objects.prefetch_related(
            "exercises__exercise", "exercises__sets"
        ).get(id=day_id)
    except WorkoutDay.DoesNotExist:
        raise NotFound()

    if request.method == "DELETE":
        day.delete()
        return Response({"ok": True})

    return Response(WorkoutDayDetailSerializer(day).data)


@api_view(["POST"])
def day_add_exercise(request, day_id):
    day = get_object_or_404(WorkoutDay, id=day_id)
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
    we = get_object_or_404(WorkoutExercise, id=we_id, workout_day_id=day_id)
    we.delete()
    return Response({"ok": True})


# --- Sets ---

@api_view(["POST"])
def set_add(request, we_id):
    we = get_object_or_404(WorkoutExercise, id=we_id)
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
    s = get_object_or_404(WorkoutSet, id=set_id)
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
        ids = [int(x.strip()) for x in exercise_ids.split(",") if x.strip()]
        with transaction.atomic():
            preset = DayPreset.objects.create(name=name)
            for i, eid in enumerate(ids):
                DayPresetExercise.objects.create(preset=preset, exercise_id=eid, order=i)
        return Response({"id": preset.id})

    presets = DayPreset.objects.all()
    return Response(DayPresetSerializer(presets, many=True).data)


@api_view(["GET", "PUT", "DELETE"])
def preset_detail(request, preset_id):
    try:
        preset = DayPreset.objects.prefetch_related("exercises__exercise").get(id=preset_id)
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


def get_object_or_404(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        raise NotFound()
