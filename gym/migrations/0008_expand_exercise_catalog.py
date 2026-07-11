from django.db import migrations


# Additive only — never rename/remove the original 36 (0002/0004), since
# WorkoutExercise/DayPresetExercise reference Exercise by FK and renaming
# would silently relabel real logged history. Where an existing name is
# equipment-ambiguous (e.g. "Bench Press", "Overhead Press", "Squat"), the
# convention here is to leave it as-is (implicitly barbell) and add the
# missing Dumbbell/Machine/Cable variants alongside it, rather than
# creating a confusing near-duplicate like "Barbell Bench Press" next to
# "Bench Press".
NEW_EXERCISES = {
    "chest": [
        "Dumbbell Bench Press",
        "Dumbbell Incline Press",
        "Dumbbell Decline Press",
        "Machine Chest Press",
        "Cable Fly",
        "Pec Deck",
        "Chest Dip",
        "Close-Grip Push-Ups",
    ],
    "back": [
        "Dumbbell Row",
        "Machine Row",
        "Chin-Ups",
        "Straight-Arm Pulldown",
        "Barbell Shrug",
        "Dumbbell Shrug",
        "Good Morning",
        "Inverted Row",
    ],
    "shoulders": [
        "Dumbbell Shoulder Press",
        "Machine Shoulder Press",
        "Cable Lateral Raise",
        "Machine Lateral Raise",
        "Dumbbell Rear Delt Fly",
        "Cable Rear Delt Fly",
        "Machine Rear Delt Fly",
        "Barbell Upright Row",
        "Push Press",
    ],
    "biceps": [
        "Cable Curl",
        "Machine Preacher Curl",
        "EZ-Bar Curl",
        "Concentration Curl",
        "Cable Hammer Curl",
        "Incline Dumbbell Curl",
        "Zottman Curl",
    ],
    "triceps": [
        "Dumbbell Triceps Extension",
        "Cable Overhead Triceps Extension",
        "Machine Triceps Extension",
        "Close-Grip Bench Press",
        "Triceps Dip",
        "Bench Dip",
        "Dumbbell Kickback",
    ],
    "legs": [
        "Goblet Squat",
        "Hack Squat",
        "Bulgarian Split Squat",
        "Walking Lunge",
        "Hip Thrust",
        "Glute Bridge",
        "Dumbbell Deadlift",
        "Sumo Deadlift",
        "Step-Up",
        "Seated Calf Raise",
        "Standing Calf Raise",
    ],
    "core": [
        "Sit-Ups",
        "Bicycle Crunch",
        "Cable Crunch",
        "Ab Wheel Rollout",
        "Side Plank",
        "Mountain Climbers",
        "Lying Leg Raise",
        "Machine Ab Crunch",
    ],
    "cardio": [
        "Treadmill Running",
        "Stationary Bike",
        "Rowing Machine",
        "Jump Rope",
        "Stair Climber",
        "Elliptical",
    ],
}


def seed_exercises(apps, schema_editor):
    Exercise = apps.get_model("gym", "Exercise")
    for body_part, names in NEW_EXERCISES.items():
        for name in names:
            Exercise.objects.get_or_create(name=name, defaults={"body_part": body_part})


class Migration(migrations.Migration):

    dependencies = [
        ("gym", "0007_finalize_user_fields"),
    ]

    operations = [
        migrations.RunPython(seed_exercises, migrations.RunPython.noop),
    ]
