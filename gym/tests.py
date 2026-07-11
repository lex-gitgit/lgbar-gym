import json
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
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
            ("get", reverse("api_chat")),
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
