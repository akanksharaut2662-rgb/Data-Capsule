# lambdas/upload/index.py
import json
import boto3
import uuid
import time
import os
import base64

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

BUCKET_NAME   = os.environ['BUCKET_NAME']
TABLE_NAME    = os.environ['TABLE_NAME']
EXPIRY_HOURS  = float(os.environ.get('EXPIRY_HOURS', 24))
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')
FRONTEND_URL  = os.environ.get('FRONTEND_URL', '')

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))

        file_content_b64 = body.get('file_content')
        file_name        = body.get('file_name', 'unknown.txt')
        file_type        = body.get('file_type', 'text/plain')
        uploader_email   = body.get('uploader_email', '').strip()

        if not file_content_b64:
            return response(400, {'error': 'No file content provided'})

        file_bytes = base64.b64decode(file_content_b64)

        capsule_id = str(uuid.uuid4())
        s3_key     = f"capsules/{capsule_id}/{file_name}"

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_bytes,
            ContentType=file_type,
            ServerSideEncryption='AES256'
        )

        now = int(time.time())
        ttl = now + int(EXPIRY_HOURS * 3600)

        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item={
            'capsule_id':     capsule_id,
            'file_name':      file_name,
            'file_type':      file_type,
            's3_key':         s3_key,
            'uploader_email': uploader_email,
            'created_at':     now,
            'ttl':            ttl,
            'status':         'active',
            'access_count':   0
        })

        # ── Send email notification via SNS ──
        if uploader_email and SNS_TOPIC_ARN:
            send_notification(
                email      = uploader_email,
                capsule_id = capsule_id,
                file_name  = file_name,
                ttl        = ttl,
                expiry_hours = EXPIRY_HOURS
            )

        return response(200, {
            'message':         'Capsule created successfully',
            'capsule_id':      capsule_id,
            'expires_at':      ttl,
            'expires_in_hours': EXPIRY_HOURS,
            'access_url':      f"/capsule/{capsule_id}"
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return response(500, {'error': 'Internal server error', 'detail': str(e)})


def send_notification(email, capsule_id, file_name, ttl, expiry_hours):
    try:
        import datetime

        expiry_dt    = datetime.datetime.utcfromtimestamp(ttl)
        expiry_str   = expiry_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        expiry_label = f"{int(expiry_hours * 60)} minutes" if expiry_hours < 1 else f"{int(expiry_hours)} hours"

        # Check if email is already confirmed — only subscribe if not
        existing = sns.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
        already_confirmed = any(
            sub['Endpoint'] == email and sub['SubscriptionArn'] != 'PendingConfirmation'
            for sub in existing.get('Subscriptions', [])
        )

        if not already_confirmed:
            sns.subscribe(
                TopicArn = SNS_TOPIC_ARN,
                Protocol = 'email',
                Endpoint = email
            )
            print(f"Subscription requested for {email} — confirmation email sent")
            # Can't publish yet since not confirmed — store a flag or just notify
            # We'll publish anyway; SNS will deliver once confirmed
        
        message = f"""
You have been granted secure access to a Data Capsule.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPSULE DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File:        {file_name}
Capsule ID:  {capsule_id}
Expires:     {expiry_str} ({expiry_label} from now)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO ACCESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Open the secure portal:
   {FRONTEND_URL}

2. Paste your Capsule ID into the Load field:
   {capsule_id}

3. Click LOAD then use Preview, Query, or
   Partial Export to view the data.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- This capsule expires in {expiry_label}
- After expiry, all data is permanently deleted
- You cannot download the raw file
- Access is logged and monitored

This is an automated message from Data Capsule.
Do not reply to this email.
        """.strip()

        sns.publish(
            TopicArn = SNS_TOPIC_ARN,
            Subject  = f"[Data Capsule] Secure Access — {file_name} (expires in {expiry_label})",
            Message  = message
        )

        print(f"Capsule notification published for {email}")

    except Exception as e:
        print(f"SNS notification failed: {str(e)}")

def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }