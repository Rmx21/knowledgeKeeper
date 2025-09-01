"""
Amazon Connect Tool para Strands Agent
Proporciona interface entre el agente inteligente y el sistema de llamadas telefónicas.
"""

import os
import sys
import time
from typing import Dict, List, Optional
from strands.tools import tool

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .connect_runtime import (
    start_outbound_call,
    get_contact_status,
    update_prompt,
    get_call_recording_and_transcript,
)
from functions import generate_call_report, save_call_report

_current_call_state = {
    "active": False,
    "contact_id": None,
    "phone_number": None,
    "questions_sent": [],
    "queued_questions": [],
    "q_sent": [],
    "current_question_index": 0,
    "responses_received": [],
    "call_config": {}
}

@tool
def initialize_call(phone_number: str, interview_context: str, initial_question: str) -> Dict:
    """
    Inicializa una llamada telefónica para entrevista.
    
    Args:
        phone_number: Número telefónico del candidato
        interview_context: Contexto de la entrevista
        initial_question: Primera pregunta para enviar
        
    Returns:
        Dict con información de la llamada iniciada
    """
    global _current_call_state
    
    call_config = {
        "phone_number": phone_number,
        "interview_context": interview_context,
        "questions": [],
        "language": "es"
    }
    
    try:
        opening_prompt = (
            "Hola, soy el asistente de IA de Dacodes para recopilar información de tus proyectos."
            "La llamada será grabada para poder almacenar el conocimiento que nos transmitas."
            "¿Es un buen momento para iniciar?"
        )
        result = start_outbound_call(phone_number, interview_context, opening_prompt)
        contact_id = result.get("ContactId")
        
        _current_call_state.update({
            "active": True,
            "contact_id": contact_id,
            "phone_number": phone_number,
            "questions_sent": [],
            "queued_questions": [],
            "q_sent": [],
            "current_question_index": 0,
            "responses_received": [],
            "call_config": {**call_config, "initial_question": initial_question}
        })
        
        return {
            "success": True,
            "contact_id": contact_id,
            "status": "call_initiated",
            "message": f"Llamada iniciada a {phone_number}",
            "initial_question_ready": initial_question
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status": "call_failed"
        }
        
@tool
def set_call_questions(questions: List[str]) -> Dict:
    """
    Define la lista de preguntas a enviar (sin enviarlas aún).
    Replica la configuración esperada por el bucle q_sent del flujo original.
    """
    global _current_call_state
    if not _current_call_state["active"] or not _current_call_state["contact_id"]:
        return {"success": False, "message": "No hay llamada activa"}

    _current_call_state["queued_questions"] = list(questions or [])
    _current_call_state["q_sent"] = [False] * len(_current_call_state["queued_questions"])
    return {
        "success": True,
        "queued_count": len(_current_call_state["queued_questions"]),
        "message": "Preguntas cargadas en el estado de la llamada"
    }

@tool
def push_questions_once() -> Dict:
    """
    Empuja (una vez) cualquier pregunta no enviada aún al atributo NovaPrompt, 
    replicando el patrón original basado en q_sent. No espera DTMF.
    """
    global _current_call_state
    if not _current_call_state["active"] or not _current_call_state["contact_id"]:
        return {"success": False, "message": "No hay llamada activa"}

    contact_id = _current_call_state["contact_id"]
    q_list = _current_call_state.get("queued_questions", [])
    q_sent = _current_call_state.get("q_sent", [])
    if not q_list:
        return {"success": True, "sent_now": 0, "message": "No hay preguntas en cola"}

    sent_now = 0
    try:
        for idx, question in enumerate(q_list, start=1):
            try:
                current_flag = q_sent[idx - 1]
            except Exception:
                while len(q_sent) < len(q_list):
                    q_sent.append(False)
                current_flag = q_sent[idx - 1]

            if not current_flag:
                if update_prompt(contact_id, question):
                    q_sent[idx - 1] = True
                    _current_call_state["questions_sent"].append(question)
                    _current_call_state["current_question_index"] = idx
                    sent_now += 1
    except Exception:
        pass

    _current_call_state["q_sent"] = q_sent
    return {
        "success": True,
        "sent_now": sent_now,
        "sent_total": sum(1 for f in q_sent if f),
        "remaining": len(q_list) - sum(1 for f in q_sent if f)
    }

@tool
def monitor_call_status() -> Dict:
    """
    Monitorea el estado actual de la llamada.
    
    Returns:
        Dict con estado actual de la llamada
    """
    global _current_call_state
    
    if not _current_call_state["active"]:
        return {
            "call_active": False,
            "message": "No hay llamada activa"
        }
    
    try:
        contact_status = get_contact_status(_current_call_state["contact_id"])
        if not contact_status.get('active', True):
            _current_call_state["active"] = False
        
        return {
            "call_active": contact_status.get('active', True),
            "contact_id": _current_call_state["contact_id"],
            "state": contact_status.get('state', 'UNKNOWN'),
            "questions_sent_count": len(_current_call_state["questions_sent"]),
            "current_question_index": _current_call_state["current_question_index"],
            "error": contact_status.get('error')
        }
        
    except Exception as e:
        return {
            "call_active": False,
            "error": str(e),
            "message": "Error monitoreando llamada"
        }

@tool
def update_call_message(new_question: str) -> Dict:
    """
    Actualiza el mensaje/pregunta en el flow de la llamada activa.
    
    Args:
        new_question: Nueva pregunta para enviar al candidato
        
    Returns:
        Dict con resultado de la actualización
    """
    global _current_call_state
    
    if not _current_call_state["active"]:
        return {
            "success": False,
            "message": "No hay llamada activa para actualizar"
        }
    
    try:
        success = update_prompt(_current_call_state["contact_id"], new_question)
        
        if success:
            _current_call_state["questions_sent"].append(new_question)
            _current_call_state["current_question_index"] += 1
            
            return {
                "success": True,
                "message": f"Pregunta enviada: {new_question}",
                "question_number": len(_current_call_state["questions_sent"]),
                "contact_id": _current_call_state["contact_id"]
            }
        else:
            return {
                "success": False,
                "message": "Error enviando pregunta al flow"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Error actualizando mensaje en llamada"
        }

@tool
def finalize_call() -> Dict:
    """
    Finaliza la llamada y procesa la transcripción para generar reportes.
    
    Returns:
        Dict con resultado del procesamiento final
    """
    global _current_call_state
    
    if not _current_call_state["contact_id"]:
        return {
            "success": False,
            "message": "No hay información de llamada para finalizar"
        }
    
    try:
        contact_id = _current_call_state["contact_id"]
        call_config = _current_call_state["call_config"]
        
        print("Obteniendo grabación y transcribiendo...")
        transcript_data = get_call_recording_and_transcript(contact_id, max_wait_minutes=3)
        
        if transcript_data == "error":
            return {
                "success": False,
                "message": "Error obteniendo transcripción"
            }
        
        print("Generando reporte de llamada...")
        call_report = generate_call_report(transcript_data, call_config, contact_id)
        
        s3_bucket = transcript_data.get('s3_bucket')
        s3_key = transcript_data.get('s3_key')
        
        report_location = None
        if s3_bucket and s3_key:
            report_location = save_call_report(call_report, s3_bucket, s3_key)
        
        _current_call_state.update({
            "active": False,
            "contact_id": None,
            "phone_number": None,
            "questions_sent": [],
            "current_question_index": 0,
            "responses_received": [],
            "call_config": {}
        })
        
        return {
            "success": True,
            "contact_id": contact_id,
            "transcript": transcript_data.get('transcript', ''),
            "customer_responses": transcript_data.get('customer_responses', []),
            "report_location": report_location,
            "call_report": call_report,
            "message": "Llamada finalizada y procesada correctamente"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Error finalizando llamada"
        }

@tool
def get_call_state() -> Dict:
    """
    Obtiene el estado actual de la llamada (para debugging).
    
    Returns:
        Dict con estado completo actual
    """
    global _current_call_state
    return _current_call_state.copy()
