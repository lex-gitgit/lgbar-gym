from django.db import migrations


BODY_PARTS = {
    "Bench Press": "chest",
    "Incline Bench Press": "chest",
    "Decline Bench Press": "chest",
    "Dumbbell Flyes": "chest",
    "Push-Ups": "chest",
    "Lat Pulldown": "back",
    "Pull-Ups": "back",
    "Barbell Row": "back",
    "T-Bar Row": "back",
    "Seated Cable Row": "back",
    "Face Pull": "back",
    "Overhead Press": "shoulders",
    "Arnold Press": "shoulders",
    "Lateral Raise": "shoulders",
    "Front Raise": "shoulders",
    "Barbell Curl": "biceps",
    "Dumbbell Curl": "biceps",
    "Hammer Curl": "biceps",
    "Preacher Curl": "biceps",
    "Spider Curl": "biceps",
    "Reverse Curl": "biceps",
    "Triceps Pushdown": "triceps",
    "Overhead Triceps Extension": "triceps",
    "Skull Crushers": "triceps",
    "Squat": "legs",
    "Front Squat": "legs",
    "Leg Press": "legs",
    "Romanian Deadlift": "legs",
    "Deadlift": "legs",
    "Leg Curl": "legs",
    "Leg Extension": "legs",
    "Calf Raise": "legs",
    "Plank": "core",
    "Crunches": "core",
    "Russian Twist": "core",
    "Hanging Leg Raise": "core",
}


def assign_body_parts(apps, schema_editor):
    Exercise = apps.get_model("gym", "Exercise")
    for name, body_part in BODY_PARTS.items():
        Exercise.objects.filter(name=name).update(body_part=body_part)


class Migration(migrations.Migration):

    dependencies = [
        ("gym", "0003_exercise_body_part"),
    ]

    operations = [
        migrations.RunPython(assign_body_parts),
    ]
