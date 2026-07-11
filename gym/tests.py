import json
from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    ChatMessage,
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


# --- Model tests ---

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
        self.alice = User.objects.create_user("alice", password="pw")
        self.bob = User.objects.create_user("bob", password="pw")

    def test_name_unique_per_user(self):
        DayPreset.objects.create(user=self.alice, name="Push")
        with self.assertRaises(IntegrityError):
            DayPreset.objects.create(user=self.alice, name="Push")

    def test_same_name_across_users_allowed(self):
        DayPreset.objects.create(user=self.alice, name="Push")
        DayPreset.objects.create(user=self.bob, name="Push")
        self.assertEqual(DayPreset.objects.filter(name="Push").count(), 2)


class WorkoutDayModelTest(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw")

    def test_ordering_newest_first(self):
        WorkoutDay.objects.create(user=self.alice, date=date(2026, 1, 1))
        WorkoutDay.objects.create(user=self.alice, date=date(2026, 1, 10))
        days = list(WorkoutDay.objects.filter(user=self.alice))
        self.assertEqual(days[0].date, date(2026, 1, 10))

    def test_preset_delete_sets_null(self):
        preset = DayPreset.objects.create(user=self.alice, name="Push")
        day = WorkoutDay.objects.create(user=self.alice, date=date(2026, 1, 1), preset=preset)
        preset.delete()
        day.refresh_from_db()
        self.assertIsNone(day.preset)

    def test_cascade_delete_removes_children(self):
        ex = Exercise.objects.create(name=EX_ALPHA)
        day = WorkoutDay.objects.create(user=self.alice, date=date(2026, 1, 1))
        we = WorkoutExercise.objects.create(workout_day=day, exercise=ex, order=0)
        WorkoutSet.objects.create(workout_exercise=we, set_number=1, reps=5, weight=100)
        day.delete()
        self.assertEqual(WorkoutExercise.objects.filter(id=we.id).count(), 0)
        self.assertEqual(WorkoutSet.objects.count(), 0)


class WorkoutSetModelTest(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw")
        ex = Exercise.objects.create(name=EX_ALPHA)
        day = WorkoutDay.objects.create(user=self.alice, date=date(2026, 1, 1))
        self.we = WorkoutExercise.objects.create(workout_day=day, exercise=ex, order=0)

    def test_str_and_ordering(self):
        WorkoutSet.objects.create(workout_exercise=self.we, set_number=2, reps=8, weight=50)
        WorkoutSet.objects.create(workout_exercise=self.we, set_number=1, reps=10, weight=45)
        sets = list(self.we.sets.all())
        self.assertEqual(sets[0].set_number, 1)
        self.assertIn("kg", str(sets[0]))


# --- API test base ---

class ApiTestCase(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw12345")
        self.bob = User.objects.create_user("bob", password="pw12345")
        self.ex = Exercise.objects.create(name=EX_ALPHA, body_part="chest")
        self.ex2 = Exercise.objects.create(name=EX_BETA, body_part="back")

    def login_as(self, user):
        self.client.force_login(user)

    def post_json(self, url, data):
        return self.client.post(url, data=json.dumps(data), content_type="application/json")

    def put_json(self, url, data):
        return self.client.put(url, data=json.dumps(data), content_type="application/json")

    def make_day(self, user, day_date=None, notes=""):
        return WorkoutDay.objects.create(user=user, date=day_date or date(2026, 1, 1), notes=notes)

    def make_preset(self, user, name="Push"):
        return DayPreset.objects.create(user=user, name=name)


# --- Auth ---

class AuthApiTests(ApiTestCase):
    def test_login_valid(self):
        res = self.post_json(reverse("api_login"), {"username": "alice", "password": "pw12345"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["username"], "alice")

    def test_login_invalid(self):
        res = self.post_json(reverse("api_login"), {"username": "alice", "password": "wrong"})
        self.assertEqual(res.status_code, 401)

    def test_logout(self):
        self.login_as(self.alice)
        res = self.client.post(reverse("api_logout"))
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("api_me"))
        self.assertEqual(res.status_code, 403)

    def test_me_unauthenticated(self):
        res = self.client.get(reverse("api_me"))
        self.assertEqual(res.status_code, 403)

    def test_me_authenticated(self):
        self.login_as(self.alice)
        res = self.client.get(reverse("api_me"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["username"], "alice")


class AuthGatingTests(ApiTestCase):
    def test_protected_endpoints_require_login(self):
        day = self.make_day(self.alice)
        we = WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        s = WorkoutSet.objects.create(workout_exercise=we, set_number=1, reps=5, weight=100)
        preset = self.make_preset(self.alice)

        endpoints = [
            ("get", reverse("api_exercise_list")),
            ("get", reverse("api_day_list_create")),
            ("get", reverse("api_day_detail", args=[day.id])),
            ("post", reverse("api_day_add_exercise", args=[day.id])),
            ("delete", reverse("api_day_remove_exercise", args=[day.id, we.id])),
            ("post", reverse("api_set_add", args=[we.id])),
            ("delete", reverse("api_set_delete", args=[s.id])),
            ("get", reverse("api_preset_list_create")),
            ("get", reverse("api_preset_detail", args=[preset.id])),
            ("get", reverse("api_leaderboard")),
            ("get", reverse("api_leaderboard_exercise", args=[self.ex.id])),
            ("get", reverse("api_chat")),
            ("post", reverse("api_coach")),
        ]
        for method, url in endpoints:
            res = getattr(self.client, method)(url)
            self.assertEqual(res.status_code, 403, f"{method.upper()} {url} should require auth")


# --- Exercises ---

class ExerciseApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)

    def test_list_includes_seed_and_custom(self):
        res = self.client.get(reverse("api_exercise_list"))
        names = [e["name"] for e in res.json()]
        self.assertIn(EX_ALPHA, names)
        self.assertIn("Bench Press", names)

    def test_search_filter(self):
        res = self.client.get(reverse("api_exercise_list"), {"search": "ZZ Test Alpha"})
        names = [e["name"] for e in res.json()]
        self.assertEqual(names, [EX_ALPHA])

    def test_body_part_filter(self):
        res = self.client.get(reverse("api_exercise_list"), {"body_part": "back"})
        names = [e["name"] for e in res.json()]
        self.assertIn(EX_BETA, names)
        self.assertNotIn(EX_ALPHA, names)

    def test_create_exercise(self):
        res = self.post_json(reverse("api_exercise_list"), {"name": EX_GAMMA, "body_part": "legs"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Exercise.objects.filter(name=EX_GAMMA).exists())

    def test_create_duplicate_is_idempotent(self):
        self.post_json(reverse("api_exercise_list"), {"name": EX_GAMMA})
        self.post_json(reverse("api_exercise_list"), {"name": EX_GAMMA})
        self.assertEqual(Exercise.objects.filter(name=EX_GAMMA).count(), 1)

    def test_delete_exercise(self):
        ex = Exercise.objects.create(name=EX_GAMMA)
        res = self.client.delete(reverse("api_exercise_delete", args=[ex.id]))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Exercise.objects.filter(id=ex.id).exists())

    def test_delete_exercise_used_in_workout_is_blocked(self):
        ex = Exercise.objects.create(name=EX_GAMMA)
        day = self.make_day(self.alice)
        WorkoutExercise.objects.create(workout_day=day, exercise=ex, order=0)
        res = self.client.delete(reverse("api_exercise_delete", args=[ex.id]))
        self.assertEqual(res.status_code, 400)
        self.assertTrue(Exercise.objects.filter(id=ex.id).exists())

    def test_delete_exercise_used_in_workout_by_other_user_is_blocked(self):
        # Deletion must be blocked even if the logging user isn't the requester —
        # the exercise catalog is shared, so any friend's history can be affected.
        ex = Exercise.objects.create(name=EX_GAMMA)
        day = self.make_day(self.bob)
        WorkoutExercise.objects.create(workout_day=day, exercise=ex, order=0)
        res = self.client.delete(reverse("api_exercise_delete", args=[ex.id]))
        self.assertEqual(res.status_code, 400)
        self.assertTrue(Exercise.objects.filter(id=ex.id).exists())

    def test_delete_exercise_used_in_preset_is_blocked(self):
        ex = Exercise.objects.create(name=EX_GAMMA)
        preset = self.make_preset(self.alice)
        DayPresetExercise.objects.create(preset=preset, exercise=ex, order=0)
        res = self.client.delete(reverse("api_exercise_delete", args=[ex.id]))
        self.assertEqual(res.status_code, 400)
        self.assertTrue(Exercise.objects.filter(id=ex.id).exists())


# --- Workout days ---

class WorkoutDayApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)

    def test_create_day_with_exercises(self):
        res = self.post_json(
            reverse("api_day_list_create"),
            {"date": "2026-01-05", "exercises": f"{self.ex.id},{self.ex2.id}", "notes": "Good session"},
        )
        self.assertEqual(res.status_code, 200)
        day = WorkoutDay.objects.get(id=res.json()["id"])
        self.assertEqual(day.user, self.alice)
        self.assertEqual(day.exercises.count(), 2)
        self.assertEqual(list(day.exercises.order_by("order")), list(day.exercises.all()))

    def test_create_day_missing_fields(self):
        res = self.post_json(reverse("api_day_list_create"), {"date": "", "exercises": ""})
        self.assertEqual(res.status_code, 400)

    def test_list_scoped_and_capped_at_20(self):
        for i in range(25):
            self.make_day(self.alice, day_date=date(2026, 1, 1) + timedelta(days=i))
        res = self.client.get(reverse("api_day_list_create"))
        self.assertEqual(len(res.json()), 20)

    def test_day_detail_shape(self):
        day = self.make_day(self.alice)
        we = WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=we, set_number=1, reps=10, weight=50)
        res = self.client.get(reverse("api_day_detail", args=[day.id]))
        data = res.json()
        self.assertEqual(len(data["exercises"]), 1)
        self.assertEqual(len(data["exercises"][0]["sets"]), 1)

    def test_delete_day_cascades(self):
        day = self.make_day(self.alice)
        we = WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        res = self.client.delete(reverse("api_day_detail", args=[day.id]))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(WorkoutExercise.objects.filter(id=we.id).exists())

    def test_add_exercise_appends_next_order(self):
        day = self.make_day(self.alice)
        WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        res = self.post_json(
            reverse("api_day_add_exercise", args=[day.id]), {"exercise_id": self.ex2.id}
        )
        self.assertEqual(res.status_code, 200)
        new_we = day.exercises.get(exercise=self.ex2)
        self.assertEqual(new_we.order, 1)

    def test_remove_exercise(self):
        day = self.make_day(self.alice)
        we = WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        res = self.client.delete(reverse("api_day_remove_exercise", args=[day.id, we.id]))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(WorkoutExercise.objects.filter(id=we.id).exists())

    def test_set_add_increments_set_number(self):
        day = self.make_day(self.alice)
        we = WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        self.post_json(reverse("api_set_add", args=[we.id]), {"weight": 50, "reps": 10})
        res = self.post_json(reverse("api_set_add", args=[we.id]), {"weight": 55, "reps": 8})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(we.sets.count(), 2)
        self.assertEqual(list(we.sets.values_list("set_number", flat=True)), [1, 2])

    def test_set_delete(self):
        day = self.make_day(self.alice)
        we = WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        s = WorkoutSet.objects.create(workout_exercise=we, set_number=1, reps=5, weight=100)
        res = self.client.delete(reverse("api_set_delete", args=[s.id]))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(WorkoutSet.objects.filter(id=s.id).exists())


# --- Cross-user isolation (security-critical) ---

class UserScopingTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.alice_day = self.make_day(self.alice, notes="alice's day")
        self.alice_we = WorkoutExercise.objects.create(
            workout_day=self.alice_day, exercise=self.ex, order=0
        )
        self.alice_set = WorkoutSet.objects.create(
            workout_exercise=self.alice_we, set_number=1, reps=5, weight=100
        )
        self.alice_preset = self.make_preset(self.alice, name="Alice Push")
        self.login_as(self.bob)

    def test_cannot_view_foreign_day(self):
        res = self.client.get(reverse("api_day_detail", args=[self.alice_day.id]))
        self.assertEqual(res.status_code, 404)

    def test_cannot_delete_foreign_day(self):
        res = self.client.delete(reverse("api_day_detail", args=[self.alice_day.id]))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(WorkoutDay.objects.filter(id=self.alice_day.id).exists())

    def test_cannot_add_exercise_to_foreign_day(self):
        res = self.post_json(
            reverse("api_day_add_exercise", args=[self.alice_day.id]), {"exercise_id": self.ex2.id}
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(self.alice_day.exercises.count(), 1)

    def test_cannot_remove_foreign_exercise(self):
        res = self.client.delete(
            reverse("api_day_remove_exercise", args=[self.alice_day.id, self.alice_we.id])
        )
        self.assertEqual(res.status_code, 404)
        self.assertTrue(WorkoutExercise.objects.filter(id=self.alice_we.id).exists())

    def test_cannot_add_set_to_foreign_exercise(self):
        res = self.post_json(
            reverse("api_set_add", args=[self.alice_we.id]), {"weight": 999, "reps": 1}
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(self.alice_we.sets.count(), 1)

    def test_cannot_delete_foreign_set(self):
        res = self.client.delete(reverse("api_set_delete", args=[self.alice_set.id]))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(WorkoutSet.objects.filter(id=self.alice_set.id).exists())

    def test_cannot_view_foreign_preset(self):
        res = self.client.get(reverse("api_preset_detail", args=[self.alice_preset.id]))
        self.assertEqual(res.status_code, 404)

    def test_cannot_update_foreign_preset(self):
        res = self.put_json(
            reverse("api_preset_detail", args=[self.alice_preset.id]),
            {"name": "Hijacked", "exercises": str(self.ex.id)},
        )
        self.assertEqual(res.status_code, 404)
        self.alice_preset.refresh_from_db()
        self.assertEqual(self.alice_preset.name, "Alice Push")

    def test_cannot_delete_foreign_preset(self):
        res = self.client.delete(reverse("api_preset_detail", args=[self.alice_preset.id]))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(DayPreset.objects.filter(id=self.alice_preset.id).exists())

    def test_cannot_quick_log_foreign_preset(self):
        res = self.post_json(
            reverse("api_preset_quick_log", args=[self.alice_preset.id]), {"date": "2026-02-01"}
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(WorkoutDay.objects.filter(preset=self.alice_preset).count(), 0)

    def test_day_list_excludes_foreign_days(self):
        self.make_day(self.bob, notes="bob's day")
        res = self.client.get(reverse("api_day_list_create"))
        notes = [d["notes"] for d in res.json()]
        self.assertNotIn("alice's day", notes)

    def test_preset_list_excludes_foreign_presets(self):
        self.make_preset(self.bob, name="Bob Pull")
        res = self.client.get(reverse("api_preset_list_create"))
        names = [p["name"] for p in res.json()]
        self.assertNotIn("Alice Push", names)
        self.assertIn("Bob Pull", names)

    def test_foreign_preset_id_on_day_create_is_ignored(self):
        res = self.post_json(
            reverse("api_day_list_create"),
            {"date": "2026-01-05", "exercises": str(self.ex.id), "preset": self.alice_preset.id},
        )
        self.assertEqual(res.status_code, 200)
        day = WorkoutDay.objects.get(id=res.json()["id"])
        self.assertIsNone(day.preset)


# --- Presets ---

class PresetApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)

    def test_create_preset(self):
        res = self.post_json(
            reverse("api_preset_list_create"),
            {"name": "Push", "exercises": f"{self.ex.id},{self.ex2.id}"},
        )
        self.assertEqual(res.status_code, 200)
        preset = DayPreset.objects.get(id=res.json()["id"])
        self.assertEqual(preset.user, self.alice)
        self.assertEqual(preset.exercises.count(), 2)

    def test_duplicate_name_same_user_rejected(self):
        self.make_preset(self.alice, name="Push")
        res = self.post_json(
            reverse("api_preset_list_create"), {"name": "Push", "exercises": str(self.ex.id)}
        )
        self.assertEqual(res.status_code, 400)

    def test_same_name_different_users_allowed(self):
        self.make_preset(self.bob, name="Push")
        res = self.post_json(
            reverse("api_preset_list_create"), {"name": "Push", "exercises": str(self.ex.id)}
        )
        self.assertEqual(res.status_code, 200)

    def test_update_preset(self):
        preset = self.make_preset(self.alice, name="Push")
        res = self.put_json(
            reverse("api_preset_detail", args=[preset.id]),
            {"name": "Push v2", "exercises": f"{self.ex.id},{self.ex2.id}"},
        )
        self.assertEqual(res.status_code, 200)
        preset.refresh_from_db()
        self.assertEqual(preset.name, "Push v2")
        self.assertEqual(preset.exercises.count(), 2)

    def test_update_to_own_other_existing_name_rejected(self):
        self.make_preset(self.alice, name="Pull")
        preset = self.make_preset(self.alice, name="Push")
        res = self.put_json(
            reverse("api_preset_detail", args=[preset.id]),
            {"name": "Pull", "exercises": str(self.ex.id)},
        )
        self.assertEqual(res.status_code, 400)

    def test_update_keeping_own_name_succeeds(self):
        preset = self.make_preset(self.alice, name="Push")
        res = self.put_json(
            reverse("api_preset_detail", args=[preset.id]),
            {"name": "Push", "exercises": str(self.ex.id)},
        )
        self.assertEqual(res.status_code, 200)

    def test_delete_preset(self):
        preset = self.make_preset(self.alice, name="Push")
        res = self.client.delete(reverse("api_preset_detail", args=[preset.id]))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(DayPreset.objects.filter(id=preset.id).exists())


class PresetQuickLogApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)

    def test_quick_log_creates_day_with_no_history(self):
        preset = self.make_preset(self.alice, name="Push")
        DayPresetExercise.objects.create(preset=preset, exercise=self.ex, order=0)
        DayPresetExercise.objects.create(preset=preset, exercise=self.ex2, order=1)
        res = self.post_json(
            reverse("api_preset_quick_log", args=[preset.id]), {"date": "2026-02-01"}
        )
        self.assertEqual(res.status_code, 200)
        day = WorkoutDay.objects.get(id=res.json()["id"])
        self.assertEqual(day.user, self.alice)
        self.assertEqual(day.preset, preset)
        self.assertEqual(
            list(day.exercises.order_by("order").values_list("exercise_id", flat=True)),
            [self.ex.id, self.ex2.id],
        )
        for we in day.exercises.all():
            self.assertEqual(we.sets.count(), 0)

    def test_quick_log_copies_forward_last_sets(self):
        preset = self.make_preset(self.alice, name="Push")
        DayPresetExercise.objects.create(preset=preset, exercise=self.ex, order=0)
        old_day = self.make_day(self.alice, day_date=date(2026, 1, 1))
        old_we = WorkoutExercise.objects.create(workout_day=old_day, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=old_we, set_number=1, reps=8, weight=60)
        WorkoutSet.objects.create(workout_exercise=old_we, set_number=2, reps=6, weight=65)

        res = self.post_json(
            reverse("api_preset_quick_log", args=[preset.id]), {"date": "2026-02-01"}
        )
        self.assertEqual(res.status_code, 200)
        day = WorkoutDay.objects.get(id=res.json()["id"])
        sets = list(day.exercises.get(exercise=self.ex).sets.order_by("set_number"))
        self.assertEqual(len(sets), 2)
        self.assertEqual(sets[0].reps, 8)
        self.assertEqual(float(sets[0].weight), 60.0)
        self.assertEqual(sets[1].reps, 6)

    def test_quick_log_uses_most_recent_occurrence(self):
        preset = self.make_preset(self.alice, name="Push")
        DayPresetExercise.objects.create(preset=preset, exercise=self.ex, order=0)
        day1 = self.make_day(self.alice, day_date=date(2026, 1, 1))
        we1 = WorkoutExercise.objects.create(workout_day=day1, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=we1, set_number=1, reps=10, weight=40)
        day2 = self.make_day(self.alice, day_date=date(2026, 1, 15))
        we2 = WorkoutExercise.objects.create(workout_day=day2, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=we2, set_number=1, reps=5, weight=80)

        res = self.post_json(
            reverse("api_preset_quick_log", args=[preset.id]), {"date": "2026-02-01"}
        )
        day = WorkoutDay.objects.get(id=res.json()["id"])
        we = day.exercises.get(exercise=self.ex)
        self.assertEqual(we.sets.count(), 1)
        self.assertEqual(float(we.sets.first().weight), 80.0)

    def test_quick_log_skips_empty_prior_occurrence(self):
        preset = self.make_preset(self.alice, name="Push")
        DayPresetExercise.objects.create(preset=preset, exercise=self.ex, order=0)
        # Exercise was added to an earlier day but no sets were ever logged for it.
        empty_day = self.make_day(self.alice, day_date=date(2026, 1, 10))
        WorkoutExercise.objects.create(workout_day=empty_day, exercise=self.ex, order=0)
        real_day = self.make_day(self.alice, day_date=date(2026, 1, 1))
        real_we = WorkoutExercise.objects.create(workout_day=real_day, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=real_we, set_number=1, reps=12, weight=30)

        res = self.post_json(
            reverse("api_preset_quick_log", args=[preset.id]), {"date": "2026-02-01"}
        )
        day = WorkoutDay.objects.get(id=res.json()["id"])
        we = day.exercises.get(exercise=self.ex)
        self.assertEqual(we.sets.count(), 1)
        self.assertEqual(we.sets.first().reps, 12)

    def test_quick_log_empty_preset_rejected(self):
        preset = self.make_preset(self.alice, name="Empty")
        res = self.post_json(
            reverse("api_preset_quick_log", args=[preset.id]), {"date": "2026-02-01"}
        )
        self.assertEqual(res.status_code, 400)

    def test_quick_log_defaults_to_today(self):
        preset = self.make_preset(self.alice, name="Push")
        DayPresetExercise.objects.create(preset=preset, exercise=self.ex, order=0)
        res = self.post_json(reverse("api_preset_quick_log", args=[preset.id]), {})
        self.assertEqual(res.status_code, 200)
        day = WorkoutDay.objects.get(id=res.json()["id"])
        self.assertEqual(day.date, date.today())


# --- Leaderboard ---

class LeaderboardApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.week_start = self.today - timedelta(days=self.today.weekday())
        self.month_start = self.today.replace(day=1)
        self.login_as(self.alice)

    def test_ordering_and_counts(self):
        self.make_day(self.alice, day_date=self.today)
        self.make_day(self.alice, day_date=self.week_start)
        # only count a "last month" day if it actually falls outside the current week
        if self.month_start < self.week_start:
            self.make_day(self.alice, day_date=self.month_start)

        res = self.client.get(reverse("api_leaderboard"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        entries = {e["username"]: e for e in data["entries"]}

        self.assertEqual(entries["alice"]["week_count"], 2)
        expected_month = 3 if self.month_start < self.week_start else 2
        self.assertEqual(entries["alice"]["month_count"], expected_month)
        self.assertIn("bob", entries)
        self.assertEqual(entries["bob"]["week_count"], 0)
        self.assertEqual(data["entries"][0]["username"], "alice")

    def test_superuser_excluded(self):
        User.objects.create_superuser("admin", "admin@example.com", "pw12345")
        res = self.client.get(reverse("api_leaderboard"))
        usernames = [e["username"] for e in res.json()["entries"]]
        self.assertNotIn("admin", usernames)

    def test_week_volume_normalizes_units(self):
        day = self.make_day(self.alice, day_date=self.today)
        we = WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=we, set_number=1, reps=10, weight=50, weight_unit="kg")
        WorkoutSet.objects.create(workout_exercise=we, set_number=2, reps=5, weight=100, weight_unit="lbs")

        res = self.client.get(reverse("api_leaderboard"))
        entries = {e["username"]: e for e in res.json()["entries"]}
        # 50kg*10 + (100lbs->45.3592kg)*5 = 500 + 226.796 = 726.8 (rounded)
        self.assertAlmostEqual(entries["alice"]["week_volume_kg"], 726.8, places=1)
        self.assertEqual(entries["bob"]["week_volume_kg"], 0)

    def test_volume_excludes_sets_outside_this_week(self):
        day = self.make_day(self.alice, day_date=self.week_start - timedelta(days=1))
        we = WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=we, set_number=1, reps=10, weight=999, weight_unit="kg")

        res = self.client.get(reverse("api_leaderboard"))
        entries = {e["username"]: e for e in res.json()["entries"]}
        self.assertEqual(entries["alice"]["week_volume_kg"], 0)

    def test_streak_counts_consecutive_weeks_and_stops_at_gap(self):
        for weeks_ago in (0, 1, 2):
            self.make_day(self.alice, day_date=self.week_start - timedelta(weeks=weeks_ago))
        # gap at weeks_ago=3, then an older, non-contiguous workout
        self.make_day(self.alice, day_date=self.week_start - timedelta(weeks=4))

        res = self.client.get(reverse("api_leaderboard"))
        entries = {e["username"]: e for e in res.json()["entries"]}
        self.assertEqual(entries["alice"]["streak_weeks"], 3)
        self.assertEqual(entries["bob"]["streak_weeks"], 0)

    def test_big_lift_prs_picks_best_e1rm(self):
        bench = Exercise.objects.get(name="Bench Press")
        day = self.make_day(self.alice, day_date=self.today)
        we = WorkoutExercise.objects.create(workout_day=day, exercise=bench, order=0)
        WorkoutSet.objects.create(workout_exercise=we, set_number=1, reps=10, weight=80, weight_unit="kg")
        WorkoutSet.objects.create(workout_exercise=we, set_number=2, reps=5, weight=100, weight_unit="kg")

        res = self.client.get(reverse("api_leaderboard"))
        entries = {e["username"]: e for e in res.json()["entries"]}
        pr = entries["alice"]["prs"]["Bench Press"]
        # 100kg x5 -> e1rm 116.7 beats 80kg x10 -> e1rm 106.7
        self.assertEqual(pr["weight_kg"], 100.0)
        self.assertEqual(pr["reps"], 5)
        self.assertAlmostEqual(pr["e1rm"], 116.7, places=1)
        self.assertEqual(entries["bob"]["prs"], {})

    def test_big_lifts_list_in_response(self):
        res = self.client.get(reverse("api_leaderboard"))
        self.assertEqual(
            res.json()["big_lifts"],
            ["Bench Press", "Squat", "Deadlift", "Overhead Press"],
        )


class LeaderboardExerciseApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)

    def test_ranks_users_by_best_e1rm(self):
        alice_day = self.make_day(self.alice)
        alice_we = WorkoutExercise.objects.create(workout_day=alice_day, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=alice_we, set_number=1, reps=5, weight=100, weight_unit="kg")

        bob_day = self.make_day(self.bob)
        bob_we = WorkoutExercise.objects.create(workout_day=bob_day, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=bob_we, set_number=1, reps=8, weight=120, weight_unit="kg")

        res = self.client.get(reverse("api_leaderboard_exercise", args=[self.ex.id]))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["exercise"], {"id": self.ex.id, "name": EX_ALPHA})
        # bob: 120kg x8 -> e1rm 152.0 beats alice: 100kg x5 -> e1rm 116.7
        self.assertEqual([e["username"] for e in data["entries"]], ["bob", "alice"])
        self.assertAlmostEqual(data["entries"][0]["e1rm"], 152.0, places=1)

    def test_picks_best_set_not_most_recent(self):
        day = self.make_day(self.alice)
        we = WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)
        WorkoutSet.objects.create(workout_exercise=we, set_number=1, reps=5, weight=100, weight_unit="kg")
        WorkoutSet.objects.create(workout_exercise=we, set_number=2, reps=3, weight=60, weight_unit="kg")

        res = self.client.get(reverse("api_leaderboard_exercise", args=[self.ex.id]))
        entries = res.json()["entries"]
        self.assertEqual(entries[0]["weight_kg"], 100.0)

    def test_excludes_users_who_havent_logged_it(self):
        self.make_day(self.alice)  # no exercise logged
        res = self.client.get(reverse("api_leaderboard_exercise", args=[self.ex.id]))
        self.assertEqual(res.json()["entries"], [])

    def test_unknown_exercise_404s(self):
        res = self.client.get(reverse("api_leaderboard_exercise", args=[999999]))
        self.assertEqual(res.status_code, 404)


# --- Chat ---

class ChatApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)

    def test_post_message(self):
        res = self.post_json(reverse("api_chat"), {"text": "hello gang"})
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["username"], "alice")
        self.assertEqual(data["text"], "hello gang")
        self.assertIn("id", data)
        self.assertIn("created_at", data)

    def test_post_empty_message_rejected(self):
        res = self.post_json(reverse("api_chat"), {"text": "   "})
        self.assertEqual(res.status_code, 400)

    def test_post_too_long_message_rejected(self):
        res = self.post_json(reverse("api_chat"), {"text": "x" * 1001})
        self.assertEqual(res.status_code, 400)

    def test_get_returns_latest_50_ascending(self):
        for i in range(60):
            ChatMessage.objects.create(user=self.alice, text=f"msg {i}")
        res = self.client.get(reverse("api_chat"))
        data = res.json()
        self.assertEqual(len(data), 50)
        self.assertEqual(data[0]["text"], "msg 10")
        self.assertEqual(data[-1]["text"], "msg 59")

    def test_get_after_id(self):
        msgs = [ChatMessage.objects.create(user=self.alice, text=f"msg {i}") for i in range(5)]
        res = self.client.get(reverse("api_chat"), {"after": msgs[2].id})
        data = res.json()
        self.assertEqual([m["text"] for m in data], ["msg 3", "msg 4"])

    def test_get_after_max_id_returns_empty(self):
        msg = ChatMessage.objects.create(user=self.alice, text="only one")
        res = self.client.get(reverse("api_chat"), {"after": msg.id})
        self.assertEqual(res.json(), [])

    def test_messages_visible_across_users(self):
        ChatMessage.objects.create(user=self.bob, text="from bob")
        res = self.client.get(reverse("api_chat"))
        texts = [m["text"] for m in res.json()]
        self.assertIn("from bob", texts)


# --- Coach ---

def _mock_openrouter_response(reply="Get back to your set.", status_code=200):
    mock_resp = Mock()
    mock_resp.status_code = status_code
    mock_resp.ok = 200 <= status_code < 300
    mock_resp.json.return_value = {"choices": [{"message": {"content": reply}}]}
    return mock_resp


@override_settings(OPENROUTER_API_KEY="test-key", OPENROUTER_MODEL="google/gemma-4-31b-it:free")
class CoachApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)

    @patch("gym.api_views.requests.post")
    def test_happy_path_returns_reply(self, mock_post):
        mock_post.return_value = _mock_openrouter_response("Nice work, now go do another set.")
        res = self.post_json(reverse("api_coach"), {"messages": [{"role": "user", "content": "how many sets?"}]})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], "Nice work, now go do another set.")

    @patch("gym.api_views.requests.post")
    def test_system_prompt_includes_username_and_workout_facts(self, mock_post):
        mock_post.return_value = _mock_openrouter_response()
        day = self.make_day(self.alice, day_date=date.today())
        WorkoutExercise.objects.create(workout_day=day, exercise=self.ex, order=0)

        self.post_json(reverse("api_coach"), {"messages": [{"role": "user", "content": "hi"}]})

        sent_payload = mock_post.call_args.kwargs["json"]
        system_msg = sent_payload["messages"][0]
        self.assertEqual(system_msg["role"], "system")
        self.assertIn("alice", system_msg["content"])
        self.assertIn(self.ex.name, system_msg["content"])
        self.assertEqual(sent_payload["model"], "google/gemma-4-31b-it:free")

    @patch("gym.api_views.requests.post")
    def test_history_truncated_to_20_messages(self, mock_post):
        mock_post.return_value = _mock_openrouter_response()
        history = [{"role": "user", "content": f"msg {i}"} for i in range(30)]
        self.post_json(reverse("api_coach"), {"messages": history})

        sent_payload = mock_post.call_args.kwargs["json"]
        # 1 system message + last 20 of the 30 sent
        self.assertEqual(len(sent_payload["messages"]), 21)
        self.assertEqual(sent_payload["messages"][1]["content"], "msg 10")
        self.assertEqual(sent_payload["messages"][-1]["content"], "msg 29")

    def test_missing_messages_rejected(self):
        res = self.post_json(reverse("api_coach"), {})
        self.assertEqual(res.status_code, 400)

    def test_messages_not_a_list_rejected(self):
        res = self.post_json(reverse("api_coach"), {"messages": "not a list"})
        self.assertEqual(res.status_code, 400)

    def test_bad_role_rejected(self):
        res = self.post_json(
            reverse("api_coach"), {"messages": [{"role": "system", "content": "sneaky"}]}
        )
        self.assertEqual(res.status_code, 400)

    def test_empty_content_rejected(self):
        res = self.post_json(reverse("api_coach"), {"messages": [{"role": "user", "content": "   "}]})
        self.assertEqual(res.status_code, 400)

    @override_settings(OPENROUTER_API_KEY="")
    def test_missing_api_key_returns_503(self):
        res = self.post_json(reverse("api_coach"), {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(res.status_code, 503)

    @patch("gym.api_views.requests.post")
    def test_openrouter_rate_limit_returns_429(self, mock_post):
        mock_post.return_value = _mock_openrouter_response(status_code=429)
        res = self.post_json(reverse("api_coach"), {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(res.status_code, 429)

    @patch("gym.api_views.requests.post")
    def test_openrouter_server_error_returns_502(self, mock_post):
        mock_post.return_value = _mock_openrouter_response(status_code=500)
        res = self.post_json(reverse("api_coach"), {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(res.status_code, 502)

    @patch("gym.api_views.requests.post")
    def test_openrouter_network_error_returns_502(self, mock_post):
        import requests as requests_module
        mock_post.side_effect = requests_module.ConnectionError("boom")
        res = self.post_json(reverse("api_coach"), {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(res.status_code, 502)
