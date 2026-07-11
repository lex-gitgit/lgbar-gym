import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gym", "0006_assign_owner"),
    ]

    operations = [
        migrations.AlterField(
            model_name="daypreset",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="day_presets",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="daypreset",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="workoutday",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="workout_days",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name="daypreset",
            constraint=models.UniqueConstraint(
                fields=["user", "name"], name="unique_preset_name_per_user"
            ),
        ),
    ]
