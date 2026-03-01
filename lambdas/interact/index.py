# lambdas/interact/index.py
import json
import boto3
import time
import os
import base64

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']

def lambda_handler(event, context):
    try:
        path_params = event.get('pathParameters', {}) or {}
        capsule_id = path_params.get('capsule_id')
        
        if not capsule_id:
            return response(400, {'error': 'capsule_id is required'})

        query_params = event.get('queryStringParameters', {}) or {}
        action = query_params.get('action', 'preview')

        # Fetch capsule metadata from DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        result = table.get_item(Key={'capsule_id': capsule_id})
        
        item = result.get('Item')
        if not item:
            return response(404, {'error': 'Capsule not found or has expired'})

        # Check expiry
        now = int(time.time())
        if item.get('ttl', 0) < now:
            return response(410, {'error': 'Capsule has expired. Data has been deleted.'})

        if item.get('status') != 'active':
            return response(403, {'error': 'Capsule is no longer active'})

        # Get file details from item
        file_name = item.get('file_name', 'unknown')
        file_type = item.get('file_type', 'text/plain')
        s3_key = item['s3_key']

        # Increment access counter
        table.update_item(
            Key={'capsule_id': capsule_id},
            UpdateExpression='SET access_count = access_count + :val',
            ExpressionAttributeValues={':val': 1}
        )

        # ---- METADATA: no S3 fetch needed ----
        if action == 'metadata':
            return response(200, {
                'capsule_id': capsule_id,
                'file_name': file_name,
                'file_type': file_type,
                'created_at': int(item['created_at']),
                'expires_at': int(item['ttl']),
                'access_count': int(item.get('access_count', 0)),
                'status': item['status']
            })

        # ---- ALL OTHER ACTIONS: fetch from S3 ----
        s3_object = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        file_content = s3_object['Body'].read()

        if action == 'preview':
            return handle_preview(file_content, file_type, file_name, item)
        elif action == 'query':
            return handle_query(file_content, file_type, query_params)
        elif action == 'partial_export':
            return handle_partial_export(file_content, file_type, query_params)
        else:
            return response(400, {'error': f'Unknown action: {action}. Valid actions: preview, query, partial_export, metadata'})

    except Exception as e:
        print(f"Error: {str(e)}")
        return response(500, {'error': 'Internal server error', 'detail': str(e)})


def handle_preview(file_content, file_type, file_name, item):
    """Returns a safe text preview — never raw file bytes as a download."""
    
    if 'text' in file_type or file_name.endswith(('.txt', '.csv', '.json', '.xml', '.log')):
        # Safe: return text content (truncated to 5000 chars for preview)
        text = file_content.decode('utf-8', errors='replace')
        preview = text[:5000]
        truncated = len(text) > 5000
        return response(200, {
            'action': 'preview',
            'file_name': file_name,
            'content_type': 'text',
            'preview': preview,
            'truncated': truncated,
            'total_chars': len(text)
        })
    
    elif 'image' in file_type:
        # Safe: return base64 for inline rendering (no download trigger)
        b64 = base64.b64encode(file_content).decode()
        return response(200, {
            'action': 'preview',
            'file_name': file_name,
            'content_type': 'image',
            'data_uri': f"data:{file_type};base64,{b64[:50000]}",  # cap size
            'note': 'Image rendered inline. Raw file is not accessible.'
        })
    
    elif file_type == 'application/pdf':
        # For PDFs: return metadata only in preview (full rendering needs client-side PDF.js)
        return response(200, {
            'action': 'preview',
            'file_name': file_name,
            'content_type': 'pdf',
            'size_bytes': len(file_content),
            'note': 'PDF preview: use the query action to extract text content.'
        })
    
    else:
        return response(200, {
            'action': 'preview',
            'file_name': file_name,
            'content_type': 'binary',
            'size_bytes': len(file_content),
            'note': 'Binary file. Direct download is not permitted.'
        })


def handle_query(file_content, file_type, query_params):
    """For structured data (CSV/JSON): return schema/stats without full data."""
    
    if file_name_is_csv(file_type):
        import csv
        import io
        text = file_content.decode('utf-8', errors='replace')
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        columns = rows[0].keys() if rows else []
        return response(200, {
            'action': 'query',
            'content_type': 'csv',
            'columns': list(columns),
            'total_rows': len(rows),
            'sample_rows': rows[:3],  # Only first 3 rows as sample
            'note': 'Full data access is not permitted. Use partial_export for limited rows.'
        })
    
    elif 'json' in file_type:
        import json as jsonlib
        data = jsonlib.loads(file_content.decode('utf-8'))
        if isinstance(data, list):
            return response(200, {
                'action': 'query',
                'content_type': 'json_array',
                'total_records': len(data),
                'sample': data[:3],
                'keys': list(data[0].keys()) if data else []
            })
        else:
            return response(200, {
                'action': 'query',
                'content_type': 'json_object',
                'keys': list(data.keys()),
                'sample': {k: v for k, v in list(data.items())[:5]}
            })
    
    return response(400, {'error': 'Query action only supports CSV and JSON files'})


def handle_partial_export(file_content, file_type, query_params):
    """Export a limited subset of data — never the full file."""
    max_rows = min(int(query_params.get('rows', 10)), 50)  # Cap at 50 rows max
    
    if file_name_is_csv(file_type):
        import csv
        import io
        text = file_content.decode('utf-8', errors='replace')
        reader = csv.DictReader(io.StringIO(text))
        rows = [row for i, row in enumerate(reader) if i < max_rows]
        return response(200, {
            'action': 'partial_export',
            'rows_returned': len(rows),
            'max_allowed': 50,
            'data': rows,
            'note': f'Partial export: {len(rows)} rows only. Full download is not permitted.'
        })
    
    elif 'text' in file_type:
        text = file_content.decode('utf-8', errors='replace')
        chars = max_rows * 100  # ~100 chars per "row"
        return response(200, {
            'action': 'partial_export',
            'content': text[:chars],
            'truncated': len(text) > chars
        })
    
    return response(400, {'error': 'Partial export not supported for this file type'})


def file_name_is_csv(file_type):
    return 'csv' in file_type or file_type == 'text/csv'


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }