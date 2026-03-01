# lambdas/upload/index.py
import json
import boto3
import uuid
import time
import os
import base64

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
EXPIRY_HOURS = int(os.environ.get('EXPIRY_HOURS', 0.25))

def lambda_handler(event, context):
    try:
        # Parse the incoming request
        body = json.loads(event.get('body', '{}'))
        
        file_content_b64 = body.get('file_content')  # base64 encoded file
        file_name = body.get('file_name', 'unknown.txt')
        file_type = body.get('file_type', 'text/plain')
        uploader_email = body.get('uploader_email', '')

        if not file_content_b64:
            return response(400, {'error': 'No file content provided'})

        # Decode base64 file
        file_bytes = base64.b64decode(file_content_b64)

        # Generate unique capsule ID
        capsule_id = str(uuid.uuid4())
        s3_key = f"capsules/{capsule_id}/{file_name}"

        # Upload to S3 (private, no public access)
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_bytes,
            ContentType=file_type,
            ServerSideEncryption='AES256'
        )

        # Calculate TTL (current time + 24 hours)
        now = int(time.time())
        ttl = now + (EXPIRY_HOURS * 3600)

        # Store capsule metadata in DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item={
            'capsule_id': capsule_id,
            'file_name': file_name,
            'file_type': file_type,
            's3_key': s3_key,
            'uploader_email': uploader_email,
            'created_at': now,
            'ttl': ttl,
            'status': 'active',
            'access_count': 0
        })

        # Return capsule access URL (just the ID — no direct S3 link)
        return response(200, {
            'message': 'Capsule created successfully',
            'capsule_id': capsule_id,
            'expires_at': ttl,
            'expires_in_hours': EXPIRY_HOURS,
            'access_url': f"/capsule/{capsule_id}"
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return response(500, {'error': 'Internal server error'})


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }