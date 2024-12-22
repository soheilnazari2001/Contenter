from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status
import json

from .models import Content, Score
from .serializers import ContentSerializer, ScoreSerializer
from .kafka_producer import produce_message


@api_view(['POST'])
def create_content(request):
    try:
        data = json.loads(request.body)
        serializer = ContentSerializer(data=data)
        if serializer.is_valid():
            content = serializer.save()

            # Prepare Kafka message
            kafka_message = json.dumps({
                'id': content.id,
                'title': content.title,
                'body': content.body,
                'created_at': content.created_at.isoformat()
            })

            # Produce message to Kafka
            produce_message(
                topic="content-updates",
                key=str(content.id),
                value=kafka_message
            )

            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_score(request):
    """
    API endpoint to create a score and publish it to Kafka.
    """
    try:
        data = json.loads(request.body)
        serializer = ScoreSerializer(data=data)
        if serializer.is_valid():
            score = serializer.save()

            # Prepare Kafka message
            kafka_message = json.dumps({
                'id': score.id,
                'value': score.value,
                'content_id': score.content.id,
                'created_at': score.created_at.isoformat()
            })

            # Produce message to Kafka
            produce_message(
                topic="score-updates",
                key=str(score.id),
                value=kafka_message
            )

            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_content(request, content_id):
    try:
        content = get_object_or_404(Content, id=content_id, is_deleted=False)
        serializer = ContentSerializer(content)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_scores(request, content_id):
    try:
        scores = Score.objects.filter(content_id=content_id)
        serializer = ScoreSerializer(scores, many=True)
        return JsonResponse(serializer.data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
