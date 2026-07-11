from rest_framework import serializers

from .models import (
    DayPreset,
    DayPresetExercise,
    Exercise,
    WorkoutDay,
    WorkoutExercise,
    WorkoutSet,
)


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ["id", "name", "body_part", "created_at"]


class WorkoutSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutSet
        fields = ["id", "set_number", "reps", "weight", "weight_unit"]


class WorkoutExerciseSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source="exercise.name", read_only=True)
    sets = WorkoutSetSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutExercise
        fields = ["id", "exercise", "exercise_name", "order", "notes", "sets"]


class WorkoutDayListSerializer(serializers.ModelSerializer):
    preset_name = serializers.CharField(source="preset.name", read_only=True)
    exercise_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkoutDay
        fields = ["id", "date", "preset", "preset_name", "notes", "exercise_count", "created_at"]

    def get_exercise_count(self, obj):
        return obj.exercises.count()


class WorkoutDayDetailSerializer(serializers.ModelSerializer):
    preset_name = serializers.CharField(source="preset.name", read_only=True)
    exercises = WorkoutExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutDay
        fields = ["id", "date", "preset", "preset_name", "notes", "exercises", "created_at"]


class DayPresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DayPreset
        fields = ["id", "name", "created_at"]


class DayPresetExerciseSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source="exercise.name", read_only=True)
    exercise_body_part = serializers.CharField(source="exercise.body_part", read_only=True)

    class Meta:
        model = DayPresetExercise
        fields = ["id", "preset", "exercise", "exercise_name", "exercise_body_part", "order"]


class DayPresetDetailSerializer(serializers.ModelSerializer):
    exercises = DayPresetExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = DayPreset
        fields = ["id", "name", "exercises", "created_at"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
