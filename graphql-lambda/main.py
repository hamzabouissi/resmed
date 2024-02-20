import boto3
import os

table_name = os.getenv("TableName")
dynamodb = boto3.resource('dynamodb')

def handler(event, context, *args,**kwargs):
    print(f"received event {event}, {context}")
    dynamdbTable = dynamodb.Table(table_name)
    
    key = event['info']['fieldName']
    print(key)
    if key == "listNotes":
        response = dynamdbTable.scan()
        data = response['Items']
        print(f"list items {data}" )
        return data
        

    if key == "deleteNote":
        noteId = event['arguments']['noteId']
        dynamdbTable.delete_item(
            key={
                "Id":noteId
            }
        )
        return None

    if key == "createNote":
        note = event['arguments']['note']
        response = dynamdbTable.put_item(
            Item=note,
            ReturnValues="ALL_OLD"
        ) 
        print(f"create {note} with response {response}" )
        return response['Attributes']
    
