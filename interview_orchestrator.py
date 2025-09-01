"""
Interview Orchestrator
Coordina el flujo completo de entrevista telefónica entre el agente inteligente y Amazon Connect.
Gestiona la extracción de preguntas del agente y el flujo dinámico de la llamada.
"""

import time
import re
from typing import Dict, List, Optional, Tuple
from strands.tools import tool
from tools.connect_runtime import get_contact_attributes, clear_user_response, send_farewell_and_hangup

# Importar tools necesarios
from tools.amazon_connect_tool import (
    initialize_call,
    monitor_call_status, 
    update_call_message,
    finalize_call,
    get_call_state,
    set_call_questions,
)
from knowledge_generator import (
    generate_user_knowledge_json,
    generate_user_summary_md,
    save_user_documents
)

@tool
def conduct_interview(user_id: str, phone_number: str, agent_analysis: str, max_questions: int = 4) -> Dict:
    """
    Conduce una entrevista telefónica completa basada en el análisis del agente.
    
    Args:
        user_id: Identificador del usuario (ej: "Rmx21")
        phone_number: Número telefónico del candidato
        agent_analysis: Análisis completo del agente con preguntas generadas
        max_questions: Máximo número de preguntas a realizar (default: 4)
        
    Returns:
        Dict con resultado completo de la entrevista
    """
    
    questions = extract_questions_from_agent_analysis(agent_analysis, max_questions)
    
    if not questions:
        return {
            "success": False,
            "message": "No se pudieron extraer preguntas del análisis del agente",
            "user_id": user_id
        }
    
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q[:100]}{'...' if len(q) > 100 else ''}")
    
    interview_context = f"Entrevista de conocimiento para {user_id} basada en análisis de código"
    first_question = questions[0] if questions else "¿Podrías contarme sobre tu experiencia?"
    
    call_result = initialize_call(phone_number, interview_context, first_question)
    
    if not call_result.get("success"):
        return {
            "success": False,
            "message": f"Error iniciando llamada: {call_result.get('error', 'Desconocido')}",
            "user_id": user_id
        }
    
    contact_id = call_result.get("contact_id")
    print("Llamada iniciada.")
    
    set_call_questions(questions)

    print("Esperando a que la llamada esté establecida...")
    time.sleep(15)
    
    status_check = monitor_call_status()
    if not status_check.get("call_active", False):
        print("La llamada no está activa, esperando más tiempo...")
        time.sleep(10)
        status_check = monitor_call_status()
    
    if status_check.get("call_active", False):
        print("Llamada confirmada como activa, iniciando flujo de preguntas")
        try:
            flow_result = manage_call_flow(questions, max_wait_minutes=10)
            print(f"Flujo de llamada completado: {flow_result.get('message', '')}")
        except Exception as e:
            print(f"Error en flujo de llamada: {e}")
    else:
        print("No se pudo confirmar que la llamada esté activa, continuando sin flujo adicional")
    
    print("Finalizando llamada.")
    final_result = finalize_call()
    
    if not final_result.get("success"):
        return {
            "success": False,
            "message": f"Error finalizando llamada: {final_result.get('error', 'Desconocido')}",
            "user_id": user_id,
            "contact_id": contact_id
        }
    
    print("Generando documentos de conocimiento.")
    call_report = final_result.get("call_report", {})
    
    knowledge_json = generate_user_knowledge_json(
        user_id=user_id,
        call_report=call_report,
        analysis_data={"agent_analysis": agent_analysis, "questions_generated": questions}
    )
    summary_md = generate_user_summary_md(user_id, knowledge_json)
    save_result = save_user_documents(user_id, knowledge_json, summary_md)
    
    return {
        "success": True,
        "user_id": user_id,
        "contact_id": contact_id,
        "questions_asked": len(questions),
        "transcript": final_result.get("transcript", ""),
        "customer_responses": final_result.get("customer_responses", []),
        "report_location": final_result.get("report_location"),
        "knowledge_files": save_result,
        "message": f"Entrevista completada exitosamente para {user_id}"
    }

def extract_questions_from_agent_analysis(analysis: str, max_questions: int = 4) -> List[str]:
    """
    Extrae preguntas del análisis del agente usando patrones de texto.
    
    Args:
        analysis: Texto completo del análisis del agente
        max_questions: Máximo número de preguntas a extraer
        
    Returns:
        Lista de preguntas extraídas
    """
    
    questions = []
    
    question_patterns = [
        r'[\?\¿][^\?\¿]*[\?\¿]',
        r'^[¿\?].+[\?\¿]$',
        r'(?:pregunta|question)[:.]?\s*(.+[\?\¿])',
        r'(?:cuéntame|explica|describe|por qué|cómo|qué).+[\?\¿]',
    ]
    
    for pattern in question_patterns:
        matches = re.findall(pattern, analysis, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            clean_question = match.strip()
            if len(clean_question) > 10 and clean_question not in questions:
                questions.append(clean_question)
    
    if not questions:
        lines = analysis.split('\n')
        for line in lines:
            line = line.strip()
            if (line.endswith('?') or line.endswith('¿')) and len(line) > 15:
                if line not in questions:
                    questions.append(line)
    
    
    cleaned_questions = []
    for q in questions[:max_questions]:
        q = re.sub(r'^(pregunta\s*\d*[:.]?\s*)', '', q, flags=re.IGNORECASE)
        q = re.sub(r'^[\d\.\-\*\s]+', '', q) 
        q = q.strip()
        
        if len(q) > 10:
            cleaned_questions.append(q)
    
    return cleaned_questions[:max_questions]


@tool 
def process_agent_questions(agent_messages: List[Dict]) -> List[str]:
    """
    Procesa los mensajes del agente para extraer preguntas generadas.
    
    Args:
        agent_messages: Lista de mensajes del agente (agent.messages)
        
    Returns:
        Lista de preguntas extraídas de los mensajes
    """
    
    questions = []
    
    for message in agent_messages:
        if isinstance(message, dict):
            content = message.get('content', '')
            if isinstance(content, str):
                extracted = extract_questions_from_agent_analysis(content, max_questions=10)
                questions.extend(extracted)
    
    unique_questions = []
    for q in questions:
        if q not in unique_questions:
            unique_questions.append(q)
    
    return unique_questions[:4]

def manage_call_flow(questions: List[str], max_wait_minutes: int = 10) -> Dict:
    """
    Gestiona el flujo de preguntas basado en detección DTMF.
    Envía preguntas una por una cuando se detecta userResponse == '1' en los atributos de contacto.
    
    Args:
        questions: Lista de preguntas a enviar
        max_wait_minutes: Máximo tiempo de espera en minutos
        
    Returns:
        Dict con resultado del flujo
    """
    
    if not questions:
        return {"success": False, "message": "No hay preguntas para enviar"}
    
    print(f"Iniciando flujo DTMF con {len(questions)} preguntas")
    
    call_state = get_call_state()
    contact_id = call_state.get("contact_id")
    
    if not contact_id:
        return {"success": False, "message": "No se encontró contact_id activo"}
    
    questions_sent = 0
    max_wait_seconds = max_wait_minutes * 60
    start_time = time.time()    
    current_question_index = 1
    
    print(f"Tiempo máximo de espera: {max_wait_minutes} minutos")
    
    while current_question_index < len(questions) and (time.time() - start_time) < max_wait_seconds:
        try:
            attributes = get_contact_attributes(contact_id)
            current_user_response = attributes.get("userResponse")
            if current_user_response:
                if current_user_response:
                    question_to_send = questions[current_question_index]
                    print(f"Enviando pregunta {current_question_index + 1}: {question_to_send[:100]}...")
                    update_result = update_call_message(question_to_send)
                    if update_result.get("success"):
                        questions_sent += 1
                        current_question_index += 1
                        print(f"Pregunta {current_question_index} enviada exitosamente")
                        if current_question_index >= len(questions):
                            print("¡Todas las preguntas completadas! Enviando mensaje de despedida...")
                            farewell_success = send_farewell_and_hangup(
                                contact_id, 
                                "Excelente, hemos terminado con todas las preguntas. Muchas gracias por tu tiempo y por compartir tu conocimiento con nosotros. ¡Que tengas un excelente día!"
                            )
                            if farewell_success:
                                print("Despedida enviada y llamada terminada exitosamente")
                            else:
                                print("Hubo un problema con la despedida, pero todas las preguntas fueron enviadas")
                            break
                        
                        if clear_user_response(contact_id):
                            print(f"userResponse limpiado exitosamente")
                        else:
                            print(f"No se pudo limpiar userResponse")
                    else:
                        print(f"Error enviando pregunta: {update_result.get('error', 'Desconocido')}")
                
            
        except Exception as e:
            print(f"⚠️ Error en flujo DTMF: {e}")
            time.sleep(2)

    elapsed_time = time.time() - start_time
    
    if current_question_index >= len(questions):
        message = f"Entrevista completada exitosamente. Todas las preguntas enviadas ({questions_sent} enviadas) y llamada terminada con despedida"
        success = True
    elif elapsed_time >= max_wait_seconds:
        message = f"Tiempo máximo alcanzado. Enviadas {questions_sent} de {len(questions)} preguntas"
        success = False
    else:
        message = f"Flujo terminado. Enviadas {questions_sent} de {len(questions)} preguntas"
        success = questions_sent > 0
    
    print(f"🏁 {message}")
    
    return {
        "success": success,
        "message": message,
        "questions_sent": questions_sent,
        "total_questions": len(questions),
        "elapsed_minutes": round(elapsed_time / 60, 2),
    }

@tool
def get_interview_status() -> Dict:
    """
    Obtiene el estado actual de la entrevista en progreso.
    
    Returns:
        Dict con estado completo de la entrevista
    """
    
    call_state = get_call_state()
    call_status = monitor_call_status()
    
    return {
        "call_state": call_state,
        "call_status": call_status,
        "timestamp": time.time()
    }
