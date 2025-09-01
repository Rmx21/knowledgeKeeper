import json
import os
from datetime import datetime
from typing import Dict, List

def generate_user_knowledge_json(
    user_id: str,
    call_report: Dict,
    repositories_analyzed: List[Dict] = None
) -> Dict:
    """
    Genera JSON estructurado con los findings del usuario.
    
    Args:
        user_id: Identificador del usuario (ej: "Rmx21")
        call_report: Reporte completo de la llamada telefónica
        analysis_data: Datos del análisis de código/repositorios
        repositories_analyzed: Lista de repositorios analizados
        
    Returns:
        Dict con estructura JSON del conocimiento del usuario
    """
    
    interactions = call_report.get('transcription', {}).get('interactions', [])
    questions = []
    answers = []
    
    for interaction in interactions:
        if interaction.get('speaker') == 'system':
            content = interaction.get('content', '')
            clean_content = content.replace('responde IDD click en uno para continuar.', '').strip()
            clean_content = clean_content.replace('responde IDDA click en uno para continuar.', '').strip()
            if clean_content and not clean_content.lower().startswith('es un buen momento'):
                questions.append(clean_content)
        elif interaction.get('speaker') == 'user':
            answers.append(interaction.get('content', ''))
    
    qa_pairs = []
    for i, question in enumerate(questions):
        answer = answers[i] if i < len(answers) else "No respondió"
        qa_pairs.append({
            "question": question,
            "answer": answer,
            "sequence": i + 1
        })
    
    knowledge_json = {
        "user_profile": {
            "user_id": user_id,
            "interview_date": call_report.get('call_metadata', {}).get('timestamp', ''),
            "phone_number": call_report.get('call_metadata', {}).get('phone_number', ''),
            "language": call_report.get('call_metadata', {}).get('language', 'es')
        },
        "interview_session": {
            "contact_id": call_report.get('call_metadata', {}).get('contact_id', ''),
            "total_interactions": len(interactions),
            "questions_asked": len(questions),
            "responses_received": len(answers)
        },
        "knowledge_extraction": {
            "qa_pairs": qa_pairs,
            "key_insights": _extract_key_insights(qa_pairs),
            "technical_skills": _extract_technical_skills(qa_pairs),
            "experience_areas": _extract_experience_areas(qa_pairs)
        },
        "repository_analysis": repositories_analyzed or [],
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "source": "knowledge_keeper_interview"
        }
    }
    
    return knowledge_json

def generate_user_summary_md(
    user_id: str,
    knowledge_json: Dict
) -> str:   
    user_profile = knowledge_json.get('user_profile', {})
    interview_session = knowledge_json.get('interview_session', {})
    knowledge_extraction = knowledge_json.get('knowledge_extraction', {})
    interview_date = user_profile.get('interview_date', '')
    if interview_date:
        try:
            date_obj = datetime.fromisoformat(interview_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime('%d de %B de %Y a las %H:%M UTC')
        except:
            formatted_date = interview_date
    else:
        formatted_date = "Fecha no disponible"
    
    markdown_content = f"""# Resumen de Conocimiento - {user_id}

## 📋 Información General
- **Usuario:** {user_id}
- **Fecha de entrevista:** {formatted_date}
- **Teléfono:** {user_profile.get('phone_number', 'No disponible')}
- **Idioma:** {user_profile.get('language', 'es')}

## 📞 Detalles de la Sesión
- **ID de contacto:** {interview_session.get('contact_id', 'N/A')}
- **Total de interacciones:** {interview_session.get('total_interactions', 0)}
- **Preguntas realizadas:** {interview_session.get('questions_asked', 0)}
- **Respuestas recibidas:** {interview_session.get('responses_received', 0)}

## 💬 Preguntas y Respuestas

"""
    qa_pairs = knowledge_extraction.get('qa_pairs', [])
    for qa in qa_pairs:
        markdown_content += f"""### {qa.get('sequence', 0)}. {qa.get('question', 'Pregunta no disponible')} **Respuesta:** {qa.get('answer', 'No respondió')}"""

    key_insights = knowledge_extraction.get('key_insights', [])
    if key_insights:
        markdown_content += """## 🔍 Insights Clave"""
        for insight in key_insights:
            markdown_content += f"- {insight}\n"
        markdown_content += "\n"
    
    technical_skills = knowledge_extraction.get('technical_skills', [])
    if technical_skills:
        markdown_content += """## 🛠️ Habilidades Técnicas Identificadas"""
        for skill in technical_skills:
            markdown_content += f"- {skill}\n"
        markdown_content += "\n"
    
    experience_areas = knowledge_extraction.get('experience_areas', [])
    if experience_areas:
        markdown_content += """## 🎯 Áreas de Experiencia"""
        for area in experience_areas:
            markdown_content += f"- {area}\n"
        markdown_content += "\n"
    
    repositories = knowledge_json.get('repository_analysis', [])
    if repositories:
        markdown_content += """## 📁 Repositorios Analizados"""
        for repo in repositories:
            repo_name = repo.get('name', 'Repositorio desconocido')
            commits = repo.get('commits_count', 0)
            markdown_content += f"- **{repo_name}** - {commits} commits analizados\n"
        markdown_content += "\n"
    
    markdown_content += f"""---*Generado automáticamente por Knowledge Keeper el {formatted_date}*"""
    
    return markdown_content

def save_user_documents(
    user_id: str,
    knowledge_json: Dict,
    summary_md: str,
    output_dir: str = "knowledge_output"
) -> Dict:

    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    json_filename = f"{timestamp}-{user_id}.json"
    md_filename = f"{timestamp}-{user_id}-summary.md"
    
    json_path = os.path.join(output_dir, json_filename)
    md_path = os.path.join(output_dir, md_filename)
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge_json, f, indent=2, ensure_ascii=False)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(summary_md)
        
        return {
            "success": True,
            "json_file": json_path,
            "md_file": md_path,
            "message": f"Documentos guardados para usuario {user_id}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error guardando documentos para {user_id}"
        }

def _extract_key_insights(qa_pairs: List[Dict]) -> List[str]:
    """Extrae insights clave de las respuestas del usuario."""
    insights = []
    
    for qa in qa_pairs:
        answer = qa.get('answer', '').lower()
        if 'python' in answer or 'aws' in answer:
            if 'experiencia' in answer:
                insights.append("Tiene experiencia con Python y/o AWS")
        if 'proyecto' in answer or 'desarrollé' in answer or 'implementé' in answer:
            insights.append("Ha participado en desarrollo de proyectos")
        tools = ['docker', 'kubernetes', 'terraform', 'jenkins', 'git']
        mentioned_tools = [tool for tool in tools if tool in answer]
        if mentioned_tools:
            insights.append(f"Experiencia con herramientas: {', '.join(mentioned_tools)}")
    
    return list(set(insights))  # Remover duplicados

def _extract_technical_skills(qa_pairs: List[Dict]) -> List[str]:
    """Extrae habilidades técnicas mencionadas."""
    skills = []
    for qa in qa_pairs:
        answer = qa.get('answer', '').lower()
        technologies = [
            'python', 'javascript', 'java', 'c++', 'c#', 'go', 'rust',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
            'react', 'vue', 'angular', 'django', 'flask', 'fastapi',
            'mysql', 'postgresql', 'mongodb', 'redis'
        ]
        for tech in technologies:
            if tech in answer:
                skills.append(tech.upper() if tech in ['aws', 'gcp'] else tech.capitalize())
    
    return list(set(skills))

def _extract_experience_areas(qa_pairs: List[Dict]) -> List[str]:
    """Extrae áreas de experiencia del usuario."""
    areas = []
    for qa in qa_pairs:
        answer = qa.get('answer', '').lower()
        if 'backend' in answer or 'api' in answer:
            areas.append("Desarrollo Backend")
        if 'frontend' in answer or 'ui' in answer or 'interfaz' in answer:
            areas.append("Desarrollo Frontend")
        if 'devops' in answer or 'infraestructura' in answer:
            areas.append("DevOps e Infraestructura")
        if 'base de datos' in answer or 'database' in answer:
            areas.append("Gestión de Bases de Datos")
        if 'machine learning' in answer or 'ia' in answer or 'inteligencia artificial' in answer:
            areas.append("Inteligencia Artificial/ML")
    
    return list(set(areas))
