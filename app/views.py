import json
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics, views, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Content, Score
from .serializers import ContentSerializer, ScoreSerializer
from django.core.cache import cache
from .kafka_producer import produce_message


class ContentCreateView(generics.CreateAPIView):
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ContentListView(generics.ListAPIView):
    queryset = Content.objects.order_by('-created_at').all()
    serializer_class = ContentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        user = self.request.user
        page = self.paginate_queryset(self.queryset)

        if page is None:
            return self.queryset

        prefetch_scores_ids = []
        cached_contents = []

        for content in page:
            redis_key = f"score:{user.id}:{content.id}"
            score = cache.get(redis_key)
            if score is not None:
                content.user_score = [Score(user=user, content=content, score=int(score))]
                cached_contents.append(content)
            else:
                prefetch_scores_ids.append(content.id)

        if prefetch_scores_ids:
            user_scores = Score.objects.filter(user=user, content_id__in=prefetch_scores_ids)
            uncached_contents = Content.objects.filter(id__in=prefetch_scores_ids).prefetch_related(
                Prefetch(
                    'scores',
                    queryset=user_scores,
                    to_attr='user_score'
                )
            )
            contents = cached_contents + list(uncached_contents)
        else:
            contents = cached_contents

        for content in contents:
            if hasattr(content, 'user_score') and content.user_score:
                content.user_score = content.user_score[0]

        return contents


class RateContentView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ScoreSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            data = serializer.validated_data
            content_id = data['content'].id
            redis_key = f"score:{request.user.id}:{content_id}"
            cached_score = cache.get(redis_key)

            if cached_score and int(cached_score) == data['score']:
                return Response(
                    {"message": "Content is already rated!"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cache.set(redis_key, data['score'], timeout=3600)

            message = {
                'user_id': request.user.id,
                'content_id': content_id,
                'score': data['score']
            }

            produce_message(
                topic="content-ratings",
                key=str(request.user.id),
                value=json.dumps(message)
            )

            return Response(status=status.HTTP_202_ACCEPTED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
