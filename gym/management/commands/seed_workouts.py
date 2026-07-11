from datetime import date, timedelta
from django.core.management.base import BaseCommand
from gym.models import Exercise, DayPreset, DayPresetExercise, WorkoutDay, WorkoutExercise, WorkoutSet

PUSH_EXERCISES = [
    ("Bench Press", [(60, 10), (65, 8), (65, 8), (70, 6)]),
    ("Overhead Press", [(35, 10), (37.5, 8), (40, 8)]),
    ("Triceps Pushdown", [(25, 12), (27.5, 10), (30, 10)]),
    ("Lateral Raise", [(10, 15), (12, 12), (12, 12)]),
]

PUSH_EXERCISES_2 = [
    ("Bench Press", [(65, 10), (70, 8), (72.5, 6), (72.5, 6)]),
    ("Incline Bench Press", [(50, 10), (55, 8), (55, 8)]),
    ("Overhead Press", [(37.5, 8), (40, 6), (40, 8)]),
    ("Skull Crushers", [(20, 12), (22.5, 10), (22.5, 10)]),
]

PUSH_EXERCISES_3 = [
    ("Bench Press", [(65, 10), (70, 8), (75, 6), (77.5, 5)]),
    ("Overhead Press", [(40, 8), (42.5, 6), (45, 5)]),
    ("Triceps Pushdown", [(27.5, 12), (30, 10), (32.5, 10)]),
    ("Lateral Raise", [(12, 12), (12, 12), (14, 10)]),
]

PULL_EXERCISES = [
    ("Deadlift", [(100, 8), (110, 6), (120, 5), (125, 5)]),
    ("Barbell Row", [(50, 10), (55, 10), (60, 8)]),
    ("Lat Pulldown", [(55, 10), (60, 8), (65, 8)]),
    ("Barbell Curl", [(20, 12), (22.5, 10), (22.5, 10)]),
]

PULL_EXERCISES_2 = [
    ("Deadlift", [(110, 6), (120, 5), (130, 4), (135, 3)]),
    ("Barbell Row", [(55, 10), (60, 8), (65, 8), (65, 8)]),
    ("Face Pull", [(15, 15), (17.5, 12), (20, 12)]),
    ("Hammer Curl", [(14, 12), (16, 10), (16, 10)]),
]

PULL_EXERCISES_3 = [
    ("Deadlift", [(115, 5), (125, 4), (135, 3), (140, 2)]),
    ("Barbell Row", [(60, 8), (65, 8), (70, 6), (70, 6)]),
    ("Pull-Ups", [(0, 10), (0, 8), (0, 7)]),
    ("Preacher Curl", [(18, 12), (20, 10), (20, 10)]),
]

LEGS_EXERCISES = [
    ("Squat", [(80, 10), (85, 8), (90, 6), (95, 5)]),
    ("Romanian Deadlift", [(60, 10), (65, 10), (70, 8)]),
    ("Leg Press", [(120, 12), (140, 10), (160, 10)]),
    ("Calf Raise", [(80, 15), (90, 12), (100, 12)]),
]

LEGS_EXERCISES_2 = [
    ("Squat", [(85, 8), (90, 6), (95, 5), (100, 3)]),
    ("Romanian Deadlift", [(65, 10), (70, 8), (75, 8)]),
    ("Leg Curl", [(35, 12), (40, 10), (40, 10)]),
    ("Leg Extension", [(50, 12), (55, 10), (60, 10)]),
]

PRESET_DEFS = {
    "Push": [name for name, _ in PUSH_EXERCISES + PUSH_EXERCISES_2 + PUSH_EXERCISES_3],
    "Pull": [name for name, _ in PULL_EXERCISES + PULL_EXERCISES_2 + PULL_EXERCISES_3],
    "Legs": [name for name, _ in LEGS_EXERCISES + LEGS_EXERCISES_2],
}

WORKOUTS = [
    ("Push", "Felt strong today", PUSH_EXERCISES, 28),
    ("Pull", "", PULL_EXERCISES, 25),
    ("Legs", "New squat PR!", LEGS_EXERCISES, 21),
    ("Push", "", PUSH_EXERCISES_2, 18),
    ("Pull", "Focused on form", PULL_EXERCISES_2, 14),
    ("Legs", "", LEGS_EXERCISES_2, 11),
    ("Push", "", PUSH_EXERCISES_3, 7),
    ("Pull", "Felt great", PULL_EXERCISES_3, 4),
]


class Command(BaseCommand):
    help = "Seed dummy workout logs for demo purposes"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing dummy data first")

    def handle(self, *args, **options):
        if options["clear"]:
            WorkoutSet.objects.all().delete()
            WorkoutExercise.objects.all().delete()
            WorkoutDay.objects.all().delete()
            DayPresetExercise.objects.all().delete()
            DayPreset.objects.all().delete()
            self.stdout.write("Cleared existing data.")

        preset_map = {}
        for name in PRESET_DEFS:
            preset, created = DayPreset.objects.get_or_create(name=name)
            preset_map[name] = preset
            if created:
                self.stdout.write(f"  Created preset: {name}")

        for preset_name, ex_names in PRESET_DEFS.items():
            for order, ex_name in enumerate(ex_names, start=1):
                try:
                    ex = Exercise.objects.get(name=ex_name)
                    DayPresetExercise.objects.get_or_create(
                        preset=preset_map[preset_name], exercise=ex, defaults={"order": order}
                    )
                except Exercise.DoesNotExist:
                    self.stdout.write(f"  Warning: Exercise '{ex_name}' not found, skipping")

        today = date.today()
        for preset_name, notes, exercises, offset in WORKOUTS:
            day_date = today - timedelta(days=offset)
            preset = preset_map.get(preset_name)
            day = WorkoutDay.objects.create(date=day_date, preset=preset, notes=notes)

            for order, (ex_name, sets) in enumerate(exercises, start=1):
                try:
                    exercise = Exercise.objects.get(name=ex_name)
                except Exercise.DoesNotExist:
                    self.stdout.write(f"  Warning: Exercise '{ex_name}' not found, skipping")
                    continue

                we = WorkoutExercise.objects.create(workout_day=day, exercise=exercise, order=order)
                for set_num, (weight, reps) in enumerate(sets, start=1):
                    WorkoutSet.objects.create(
                        workout_exercise=we, set_number=set_num,
                        weight=weight, reps=reps, weight_unit="kg",
                    )

            self.stdout.write(f"  Created workout: {day_date} - {preset_name} ({len(exercises)} exercises)")

        total = WorkoutDay.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Done. {total} workout days in the database."))
