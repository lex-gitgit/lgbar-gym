import json
from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from django.db import models, transaction

from .models import (
    DayPreset,
    DayPresetExercise,
    Exercise,
    WorkoutDay,
    WorkoutExercise,
    WorkoutSet,
)


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        return render(request, "gym/login.html", {"form": True})
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "gym/login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    days = WorkoutDay.objects.all()[:20]
    return render(request, "gym/dashboard.html", {"days": days})


@login_required
def exercise_list(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            Exercise.objects.get_or_create(name=name)
            messages.success(request, f'"{name}" added!')
        return redirect("exercise_list")
    exercises = Exercise.objects.all().order_by("name")
    return render(request, "gym/exercises.html", {"exercises": exercises})


@login_required
def exercise_delete(request, exercise_id):
    exercise = get_object_or_404(Exercise, id=exercise_id)
    exercise.delete()
    messages.success(request, f'"{exercise.name}" deleted.')
    return redirect("exercise_list")


@login_required
def day_create(request):
    presets = DayPreset.objects.all()
    exercises = Exercise.objects.all().order_by("name")

    preset_exercises = {}
    for p in presets:
        preset_exercises[str(p.id)] = [
            pe.exercise_id for pe in p.exercises.all()
        ]

    today = date.today().isoformat()

    if request.method == "POST":
        day_date = request.POST.get("date")
        preset_id = request.POST.get("preset") or None
        notes = request.POST.get("notes", "")
        exercise_ids = request.POST.get("exercises", "")

        if not day_date or not exercise_ids:
            messages.error(request, "Please fill in all fields.")
            return redirect("day_create")

        preset = DayPreset.objects.filter(id=preset_id).first() if preset_id else None
        ids = [int(x.strip()) for x in exercise_ids.split(",") if x.strip()]

        with transaction.atomic():
            day = WorkoutDay.objects.create(
                date=day_date, preset=preset, notes=notes
            )
            for i, eid in enumerate(ids):
                exercise = get_object_or_404(Exercise, id=eid)
                WorkoutExercise.objects.create(
                    workout_day=day, exercise=exercise, order=i
                )

        messages.success(request, "Workout logged!")
        return redirect("day_detail", day_id=day.id)

    return render(
        request,
        "gym/day_create.html",
        {
            "presets": presets,
            "exercises": exercises,
            "preset_exercises": json.dumps(preset_exercises),
            "today": today,
        },
    )


@login_required
def day_detail(request, day_id):
    day = get_object_or_404(WorkoutDay.objects.prefetch_related(
        "exercises__exercise", "exercises__sets"
    ), id=day_id)
    all_exercises = Exercise.objects.all().order_by("name")
    return render(
        request,
        "gym/day_detail.html",
        {"day": day, "all_exercises": all_exercises},
    )


@login_required
def day_add_exercise(request, day_id):
    day = get_object_or_404(WorkoutDay, id=day_id)
    if request.method == "POST":
        exercise_id = request.POST.get("exercise_id")
        if exercise_id:
            exercise = get_object_or_404(Exercise, id=exercise_id)
            max_order = day.exercises.aggregate(models.Max("order"))["order__max"]
            if max_order is None:
                max_order = -1
            WorkoutExercise.objects.create(
                workout_day=day, exercise=exercise, order=max_order + 1
            )
            messages.success(request, f'"{exercise.name}" added.')
    return redirect("day_detail", day_id=day.id)


@login_required
def day_remove_exercise(request, day_id, we_id):
    we = get_object_or_404(WorkoutExercise, id=we_id, workout_day_id=day_id)
    we.delete()
    messages.success(request, "Exercise removed.")
    return redirect("day_detail", day_id=day_id)


@login_required
def day_delete(request, day_id):
    day = get_object_or_404(WorkoutDay, id=day_id)
    day.delete()
    messages.success(request, "Workout day deleted.")
    return redirect("dashboard")


@login_required
def set_add(request, we_id):
    we = get_object_or_404(WorkoutExercise, id=we_id)
    if request.method == "POST":
        weight = request.POST.get("weight")
        weight_unit = request.POST.get("weight_unit", "kg")
        reps = request.POST.get("reps")
        if weight and reps:
            max_set = we.sets.aggregate(models.Max("set_number"))["set_number__max"] or 0
            WorkoutSet.objects.create(
                workout_exercise=we,
                set_number=max_set + 1,
                weight=weight,
                weight_unit=weight_unit,
                reps=reps,
            )
    return redirect("day_detail", day_id=we.workout_day_id)


@login_required
def set_delete(request, set_id):
    s = get_object_or_404(WorkoutSet, id=set_id)
    day_id = s.workout_exercise.workout_day_id
    s.delete()
    return redirect("day_detail", day_id=day_id)


@login_required
def preset_list(request):
    presets = DayPreset.objects.all()
    return render(request, "gym/presets.html", {"presets": presets})


@login_required
def preset_create(request):
    exercises = Exercise.objects.all().order_by("name")
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        exercise_ids = request.POST.get("exercises", "")
        if not name or not exercise_ids:
            messages.error(request, "Please provide a name and select exercises.")
            return redirect("preset_create")
        ids = [int(x.strip()) for x in exercise_ids.split(",") if x.strip()]
        with transaction.atomic():
            preset = DayPreset.objects.create(name=name)
            for i, eid in enumerate(ids):
                DayPresetExercise.objects.create(
                    preset=preset, exercise_id=eid, order=i
                )
        messages.success(request, f'Preset "{name}" created!')
        return redirect("preset_detail", preset_id=preset.id)
    return render(request, "gym/preset_form.html", {"exercises": exercises, "selected": []})


@login_required
def preset_edit(request, preset_id):
    preset = get_object_or_404(DayPreset, id=preset_id)
    exercises = Exercise.objects.all().order_by("name")
    selected = list(preset.exercises.values_list("exercise_id", flat=True))
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        exercise_ids = request.POST.get("exercises", "")
        if not name or not exercise_ids:
            messages.error(request, "Please provide a name and select exercises.")
            return redirect("preset_edit", preset_id=preset.id)
        ids = [int(x.strip()) for x in exercise_ids.split(",") if x.strip()]
        with transaction.atomic():
            preset.name = name
            preset.save()
            preset.exercises.all().delete()
            for i, eid in enumerate(ids):
                DayPresetExercise.objects.create(
                    preset=preset, exercise_id=eid, order=i
                )
        messages.success(request, f'Preset "{name}" updated!')
        return redirect("preset_detail", preset_id=preset.id)
    return render(
        request,
        "gym/preset_form.html",
        {"preset": preset, "exercises": exercises, "selected": selected},
    )


@login_required
def preset_detail(request, preset_id):
    preset = get_object_or_404(DayPreset.objects.prefetch_related("exercises__exercise"), id=preset_id)
    return render(request, "gym/preset_detail.html", {"preset": preset})


@login_required
def preset_delete(request, preset_id):
    preset = get_object_or_404(DayPreset, id=preset_id)
    preset.delete()
    messages.success(request, f'Preset "{preset.name}" deleted.')
    return redirect("preset_list")
