import json
from twitter import OAuth, TwitterStream
import googlemaps
import config
from watson_developer_cloud import NaturalLanguageUnderstandingV1
from watson_developer_cloud.natural_language_understanding_v1 import Features, EntitiesOptions, SentimentOptions
from kafka import KafkaProducer
from random import randrange, uniform
import boto3

producer = KafkaProducer(value_serializer=lambda m: json.dumps(m).encode('ascii'), bootstrap_servers=config.KAFKA_SERVER)

natural_language_understanding = NaturalLanguageUnderstandingV1(
    version=config.WATSON_VERSION,
    username=config.WATSON_USERNAME,
    password=config.WATSON_PASSWORD)
gmaps = googlemaps.Client(key=config.GOOGLE_API_KEY)
oauth = OAuth(config.ACCESS_TOKEN, config.ACCESS_SECRET, config.CONSUMER_KEY, config.CONSUMER_SECRET)
twitter_stream = TwitterStream(auth=oauth)

sns = boto3.client('sns', region_name='us-east-1')

def handler(event, context):
    iterator = twitter_stream.statuses.filter(track=event['keyword'])
    count = 10
    result = []
    for tweet in iterator:
        try:
            text = tweet['text']
        except Exception as e:
            continue
        if tweet['lang'] == 'en':
            try:
                response = natural_language_understanding.analyze(
                    text=tweet['text'],
                    features=Features(entities=EntitiesOptions(), sentiment=SentimentOptions()))
                sentiment = response['sentiment']['document']['label']
            except:
                continue

            if tweet["coordinates"]:
                lng = tweet["coordinates"]["coordinates"][0]
                lat = tweet["coordinates"]["coordinates"][1]
            elif tweet['place']:
                lng = (tweet["place"]["bounding_box"]['coordinates'][0][0][0] + tweet["place"]["bounding_box"]['coordinates'][0][1][0]) / 2
                lat = (tweet["place"]["bounding_box"]['coordinates'][0][1][1] + tweet["place"]["bounding_box"]['coordinates'][0][2][1]) / 2
            elif tweet['user']['location']:
                try:
                    geocode_result = gmaps.geocode(tweet["user"]["location"])
                    lat = geocode_result[0]['geometry']['location']['lat']
                    lng = geocode_result[0]['geometry']['location']['lng']
                except Exception as e:
                    if len(result) <= 1:
                        lat,lng = uniform(-90,90), uniform(-180,180)
                    else:
                        random_index = randrange(len(result)-1)
                        lat, lng = result[random_index]['lat'] + uniform(-5,5), result[random_index]['lng'] + uniform(-5,5)
            else:
                if len(result) <= 1:
                    lat,lng = uniform(-90,90), uniform(-180,180)
                else:
                    random_index = randrange(len(result)-1)
                    lat, lng = result[random_index]['lat'], result[random_index]['lng']

            data = {"lat": lat, "lng": lng, "text": text, "sentiment": sentiment}
            result.append(data)
            producer.send('tweet_sentiment', data)
            count -= 1
            if count <= 0:
                break
    sns.publish(TopicArn='arn:aws:sns:us-east-1:710467018335:IndexTweet', Message='Trigger indexing')
    return result
