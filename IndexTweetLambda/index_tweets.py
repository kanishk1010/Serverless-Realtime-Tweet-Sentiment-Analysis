import json
import time
import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
import config
from kafka import KafkaConsumer

consumer = KafkaConsumer(bootstrap_servers=config.KAFKA_SERVER,
                         group_id='lambda_es_index',
                         consumer_timeout_ms=30000,
                         auto_offset_reset='earliest',
                         value_deserializer=lambda m: json.loads(m.decode('ascii')))
consumer.subscribe(['tweet_sentiment'])

es = Elasticsearch(
    hosts=[{'host': config.ES_DOMAIN, 'port': 443}],
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=15
)

sns = boto3.client('sns', region_name='us-east-1')


def create_index():
    index_exists = None
    while index_exists is None:
        try:
            index_exists = es.indices.exists(index="tweet_sentiments")
        except Exception:
            time.sleep(3)

    if index_exists:
        pass
    else:
        index_response = None

        while index_response is None:
            try:
                index_response = es.indices.create(index="tweet_sentiments")
            except Exception:
                time.sleep(3)


def handler(event, context):
    indexed_tweet_count = 0
    create_index()
    for msg in consumer:
        data = msg.value
        response = None
        while response is None:
            try:
                response = es.index(index="tweets", doc_type="tweet", body=data)
            except:
                time.sleep(2)
        indexed_tweet_count += 1
    sns.publish(TopicArn='arn:aws:sns:us-east-1:710467018335:Tweet', Message=str(indexed_tweet_count)+" new tweets indexed!")
