from django.conf import settings
from django.db import models


class Exercise(models.Model):
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    BICEPS = "biceps"
    TRICEPS = "triceps"
    LEGS = "legs"
    CORE = "core"
    CARDIO = "cardio"

    BODY_PARTS = [
        (CHEST, "Chest"),
        (BACK, "Back"),
        (SHOULDERS, "Shoulders"),
        (BICEPS, "Biceps"),
        (TRICEPS, "Triceps"),
        (LEGS, "Legs"),
        (CORE, "Core"),
        (CARDIO, "Cardio"),
    ]

    name = models.CharField(max_length=100, unique=True)
    body_part = models.CharField(max_length=20, choices=BODY_PARTS, default=CHEST)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DayPreset(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="day_presets"
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_preset_name_per_user"
            )
        ]

    def __str__(self):
        return self.name


class DayPresetExercise(models.Model):
    preset = models.ForeignKey(DayPreset, on_delete=models.CASCADE, related_name="exercises")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ["preset", "exercise"]


class WorkoutDay(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workout_days"
    )
    date = models.DateField()
    preset = models.ForeignKey(
        DayPreset, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        label = self.preset.name if self.preset else "Custom"
        return f"{self.date} - {label}"


class WorkoutExercise(models.Model):
    workout_day = models.ForeignKey(
        WorkoutDay, on_delete=models.CASCADE, related_name="exercises"
    )
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.exercise.name} in {self.workout_day}"


class WorkoutSet(models.Model):
    KG = "kg"
    LBS = "lbs"
    UNIT_CHOICES = [(KG, "kg"), (LBS, "lbs")]

    workout_exercise = models.ForeignKey(
        WorkoutExercise, on_delete=models.CASCADE, related_name="sets"
    )
    set_number = models.IntegerField()
    reps = models.IntegerField()
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    weight_unit = models.CharField(max_length=3, choices=UNIT_CHOICES, default=KG)

    class Meta:
        ordering = ["set_number"]

    def __str__(self):
        return f"Set {self.set_number}: {self.weight}{self.weight_unit} x {self.reps}"


class ChatMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages"
    )
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.user.username}: {self.text[:30]}"
