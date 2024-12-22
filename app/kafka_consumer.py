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
    try:
        consumer.subscribe([settings.KAFKA_TOPIC])
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logging.info(f"End of partition reached {msg.topic()}[{msg.partition()}]")
                else:
                    logging.error(f"Kafka error: {msg.error()}")
                continue
            try:
                # Process the message
                payload = json.loads(msg.value().decode('utf-8'))
                Score.objects.create(**payload)
            except IntegrityError as e:
                logging.error(f"Database error: {e}")
    except KafkaException as e:
        logging.error(f"Kafka exception: {e}")
    finally:
        consumer.close()
