from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Content, Score
from .pagination import StandardResultsSetPagination
from .serializers import ContentSerializer, ScoreSerializer
from .tasks import process_score
import redis

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


class ContentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    permission_classes = [IsAuthenticated]  # Add this if you want authentication

    @action(detail=True, methods=['GET'])
    def get_average_score(self, request, pk=None):
        content = self.get_object()
        cache_key = f'content:{content.id}:average_score'
        cached_score = redis_client.get(cache_key)

        if cached_score:
            content.average_score = float(cached_score)

        serializer = self.get_serializer(content)
        return Response(serializer.data)


class ContentListView(generics.ListAPIView):
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Content.objects.all()
        title = self.request.query_params.get('title', None)
        if title:
            queryset = queryset.filter(title__icontains=title)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        for content in queryset:
            average_score = redis_client.get(f'content:{content.id}:average_score')

            if not average_score:
                average_score = content.average_score
                redis_client.set(f'content:{content.id}:average_score', average_score)

            content.average_score = average_score
        response = super().list(request, *args, **kwargs)
        for idx, data in enumerate(response.data['results']):
            content = queryset[idx]
            data['average_score'] = content.average_score

        return response


class ScoreViewSet(viewsets.ModelViewSet):
    queryset = Score.objects.all()
    serializer_class = ScoreSerializer
    permission_classes = [IsAuthenticated]  # Add this if you want authentication

    def get_queryset(self):
        content_id = self.kwargs.get('content_id')
        return Score.objects.filter(content_id=content_id)

    def perform_create(self, serializer):
        content_id = self.kwargs.get('content_id')
        content = Content.objects.get(id=content_id)
        score = serializer.validated_data['score']
        # Create score and handle score processing
        score_instance = serializer.save(content=content, user=self.request.user)
        process_score(content_id, score, created=True)

    def perform_update(self, serializer):
        score_instance = serializer.instance
        new_score = serializer.validated_data['score']
        old_score = score_instance.score
        score_instance.save()
        process_score(score_instance.content.id, new_score, created=False)

    @action(detail=True, methods=['GET'])
    def get_scores(self, request, content_id=None):
        content = Content.objects.get(id=content_id)
        scores = Score.objects.filter(content=content)
        serializer = ScoreSerializer(scores, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'])
    def create_score(self, request, content_id=None):
        content = Content.objects.get(id=content_id)
        score = request.data.get('score')

        if score is None or not (1 <= score <= 5):
            return Response({"error": "Score must be between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the score and return it
        score_instance = Score.objects.create(content=content, user=request.user, score=score)
        process_score(content_id, score, created=True)
        score_serializer = ScoreSerializer(score_instance)
        return Response(score_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['PUT'])
    def update_score(self, request, content_id=None, score_id=None):
        content = Content.objects.get(id=content_id)
        score_instance = Score.objects.get(id=score_id, content=content, user=request.user)
        new_score = request.data.get('score')

        if new_score is None or not (0 <= new_score <= 5):
            return Response({"error": "Score must be between 0 and 5."}, status=status.HTTP_400_BAD_REQUEST)

        score_instance.score = new_score
        score_instance.save()
        process_score(content_id, new_score, created=False)
        score_serializer = ScoreSerializer(score_instance)
        return Response(score_serializer.data, status=status.HTTP_200_OK)
