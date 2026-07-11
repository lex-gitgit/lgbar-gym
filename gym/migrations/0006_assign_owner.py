from django.db import migrations


def assign_owner(apps, schema_editor):
    User = apps.get_model("auth", "User")
    WorkoutDay = apps.get_model("gym", "WorkoutDay")
    DayPreset = apps.get_model("gym", "DayPreset")

    owner = User.objects.filter(username="user").first()
    if owner is None:
        if WorkoutDay.objects.exists() or DayPreset.objects.exists():
            raise RuntimeError(
                "No 'user' account found to assign existing WorkoutDay/DayPreset rows to."
            )
        return

    WorkoutDay.objects.filter(user__isnull=True).update(user=owner)
    DayPreset.objects.filter(user__isnull=True).update(user=owner)


class Migration(migrations.Migration):

    dependencies = [
        ("gym", "0005_add_user_fields_nullable"),
    ]

    operations = [
        migrations.RunPython(assign_owner, migrations.RunPython.noop),
    ]
