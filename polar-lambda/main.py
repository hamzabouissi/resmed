import datetime
import uuid
import boto3
import os
import base64
import json

from botocore.exceptions import ClientError


table_name = os.getenv("TableName")
thing_name = os.getenv("ThingName")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

def handler(event, context, *args,**kwargs):

    results = []
    events_count = 0
    mask_seal = 0
    current_date = datetime.datetime.now()
    print(event)
    for e in event['Records']:
        encoded_data = e["kinesis"]["data"]
        bytes_data = base64.b64decode(encoded_data)
        data = json.loads(bytes_data.decode("utf-8"))
        results.append(data)
        mask_seal = min(data['mask_seal'],mask_seal)
        events_count += data['events_per_minute']
    
    print(f"saving data of thing: {thing_name} on date {current_date}")
    result = table.put_item(
        Item={
            "id": str(uuid.uuid4()),
            "events_per_hour": events_count,
            "mask_seal": mask_seal,
            "date": current_date.isoformat(),
            "username": thing_name
        },
    )
    print(f"Result {result}")

    

def _check_thing_name_exist():
    try:
        item = dynamodb.get_item(Key={"username":thing_name},TableName=table_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # Handle the ResourceNotFoundException here
            print(f"The table '{table_name}' does not exist.")
            return
        else:
            # Handle other exceptions
            print(f"An error occurred: {e}")

