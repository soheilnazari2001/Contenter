from confluent_kafka import Consumer, KafkaException, KafkaError
import logging
import json
from django.conf import settings
from app.models import Score
from django.db import IntegrityError


# Kafka Consumer setup
def create_consumer():
    return Consumer({
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': settings.KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest',
    })


# Kafka message consumption logic
def consume_messages():
    consumer = create_consumer()
    consumer.subscribe([settings.KAFKA_TOPIC])

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue  # No message available
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    raise KafkaException(msg.error())

            message_value = msg.value().decode('utf-8')
            logging.info(f"Message received: {message_value}")
            try:
                data = json.loads(message_value)
                content_id = data.get("content_id")
                score = data.get("score")

                # Update or create a new score entry in the database
                if content_id is not None and score is not None:
                    Score.objects.update_or_create(
                        content_id=content_id,
                        defaults={'score': score},
                    )
                else:
                    logging.error("Invalid data received from Kafka")
            except IntegrityError as e:
                logging.error(f"Database integrity error: {e}")
            except Exception as e:
                logging.error(f"Error processing message: {e}")
    finally:
        consumer.close()
