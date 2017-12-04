import requests
import json
import config


def handler(event, context):
    message = event['Records'][0]['Sns']['Message']
    header = {"Content-Type": "application/json; charset=utf-8",
              "Authorization": config.ONE_SIGNAL_AUTHORIZATION}

    payload = {"app_id": config.APP_ID,
           "included_segments": ["All"],
           "contents": {"en": message}}
    req = requests.post("https://onesignal.com/api/v1/notifications", headers=header, data=json.dumps(payload))
    print(req.status_code, req.reason)
