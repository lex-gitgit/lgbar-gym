import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    DayPreset,
    DayPresetExercise,
    Exercise,
    WorkoutDay,
    WorkoutExercise,
    WorkoutSet,
)

# Names not in seed data (migration 0002_seed_data has 36 exercises)
EX_ALPHA = "ZZ Test Alpha"
EX_BETA = "ZZ Test Beta"
EX_GAMMA = "ZZ Test Gamma"
EX_DELTA = "ZZ Test Delta"


class ExerciseModelTest(TestCase):
    def test_create_exercise(self):
        e = Exercise.objects.create(name=EX_ALPHA)
        self.assertEqual(str(e), EX_ALPHA)
        self.assertIsNotNone(e.created_at)

    def test_name_unique(self):
        Exercise.objects.create(name=EX_ALPHA)
        with self.assertRaises(Exception):
            Exercise.objects.create(name=EX_ALPHA)

    def test_ordering_by_name(self):
        Exercise.objects.create(name="ZZZ B")
        Exercise.objects.create(name="ZZZ A")
        exercises = list(Exercise.objects.filter(name__startswith="ZZZ ").order_by("name"))
        self.assertEqual(exercises[0].name, "ZZZ A")
        self.assertEqual(exercises[1].name, "ZZZ B")


class DayPresetModelTest(TestCase):
    def setUp(self):
        self.exercise = Exercise.objects.create(name=EX_ALPHA)

    def test_create_preset(self):
        p = DayPreset.objects.create(name="ZZ Test Preset")
        self.assertEqual(str(p), "ZZ Test Preset")
        self.assertIsNotNone(p.created_at)

    def test_preset_with_exercises(self):
        p = DayPreset.objects.create(name="ZZ Test Preset B")
        e2 = Exercise.objects.create(name=EX_BETA)
        DayPresetExercise.objects.create(preset=p, exercise=self.exercise, order=0)
        DayPresetExercise.objects.create(preset=p, exercise=e2, order=1)
        self.assertEqual(p.exercises.count(), 2)

    def test_preset_exercise_order(self):
        p = DayPreset.objects.create(name="ZZ Test Order")
        e1 = Exercise.objects.create(name=EX_BETA)
        e2 = Exercise.objects.create(name=EX_GAMMA)
        DayPresetExercise.objects.create(preset=p, exercise=e2, order=1)
        DayPresetExercise.objects.create(preset=p, exercise=e1, order=0)
        exercises = list(p.exercises.all())
        self.assertEqual(exercises[0].exercise.name, EX_BETA)
        self.assertEqual(exercises[1].exercise.name, EX_GAMMA)

    def test_preset_exercise_unique_together(self):
        p = DayPreset.objects.create(name="ZZ Test Unique")
        DayPresetExercise.objects.create(preset=p, exercise=self.exercise, order=0)
        with self.assertRaises(Exception):
            DayPresetExercise.objects.create(preset=p, exercise=self.exercise, order=1)


class WorkoutDayModelTest(TestCase):
    def setUp(self):
        self.preset = DayPreset.objects.create(name="ZZ Push Day")

    def test_create_workout_day_without_preset(self):
        wd = WorkoutDay.objects.create(date="2025-01-01")
        self.assertEqual(str(wd), "2025-01-01 - Custom")
        self.assertIsNone(wd.preset)

    def test_create_workout_day_with_preset(self):
        wd = WorkoutDay.objects.create(date="2025-01-01", preset=self.preset)
        self.assertEqual(str(wd), "2025-01-01 - ZZ Push Day")

    def test_ordering_newest_first(self):
        d1 = WorkoutDay.objects.create(date="2025-01-01")
        d2 = WorkoutDay.objects.create(date="2025-01-02")
        days = list(WorkoutDay.objects.all())
        self.assertEqual(days[0], d2)
        self.assertEqual(days[1], d1)

    def test_notes_blank_by_default(self):
        wd = WorkoutDay.objects.create(date="2025-01-01")
        self.assertEqual(wd.notes, "")

    def test_preset_set_null_on_delete(self):
        wd = WorkoutDay.objects.create(date="2025-01-01", preset=self.preset)
        self.preset.delete()
        wd.refresh_from_db()
        self.assertIsNone(wd.preset)


class WorkoutExerciseModelTest(TestCase):
    def setUp(self):
        self.exercise = Exercise.objects.create(name=EX_ALPHA)
        self.day = WorkoutDay.objects.create(date="2025-01-01")

    def test_create_workout_exercise(self):
        we = WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=0
        )
        self.assertIn(EX_ALPHA, str(we))

    def test_ordering(self):
        e2 = Exercise.objects.create(name=EX_BETA)
        we1 = WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=1
        )
        we2 = WorkoutExercise.objects.create(
            workout_day=self.day, exercise=e2, order=0
        )
        exercises = list(self.day.exercises.all())
        self.assertEqual(exercises[0], we2)
        self.assertEqual(exercises[1], we1)

    def test_cascade_delete_with_workout_day(self):
        WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=0
        )
        self.day.delete()
        self.assertEqual(WorkoutExercise.objects.count(), 0)

    def test_notes_blank_by_default(self):
        we = WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=0
        )
        self.assertEqual(we.notes, "")


class WorkoutSetModelTest(TestCase):
    def setUp(self):
        exercise = Exercise.objects.create(name=EX_ALPHA)
        day = WorkoutDay.objects.create(date="2025-01-01")
        self.we = WorkoutExercise.objects.create(
            workout_day=day, exercise=exercise, order=0
        )

    def test_create_set(self):
        s = WorkoutSet.objects.create(
            workout_exercise=self.we, set_number=1, weight=100, reps=10
        )
        self.assertIn("Set 1:", str(s))
        self.assertIn("kg", str(s))
        self.assertEqual(s.weight_unit, "kg")

    def test_set_lbs_unit(self):
        s = WorkoutSet.objects.create(
            workout_exercise=self.we,
            set_number=1,
            weight=225,
            weight_unit="lbs",
            reps=8,
        )
        self.assertIn("Set 1:", str(s))
        self.assertIn("lbs", str(s))

    def test_ordering_by_set_number(self):
        WorkoutSet.objects.create(
            workout_exercise=self.we, set_number=2, weight=100, reps=8
        )
        WorkoutSet.objects.create(
            workout_exercise=self.we, set_number=1, weight=80, reps=10
        )
        sets = list(self.we.sets.all())
        self.assertEqual(sets[0].set_number, 1)
        self.assertEqual(sets[1].set_number, 2)

    def test_cascade_delete_with_workout_exercise(self):
        WorkoutSet.objects.create(
            workout_exercise=self.we, set_number=1, weight=100, reps=10
        )
        self.we.delete()
        self.assertEqual(WorkoutSet.objects.count(), 0)

    def test_decimal_weight(self):
        s = WorkoutSet.objects.create(
            workout_exercise=self.we, set_number=1, weight=67.5, reps=12
        )
        self.assertEqual(float(s.weight), 67.5)

    def test_unit_choices(self):
        s = WorkoutSet.objects.create(
            workout_exercise=self.we, set_number=1, weight=50, reps=10
        )
        self.assertIn(s.weight_unit, ["kg", "lbs"])


class AuthViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")

    def test_login_get(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gym/login.html")

    def test_login_post_valid(self):
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "pass1234"}
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_post_invalid(self):
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gym/login.html")

    def test_login_redirects_authenticated(self):
        self.client.login(username="testuser", password="pass1234")
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_logout(self):
        self.client.login(username="testuser", password="pass1234")
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_redirect_unauthenticated(self):
        protected_urls = [
            reverse("dashboard"),
            reverse("exercise_list"),
            reverse("day_create"),
            reverse("preset_list"),
            reverse("preset_create"),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertRedirects(
                response, f'{reverse("login")}?next={url}'
            )


class ExerciseViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.client.login(username="testuser", password="pass1234")

    def test_exercise_list_get(self):
        response = self.client.get(reverse("exercise_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gym/exercises.html")

    def test_exercise_create_post(self):
        response = self.client.post(
            reverse("exercise_list"), {"name": EX_ALPHA}
        )
        self.assertRedirects(response, reverse("exercise_list"))
        self.assertTrue(Exercise.objects.filter(name=EX_ALPHA).exists())

    def test_exercise_create_duplicate(self):
        Exercise.objects.create(name=EX_ALPHA)
        response = self.client.post(
            reverse("exercise_list"), {"name": EX_ALPHA}
        )
        self.assertRedirects(response, reverse("exercise_list"))
        self.assertEqual(Exercise.objects.filter(name=EX_ALPHA).count(), 1)

    def test_exercise_create_empty_name(self):
        response = self.client.post(reverse("exercise_list"), {"name": ""})
        self.assertRedirects(response, reverse("exercise_list"))

    def test_exercise_create_whitespace_name(self):
        response = self.client.post(reverse("exercise_list"), {"name": "   "})
        self.assertRedirects(response, reverse("exercise_list"))

    def test_exercise_delete(self):
        e = Exercise.objects.create(name=EX_ALPHA)
        response = self.client.post(
            reverse("exercise_delete", args=[e.id])
        )
        self.assertRedirects(response, reverse("exercise_list"))
        self.assertFalse(Exercise.objects.filter(id=e.id).exists())

    def test_exercise_delete_nonexistent(self):
        response = self.client.post(
            reverse("exercise_delete", args=[999])
        )
        self.assertEqual(response.status_code, 404)

    def test_exercises_ordered_in_context(self):
        Exercise.objects.create(name="ZZZ B")
        Exercise.objects.create(name="ZZZ A")
        response = self.client.get(reverse("exercise_list"))
        names = [e.name for e in response.context["exercises"]]
        zzz_names = [n for n in names if n.startswith("ZZZ ")]
        self.assertEqual(zzz_names, sorted(zzz_names))


class DayCreateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.client.login(username="testuser", password="pass1234")
        self.ex1 = Exercise.objects.create(name=EX_ALPHA)

    def test_day_create_get(self):
        response = self.client.get(reverse("day_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gym/day_create.html")
        self.assertEqual(response.context["today"], date.today().isoformat())

    def test_day_create_post_valid(self):
        response = self.client.post(
            reverse("day_create"),
            {"date": "2025-01-01", "exercises": str(self.ex1.id)},
        )
        self.assertEqual(WorkoutDay.objects.count(), 1)
        day = WorkoutDay.objects.first()
        self.assertRedirects(response, reverse("day_detail", args=[day.id]))
        self.assertEqual(day.exercises.count(), 1)

    def test_day_create_post_missing_date(self):
        response = self.client.post(
            reverse("day_create"), {"exercises": str(self.ex1.id)}
        )
        self.assertRedirects(response, reverse("day_create"))
        self.assertEqual(WorkoutDay.objects.count(), 0)

    def test_day_create_post_missing_exercises(self):
        response = self.client.post(reverse("day_create"), {"date": "2025-01-01"})
        self.assertRedirects(response, reverse("day_create"))
        self.assertEqual(WorkoutDay.objects.count(), 0)

    def test_day_create_post_empty_exercises(self):
        response = self.client.post(
            reverse("day_create"), {"date": "2025-01-01", "exercises": ""}
        )
        self.assertRedirects(response, reverse("day_create"))
        self.assertEqual(WorkoutDay.objects.count(), 0)

    def test_day_create_with_preset(self):
        preset = DayPreset.objects.create(name="ZZ Push Day")
        DayPresetExercise.objects.create(
            preset=preset, exercise=self.ex1, order=0
        )
        response = self.client.post(
            reverse("day_create"),
            {
                "date": "2025-01-01",
                "preset": str(preset.id),
                "exercises": str(self.ex1.id),
            },
        )
        day = WorkoutDay.objects.first()
        self.assertEqual(day.preset, preset)
        self.assertRedirects(response, reverse("day_detail", args=[day.id]))

    def test_day_create_multiple_exercises(self):
        ex2 = Exercise.objects.create(name=EX_BETA)
        response = self.client.post(
            reverse("day_create"),
            {
                "date": "2025-01-01",
                "exercises": f"{self.ex1.id},{ex2.id}",
            },
        )
        day = WorkoutDay.objects.first()
        self.assertEqual(day.exercises.count(), 2)

    def test_day_create_preset_exercises_in_context(self):
        preset = DayPreset.objects.create(name="ZZ Push Day")
        preset_ex = DayPresetExercise.objects.create(
            preset=preset, exercise=self.ex1, order=0
        )
        response = self.client.get(reverse("day_create"))
        raw = response.context["preset_exercises"]
        data = json.loads(raw)
        self.assertIn(str(preset.id), data)
        self.assertIn(preset_ex.exercise_id, data[str(preset.id)])


class DayDetailViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.client.login(username="testuser", password="pass1234")
        self.exercise = Exercise.objects.create(name=EX_ALPHA)
        self.day = WorkoutDay.objects.create(date="2025-01-01")

    def test_day_detail_get(self):
        response = self.client.get(reverse("day_detail", args=[self.day.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gym/day_detail.html")

    def test_day_detail_nonexistent(self):
        response = self.client.get(reverse("day_detail", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_day_detail_shows_exercises(self):
        we = WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=0
        )
        response = self.client.get(reverse("day_detail", args=[self.day.id]))
        self.assertContains(response, EX_ALPHA)

    def test_day_detail_shows_sets(self):
        we = WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=0
        )
        WorkoutSet.objects.create(
            workout_exercise=we, set_number=1, weight=100, reps=10
        )
        response = self.client.get(reverse("day_detail", args=[self.day.id]))
        self.assertContains(response, "100")
        self.assertContains(response, "10")


class DayExerciseManageViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.client.login(username="testuser", password="pass1234")
        self.exercise = Exercise.objects.create(name=EX_ALPHA)
        self.day = WorkoutDay.objects.create(date="2025-01-01")

    def test_add_exercise(self):
        response = self.client.post(
            reverse("day_add_exercise", args=[self.day.id]),
            {"exercise_id": self.exercise.id},
        )
        self.assertRedirects(response, reverse("day_detail", args=[self.day.id]))
        self.assertEqual(self.day.exercises.count(), 1)

    def test_add_exercise_increments_order(self):
        WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=0
        )
        e2 = Exercise.objects.create(name=EX_BETA)
        response = self.client.post(
            reverse("day_add_exercise", args=[self.day.id]),
            {"exercise_id": e2.id},
        )
        self.assertRedirects(response, reverse("day_detail", args=[self.day.id]))
        we2 = WorkoutExercise.objects.filter(workout_day=self.day).get(exercise=e2)
        self.assertEqual(we2.order, 1)

    def test_remove_exercise(self):
        we = WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=0
        )
        response = self.client.post(
            reverse("day_remove_exercise", args=[self.day.id, we.id])
        )
        self.assertRedirects(response, reverse("day_detail", args=[self.day.id]))
        self.assertEqual(self.day.exercises.count(), 0)

    def test_remove_exercise_wrong_day(self):
        other_day = WorkoutDay.objects.create(date="2025-01-02")
        we = WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=0
        )
        response = self.client.post(
            reverse("day_remove_exercise", args=[other_day.id, we.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_day(self):
        response = self.client.post(reverse("day_delete", args=[self.day.id]))
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(WorkoutDay.objects.count(), 0)

    def test_delete_day_cascades_exercises(self):
        WorkoutExercise.objects.create(
            workout_day=self.day, exercise=self.exercise, order=0
        )
        self.client.post(reverse("day_delete", args=[self.day.id]))
        self.assertEqual(WorkoutExercise.objects.count(), 0)


class SetViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.client.login(username="testuser", password="pass1234")
        exercise = Exercise.objects.create(name=EX_ALPHA)
        self.day = WorkoutDay.objects.create(date="2025-01-01")
        self.we = WorkoutExercise.objects.create(
            workout_day=self.day, exercise=exercise, order=0
        )

    def test_add_set_valid(self):
        response = self.client.post(
            reverse("set_add", args=[self.we.id]),
            {"weight": "100", "reps": "10", "weight_unit": "kg"},
        )
        self.assertRedirects(response, reverse("day_detail", args=[self.day.id]))
        self.assertEqual(self.we.sets.count(), 1)
        s = self.we.sets.first()
        self.assertEqual(s.set_number, 1)

    def test_add_set_increments_number(self):
        WorkoutSet.objects.create(
            workout_exercise=self.we, set_number=1, weight=100, reps=10
        )
        self.client.post(
            reverse("set_add", args=[self.we.id]),
            {"weight": "110", "reps": "8", "weight_unit": "kg"},
        )
        self.assertEqual(self.we.sets.count(), 2)
        s = self.we.sets.last()
        self.assertEqual(s.set_number, 2)

    def test_add_set_missing_weight(self):
        response = self.client.post(
            reverse("set_add", args=[self.we.id]),
            {"reps": "10", "weight_unit": "kg"},
        )
        self.assertRedirects(response, reverse("day_detail", args=[self.day.id]))
        self.assertEqual(self.we.sets.count(), 0)

    def test_add_set_missing_reps(self):
        response = self.client.post(
            reverse("set_add", args=[self.we.id]),
            {"weight": "100", "weight_unit": "kg"},
        )
        self.assertRedirects(response, reverse("day_detail", args=[self.day.id]))
        self.assertEqual(self.we.sets.count(), 0)

    def test_add_set_default_unit_is_kg(self):
        self.client.post(
            reverse("set_add", args=[self.we.id]),
            {"weight": "100", "reps": "10"},
        )
        s = self.we.sets.first()
        self.assertEqual(s.weight_unit, "kg")

    def test_add_set_lbs(self):
        self.client.post(
            reverse("set_add", args=[self.we.id]),
            {"weight": "225", "reps": "8", "weight_unit": "lbs"},
        )
        s = self.we.sets.first()
        self.assertEqual(s.weight_unit, "lbs")

    def test_delete_set(self):
        s = WorkoutSet.objects.create(
            workout_exercise=self.we, set_number=1, weight=100, reps=10
        )
        response = self.client.post(reverse("set_delete", args=[s.id]))
        self.assertRedirects(response, reverse("day_detail", args=[self.day.id]))
        self.assertEqual(self.we.sets.count(), 0)

    def test_delete_set_nonexistent(self):
        response = self.client.post(reverse("set_delete", args=[999]))
        self.assertEqual(response.status_code, 404)


class DashboardViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.client.login(username="testuser", password="pass1234")

    def test_dashboard_empty(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gym/dashboard.html")
        self.assertContains(response, "No workouts logged yet")

    def test_dashboard_shows_days(self):
        WorkoutDay.objects.create(date="2025-01-01")
        WorkoutDay.objects.create(date="2025-01-02")
        response = self.client.get(reverse("dashboard"))
        days = response.context["days"]
        self.assertEqual(len(days), 2)

    def test_dashboard_limited_to_20(self):
        for i in range(25):
            WorkoutDay.objects.create(date=f"2025-01-{i+1:02d}")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(len(response.context["days"]), 20)


class PresetViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.client.login(username="testuser", password="pass1234")
        self.ex1 = Exercise.objects.create(name=EX_ALPHA)
        self.ex2 = Exercise.objects.create(name=EX_BETA)

    def test_preset_list_get(self):
        response = self.client.get(reverse("preset_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gym/presets.html")

    def test_preset_list_empty(self):
        response = self.client.get(reverse("preset_list"))
        self.assertContains(response, "No presets yet")

    def test_preset_create_get(self):
        response = self.client.get(reverse("preset_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gym/preset_form.html")

    def test_preset_create_post_valid(self):
        response = self.client.post(
            reverse("preset_create"),
            {"name": "ZZ Push Day", "exercises": str(self.ex1.id)},
        )
        preset = DayPreset.objects.first()
        self.assertRedirects(response, reverse("preset_detail", args=[preset.id]))
        self.assertEqual(preset.exercises.count(), 1)

    def test_preset_create_multiple_exercises(self):
        response = self.client.post(
            reverse("preset_create"),
            {"name": "ZZ Full Body", "exercises": f"{self.ex1.id},{self.ex2.id}"},
        )
        preset = DayPreset.objects.first()
        self.assertEqual(preset.exercises.count(), 2)

    def test_preset_create_missing_name(self):
        response = self.client.post(
            reverse("preset_create"),
            {"name": "", "exercises": str(self.ex1.id)},
        )
        self.assertRedirects(response, reverse("preset_create"))
        self.assertEqual(DayPreset.objects.count(), 0)

    def test_preset_create_missing_exercises(self):
        response = self.client.post(
            reverse("preset_create"), {"name": "ZZ Push Day"}
        )
        self.assertRedirects(response, reverse("preset_create"))
        self.assertEqual(DayPreset.objects.count(), 0)

    def test_preset_create_empty_exercises(self):
        response = self.client.post(
            reverse("preset_create"),
            {"name": "ZZ Push Day", "exercises": ""},
        )
        self.assertRedirects(response, reverse("preset_create"))
        self.assertEqual(DayPreset.objects.count(), 0)

    def test_preset_detail(self):
        preset = DayPreset.objects.create(name="ZZ Push Day")
        DayPresetExercise.objects.create(
            preset=preset, exercise=self.ex1, order=0
        )
        response = self.client.get(reverse("preset_detail", args=[preset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gym/preset_detail.html")
        self.assertContains(response, EX_ALPHA)

    def test_preset_detail_nonexistent(self):
        response = self.client.get(reverse("preset_detail", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_preset_edit_get(self):
        preset = DayPreset.objects.create(name="ZZ Push Day")
        DayPresetExercise.objects.create(
            preset=preset, exercise=self.ex1, order=0
        )
        response = self.client.get(reverse("preset_edit", args=[preset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["selected"]), [self.ex1.id])

    def test_preset_edit_post(self):
        preset = DayPreset.objects.create(name="ZZ Push Day")
        DayPresetExercise.objects.create(
            preset=preset, exercise=self.ex1, order=0
        )
        response = self.client.post(
            reverse("preset_edit", args=[preset.id]),
            {"name": "ZZ Pull Day", "exercises": str(self.ex2.id)},
        )
        self.assertRedirects(response, reverse("preset_detail", args=[preset.id]))
        preset.refresh_from_db()
        self.assertEqual(preset.name, "ZZ Pull Day")
        self.assertEqual(preset.exercises.count(), 1)
        self.assertEqual(
            preset.exercises.first().exercise_id, self.ex2.id
        )

    def test_preset_edit_missing_fields(self):
        preset = DayPreset.objects.create(name="ZZ Push Day")
        response = self.client.post(
            reverse("preset_edit", args=[preset.id]),
            {"name": "", "exercises": ""},
        )
        self.assertRedirects(response, reverse("preset_edit", args=[preset.id]))
        preset.refresh_from_db()
        self.assertEqual(preset.name, "ZZ Push Day")

    def test_preset_delete(self):
        preset = DayPreset.objects.create(name="ZZ Push Day")
        response = self.client.post(reverse("preset_delete", args=[preset.id]))
        self.assertRedirects(response, reverse("preset_list"))
        self.assertEqual(DayPreset.objects.count(), 0)

    def test_preset_delete_nonexistent(self):
        response = self.client.post(reverse("preset_delete", args=[999]))
        self.assertEqual(response.status_code, 404)


class IntegrationTest(TestCase):
    def test_full_workflow(self):
        user = User.objects.create_user(username="testuser", password="pass1234")
        self.client.login(username="testuser", password="pass1234")

        # Create exercises (use names not in seed data)
        self.client.post(reverse("exercise_list"), {"name": EX_ALPHA})
        self.client.post(reverse("exercise_list"), {"name": EX_BETA})
        self.client.post(reverse("exercise_list"), {"name": EX_GAMMA})
        self.assertEqual(Exercise.objects.count(), 36 + 3)

        # Create preset
        bp = Exercise.objects.get(name=EX_ALPHA)
        sq = Exercise.objects.get(name=EX_BETA)
        self.client.post(
            reverse("preset_create"),
            {"name": "ZZ Power Day", "exercises": f"{bp.id},{sq.id}"},
        )
        preset = DayPreset.objects.get(name="ZZ Power Day")
        self.assertEqual(preset.exercises.count(), 2)

        # Log a workout day with the preset
        dl = Exercise.objects.get(name=EX_GAMMA)
        self.client.post(
            reverse("day_create"),
            {
                "date": "2025-06-15",
                "preset": str(preset.id),
                "notes": "Great session",
                "exercises": f"{bp.id},{sq.id},{dl.id}",
            },
        )
        day = WorkoutDay.objects.first()
        self.assertIsNotNone(day)
        self.assertEqual(day.preset, preset)
        self.assertEqual(day.notes, "Great session")
        self.assertEqual(day.exercises.count(), 3)

        # Add sets to first exercise
        we = day.exercises.first()
        self.client.post(
            reverse("set_add", args=[we.id]),
            {"weight": "100", "reps": "10", "weight_unit": "kg"},
        )
        self.client.post(
            reverse("set_add", args=[we.id]),
            {"weight": "110", "reps": "8", "weight_unit": "kg"},
        )
        self.assertEqual(we.sets.count(), 2)

        # Verify on detail page
        response = self.client.get(reverse("day_detail", args=[day.id]))
        self.assertContains(response, EX_ALPHA)
        self.assertContains(response, EX_BETA)
        self.assertContains(response, EX_GAMMA)
        self.assertContains(response, "100")
        self.assertContains(response, "110")

        # Dashboard shows the day
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Jun 15, 2025")

        # Delete a set
        s = we.sets.first()
        self.client.post(reverse("set_delete", args=[s.id]))
        self.assertEqual(we.sets.count(), 1)

        # Remove an exercise
        self.client.post(
            reverse("day_remove_exercise", args=[day.id, we.id])
        )
        self.assertEqual(day.exercises.count(), 2)

    def test_unauthenticated_access(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response, f'{reverse("login")}?next={reverse("dashboard")}'
        )

    def test_login_then_logout_flow(self):
        User.objects.create_user(username="testuser", password="pass1234")
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "pass1234"}
        )
        self.assertRedirects(response, reverse("dashboard"))
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response, f'{reverse("login")}?next={reverse("dashboard")}'
        )
