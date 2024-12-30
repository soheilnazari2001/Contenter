from rest_framework import serializers
from .models import Content, Score


class CreateContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ["title", "content"]

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class ContentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    is_rated = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    number_of_ratings = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = [
            'id', 'title', 'content',
            'created_at', 'updated_at', 'author_name',
            'number_of_ratings', 'average_rating', 'user_rating',
            'is_rated',
        ]

    def get_is_rated(self, obj):
        request = self.context.get('request')
        if request and hasattr(obj, 'user_rating'):
            return obj.user_rating is not None
        return False

    def get_user_rating(self, obj):
        if hasattr(obj, 'user_rating') and obj.user_rating:
            return obj.user_rating.score
        return None

    def get_average_rating(self, obj):
        return obj.get_average_score()

    def get_number_of_ratings(self, obj):
        return Score.objects.filter(content=obj).count()


class ScoreSerializer(serializers.Serializer):
    content_id = serializers.IntegerField()
    score = serializers.IntegerField(min_value=1, max_value=5)
