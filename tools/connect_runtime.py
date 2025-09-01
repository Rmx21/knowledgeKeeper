"""
Runtime de Amazon Connect para la nueva implementación
- Inicia llamadas outbound
- Lee/actualiza atributos del contacto (DTMF, NovaPrompt)
- Busca grabaciones en S3 y transcribe con Transcribe
"""

import os
import time
import uuid
import boto3
from datetime import datetime
from typing import Dict, Tuple

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
CONNECT_INSTANCE_ID = os.getenv('CONNECT_INSTANCE_ID')
CONTACT_FLOW_ID = os.getenv('CONTACT_FLOW_ID')
SOURCE_PHONE_NUMBER = os.getenv('SOURCE_PHONE_NUMBER')


def _connect_client():
    return boto3.client(
        'connect',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

def _s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

def _transcribe_client():
    return boto3.client(
        'transcribe',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

def start_outbound_call(phone_number: str, interview_context: str, opening_prompt: str = "¿Es un buen momento para iniciar?") -> Dict:
    """Inicia una llamada outbound y configura atributos iniciales requeridos por el flow."""
    client = _connect_client()
    call_id = f"nova_connect_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{phone_number[-4:]}"

    attributes = {
        "NovaPrompt": opening_prompt,
        "InterviewContext": interview_context,
        "NovaSessionId": call_id,
        "QuestionCount": "0",
        "InterviewStep": "0",
    }

    resp = client.start_outbound_voice_contact(
        DestinationPhoneNumber=phone_number,
        ContactFlowId=CONTACT_FLOW_ID,
        InstanceId=CONNECT_INSTANCE_ID,
        SourcePhoneNumber=SOURCE_PHONE_NUMBER,
        Attributes=attributes
    )
    return {
        "ContactId": resp['ContactId'],
        "NovaSessionId": call_id
    }

def get_contact_status(contact_id: str) -> Dict:
    try:
        client = _connect_client()
        resp = client.describe_contact(InstanceId=CONNECT_INSTANCE_ID, ContactId=contact_id)
        contact = resp.get('Contact', {})
        status_obj = contact.get('Status', {}) if isinstance(contact.get('Status', {}), dict) else {}
        state = contact.get('State') or status_obj.get('State')
        disconnect_ts = contact.get('DisconnectTimestamp') or status_obj.get('DisconnectTimestamp')
        if disconnect_ts:
            return {"active": False, "state": state or 'DISCONNECTED', "disconnectTimestamp": str(disconnect_ts)}
        terminal = {'DISCONNECTED','COMPLETED','ENDED','TERMINATED'}
        is_active = (state not in terminal) if state else True
        return {"active": is_active, "state": state, "disconnectTimestamp": None}
    except Exception as e:
        return {"active": True, "state": None, "error": str(e)}

def update_prompt(contact_id: str, text: str) -> bool:
    try:
        client = _connect_client()
        client.update_contact_attributes(
            InstanceId=CONNECT_INSTANCE_ID,
            InitialContactId=contact_id,
            Attributes={"NovaPrompt": text}
        )
        return True
    except Exception:
        return False

def get_contact_attributes(contact_id: str) -> Dict:
    try:
        client = _connect_client()
        resp = client.get_contact_attributes(InstanceId=CONNECT_INSTANCE_ID, InitialContactId=contact_id)
        return resp.get('Attributes', {}) or {}
    except Exception:
        return {}

def clear_user_response(contact_id: str) -> bool:
    """
    Limpia el atributo userResponse para evitar que se quede 'pegado' el valor anterior.
    """
    try:
        client = _connect_client()
        client.update_contact_attributes(
            InstanceId=CONNECT_INSTANCE_ID,
            InitialContactId=contact_id,
            Attributes={"userResponse": ""} 
        )
        return True
    except Exception:
        return False

def send_farewell_and_hangup(contact_id: str, farewell_message: str = "Gracias por tu tiempo. La entrevista ha terminado. ¡Que tengas un excelente día!") -> bool:
    """
    Envía un mensaje de despedida y programa el colgado de la llamada.
    """
    try:
        # Primero enviar el mensaje de despedida
        if update_prompt(contact_id, farewell_message):
            
            time.sleep(8)
            
            client = _connect_client()
            client.stop_contact(
                ContactId=contact_id,
                InstanceId=CONNECT_INSTANCE_ID
            )
            print("Llamada terminada exitosamente")
            return True
        else:
            print("No se pudo enviar mensaje de despedida")
            return False
    except Exception as e:
        print(f"Error enviando despedida y terminando llamada: {e}")
        return False


def get_s3_bucket_from_connect() -> Tuple[str, str]:
    client = _connect_client()
    resp = client.list_instance_storage_configs(InstanceId=CONNECT_INSTANCE_ID, ResourceType='CALL_RECORDINGS')
    for cfg in resp.get('StorageConfigs', []):
        if cfg.get('StorageType') == 'S3':
            s3c = cfg.get('S3Config', {})
            b = s3c.get('BucketName')
            p = s3c.get('BucketPrefix')
            if b:
                return b, p
    raise RuntimeError("No S3 storage config found for CALL_RECORDINGS")

def get_call_recording_and_transcript(contact_id: str, max_wait_minutes: int = 5) -> Dict:
    s3 = _s3_client()
    bucket, prefix = get_s3_bucket_from_connect()
    wait_seconds = 0
    max_wait = max_wait_minutes * 60
    while wait_seconds < max_wait:
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in resp.get('Contents', []):
                key = obj['Key']
                if contact_id in key and key.endswith('.wav'):
                    return _download_and_transcribe(bucket, key, contact_id)
        except Exception as e:
            print(f"Error buscando grabación: {e}")
        time.sleep(10)
        wait_seconds += 10
    return "error"

def _download_and_transcribe(bucket: str, key: str, contact_id: str) -> Dict:
    s3 = _s3_client()
    local = f"recording_{contact_id}.wav"
    s3.download_file(bucket, key, local)
    text = transcribe_with_aws(local, contact_id, bucket)
    try:
        os.remove(local)
    except Exception:
        pass
    return {
        "transcript": text,
        "audio_s3_url": f"s3://{bucket}/{key}",
        "s3_bucket": bucket,
        "s3_key": key
    }

def transcribe_with_aws(audio_file: str, contact_id: str, bucket_name: str) -> str:
    try:
        s3 = _s3_client()
        tr = _transcribe_client()
        temp_key = f"temp-transcribe/{contact_id}_{uuid.uuid4()}.wav"
        s3.upload_file(audio_file, bucket_name, temp_key)
        s3_uri = f"s3://{bucket_name}/{temp_key}"
        job_name = f"transcribe-{contact_id}-{int(time.time())}"
        tr.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            MediaFormat='wav',
            LanguageCode='es-ES'
        )
        wait = 0
        while wait < 300:
            resp = tr.get_transcription_job(TranscriptionJobName=job_name)
            status = resp['TranscriptionJob']['TranscriptionJobStatus']
            if status == 'COMPLETED':
                import requests
                uri = resp['TranscriptionJob']['Transcript']['TranscriptFileUri']
                data = requests.get(uri).json()
                segments = data['results'].get('audio_segments', [])
                parts = [seg.get('transcript','') for seg in segments]
                text = "\n".join(parts)
                s3.delete_object(Bucket=bucket_name, Key=temp_key)
                tr.delete_transcription_job(TranscriptionJobName=job_name)
                return text
            if status == 'FAILED':
                s3.delete_object(Bucket=bucket_name, Key=temp_key)
                tr.delete_transcription_job(TranscriptionJobName=job_name)
                return "Falló la transcripción"
            time.sleep(10)
            wait += 10
        s3.delete_object(Bucket=bucket_name, Key=temp_key)
        tr.delete_transcription_job(TranscriptionJobName=job_name)
        return "Timeout en transcripción"
    except Exception as e:
        return f"Error en transcripción: {e}"
