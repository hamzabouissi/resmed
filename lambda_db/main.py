import boto3
import os

topic_arn = os.getenv("TopicArn")
dynamodb = boto3.resource('dynamodb')
sns = boto3.resource('sns')

def handler(event, context, *args,**kwargs):
    for e in event['Records']:
        data = e['dynamodb']['NewImage']
        events_per_hour = float(list(data['events_per_hour'].items())[0][1])
        mask_seal = float(list(data['mask_seal'].items())[0][1])

       
        message = ""
        if mask_seal >= 10 and mask_seal <20:
            message = message + "you have experienced moderate leak during your sleep\n"
        elif mask_seal < 10:
            message = message + "you have experienced a high leak during your sleep\n"

        if events_per_hour < 5:
            message = message + "for event per hours you have experienced: Normal"
        elif 5 <= events_per_hour <= 14.9:
            message = message + "for event per hours you have experienced: Mild sleep apnea"
        elif 15 <= events_per_hour <= 29.9:
            message = message + "for event per hours you have experienced: Moderate sleep apnea"
        else:
            message = message + "for event per hours you have experienced: Severe sleep apnea"
    
        topic = sns.Topic(arn=topic_arn)
        response = topic.publish(Message=message)
        print(f"message:{message}",f"was sent to topic: {topic_arn} with response {response}",sep="\n")
        message_id = response['MessageId']
        return message_id