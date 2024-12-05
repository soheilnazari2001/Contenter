# serializers.py
from rest_framework import serializers
from .models import Content, Score
from django.core.exceptions import ValidationError


class ContentSerializer(serializers.ModelSerializer):
    average_score = serializers.FloatField(read_only=True)
    number_of_scores = serializers.IntegerField(read_only=True)

    class Meta:
        model = Content
        fields = ['id', 'title', 'content', 'author', 'average_score', 'number_of_scores']

    def validate_title(self, value):
        if len(value) < 3:
            raise ValidationError("Title should be at least 3 characters long.")
        return value

    def create(self, validated_data):
        content = Content.objects.create(**validated_data)
        return content

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance


class ScoreSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    content = serializers.StringRelatedField()

    class Meta:
        model = Score
        fields = ['id', 'score', 'user', 'content']

    def create(self, validated_data):
        score = Score.objects.create(**validated_data)
        return score

    def update(self, instance, validated_data):
        instance.score = validated_data.get('score', instance.score)
        instance.save()
        return instance
