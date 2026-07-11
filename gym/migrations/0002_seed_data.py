from django.db import migrations
from django.contrib.auth.hashers import make_password


EXERCISES = [
    "Bench Press",
    "Incline Bench Press",
    "Decline Bench Press",
    "Dumbbell Flyes",
    "Push-Ups",
    "Lat Pulldown",
    "Pull-Ups",
    "Barbell Row",
    "T-Bar Row",
    "Seated Cable Row",
    "Face Pull",
    "Overhead Press",
    "Arnold Press",
    "Lateral Raise",
    "Front Raise",
    "Barbell Curl",
    "Dumbbell Curl",
    "Hammer Curl",
    "Preacher Curl",
    "Spider Curl",
    "Reverse Curl",
    "Triceps Pushdown",
    "Overhead Triceps Extension",
    "Skull Crushers",
    "Squat",
    "Front Squat",
    "Leg Press",
    "Romanian Deadlift",
    "Deadlift",
    "Leg Curl",
    "Leg Extension",
    "Calf Raise",
    "Plank",
    "Crunches",
    "Russian Twist",
    "Hanging Leg Raise",
]


def seed_exercises(apps, schema_editor):
    Exercise = apps.get_model("gym", "Exercise")
    for name in EXERCISES:
        Exercise.objects.get_or_create(name=name)


def create_user(apps, schema_editor):
    User = apps.get_model("auth", "User")
    if not User.objects.filter(username="user").exists():
        User.objects.create(
            username="user",
            password=make_password("1234"),
            is_staff=False,
            is_superuser=False,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("gym", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_exercises),
        migrations.RunPython(create_user),
    ]
