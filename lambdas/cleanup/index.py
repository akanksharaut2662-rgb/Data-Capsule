# lambdas/cleanup/index.py
import json
import boto3
import time
import os

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']

def lambda_handler(event, context):
    """
    Scheduled cleanup job.
    DynamoDB TTL auto-deletes expired metadata records.
    This Lambda cleans up the corresponding S3 objects.
    """
    table = dynamodb.Table(TABLE_NAME)
    now = int(time.time())
    deleted_count = 0
    errors = []

    # Scan for expired or deleted capsules that still have S3 data
    # In production, use DynamoDB Streams triggered by TTL deletions
    # Here we scan for items with ttl < now as a safety net
    response = table.scan(
        FilterExpression='#ttl < :now AND #status = :active',
        ExpressionAttributeNames={
            '#ttl': 'ttl',
            '#status': 'status'
        },
        ExpressionAttributeValues={
            ':now': now,
            ':active': 'active'
        }
    )

    for item in response.get('Items', []):
        capsule_id = item['capsule_id']
        s3_key = item.get('s3_key')

        try:
            # Delete from S3
            if s3_key:
                s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
                print(f"Deleted S3 object: {s3_key}")

            # Mark as deleted in DynamoDB
            table.update_item(
                Key={'capsule_id': capsule_id},
                UpdateExpression='SET #status = :deleted',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':deleted': 'deleted'}
            )
            deleted_count += 1

        except Exception as e:
            errors.append({'capsule_id': capsule_id, 'error': str(e)})
            print(f"Error cleaning capsule {capsule_id}: {str(e)}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Cleanup complete',
            'deleted_count': deleted_count,
            'errors': errors
        })
    }