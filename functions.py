import json
from datetime import datetime
from typing import Dict, List, Optional

def load_history(convID):
    try:
        with open(convID + '.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_history(convID, messages):
    with open(convID + '.json', 'w') as f:
        json.dump(messages, f, indent=2)

def parse_transcript_interactions(transcript: str) -> List[Dict]:
    interactions = []
    if not transcript:
        print("No se recibió transcripción")
        return interactions
    lines = transcript.strip().split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        speaker = "system" if i % 2 == 0 else "user"
        interaction = { "speaker": speaker, "content": line }
        interactions.append(interaction)
    return interactions

def generate_call_report(transcript_data: Dict, call_config: Dict, contact_id: str) -> Dict:
    transcript = transcript_data.get('transcript', '')
    interactions = parse_transcript_interactions(transcript)
    call_report = {
        "call_metadata": {
            "contact_id": contact_id,
            "timestamp": datetime.now().isoformat(),
            "phone_number": call_config.get('phone_number', ''),
            "interview_context": call_config.get('interview_context', ''),
            "questions_asked": call_config.get('questions', []),
            "language": call_config.get('language', 'es')
        },
        "transcription": {
            "interactions": interactions
        },
    }
    
    return call_report

def save_call_report(call_report: dict, s3_bucket: str, s3_prefix: str, filename: str = None) -> str:
    if not filename:
        contact_id = call_report.get('call_metadata', {}).get('contact_id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"call_report_{contact_id}_{timestamp}.json"
    try:
        import boto3
        import os
        import tempfile
        AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
        s3_client = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        if s3_prefix.endswith('.wav'):
            s3_key = s3_prefix.replace('.wav', '_report.json')
        else:
            s3_key = f"{s3_prefix.rstrip('/')}/{filename}"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
            json.dump(call_report, temp_file, indent=2, ensure_ascii=False)
            temp_filename = temp_file.name
        s3_client.upload_file(temp_filename, s3_bucket, s3_key)
        os.unlink(temp_filename)
        s3_location = f"s3://{s3_bucket}/{s3_key}"
        return s3_location

    except Exception as e:
        print(f"❌ Error guardando en S3: {e}")
        raise
