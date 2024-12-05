from kafka import KafkaProducer
import json
from Contenter.settings import KAFKA_URL
from .models import Content, Score
import redis

redis_client = redis.StrictRedis.from_url('redis://localhost:6379')

producer = KafkaProducer(
    bootstrap_servers=KAFKA_URL,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


def process_score(content_id, score, created):
    content = Content.objects.get(id=content_id)
    cache_key = f'content:{content.id}:average_score'

    if created:
        redis_client.set(cache_key, score)
    scores = Score.objects.filter(content=content)
    total_score = sum([s.score for s in scores])
    new_average_score = total_score / len(scores) if len(scores) > 0 else 0
    content.average_score = new_average_score
    content.user_count = len(scores)
    content.save()
    redis_client.set(cache_key, new_average_score)

    producer.send('score_topic', {
        'content_id': content.id,
        'new_score': new_average_score
    })
    if new_average_score < 0.5:
        redis_client.set(f'content:{content.id}:blocked', True)
    else:
        redis_client.delete(f'content:{content.id}:blocked')


def clear_content_cache(content_id):
    redis_client.delete(f'content:{content_id}:average_score')
    redis_client.delete(f'content:{content_id}:blocked')


def on_score_created_or_updated(content_id, score, created):
    process_score(content_id, score, created)
    clear_content_cache(content_id)
