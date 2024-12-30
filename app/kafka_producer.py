from confluent_kafka import Producer
import logging

producer_config = {
    'bootstrap.servers': 'kafka1:9093,kafka2:9093,kafka3:9093',  # Replace with your Kafka cluster details
    'client.id': 'django-producer'
}

producer = Producer(producer_config)


def delivery_callback(err, msg):
    if err:
        logging.error(f"Message delivery failed: {err}")
    else:
        logging.info(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")


def produce_message(topic, key, value):
    try:
        producer.produce(
            topic,
            key=key,
            value=value,
            callback=delivery_callback
        )
        producer.flush()  # Ensure message is delivered
    except Exception as e:
        logging.error(f"Failed to send message: {e}")
