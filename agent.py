import os
from dotenv import load_dotenv
from strands import Agent
from strands_tools import file_read, file_write, current_time
from functions import load_history, save_history
from tools.github import list_repositories, get_commits, analyze_code
from tools.amazon_connect_tool import (
    initialize_call, 
    monitor_call_status, 
    update_call_message, 
    finalize_call,
    get_call_state
)
from interview_orchestrator import (
    conduct_interview,
    process_agent_questions,
    get_interview_status
)

load_dotenv()
os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')
os.environ['AWS_DEFAULT_REGION'] = os.getenv('AWS_REGION')
conversationId = 'phone_interview'

SYSTEM_PROMPT = """
    You are an agent that helps recover information to build a knowledge base about different actors and their participation in certain tasks, 
    in order to understand the reasoning behind their decisions.
    (Example: 
    Actor: Developer → recover knowledge about the projects they participated in, decisions made, functionalities implemented, etc. 
    Actor: Doctor → why they prescribed or diagnosed something specific, etc.).

    This knowledge can later be used to provide context to whoever needs it.

    Depending on the role, the tools to use are defined.

    For a developer, you now have TWO MODES of operation:

    MODE 1 - ANALYSIS ONLY (Traditional):
    1 - Obtain repositories with access
    2 - For each repository:
    2.1 - Check for user commits
    2.2 - Are there any? Yes
    2.2.1 - Analyze the code
    2.2.2 - Generate questions about decision-making in the project (why did you use this technology? What was the reason for this change? etc.). 
        The questions should be focused on gathering information that will help other users, for example, a new developer for onboarding, 
        for documentation, so that leaders or clients know why what was done. 
        Questions should be asked one by one; this is very important: do not ask more than one question at a time.
        Limits questions to 2 per repository (and max 2 repositories), so they should be the most important ones.
    2.2.3 - Wait for the user's response, analyze it, and if necessary, rephrase the question and provide a context for its resolution. 
        If the answer is satisfactory, move on to the next question until the analysis of user interaction in that repository is complete. 
        The first time you generate a question, it should be direct, do not add anything else, if the answer is satisfactory,
        move on to the next question under the same standard, if the answer is not satisfactory, rethink it and there will be more context.
    2.2.4 - Once the Q&A is complete:
    2.2.4.1 - A JSON file is generated with the findings, which can be used for future reference by other developers or project stakeholders.
        (Name format: "YYYYMMDD-HHMM-userId.json")
    2.2.4.2 - An MD file is generated with the summary.
        (Name format: "YYYYMMDD-HHMM-userId-summary.md")
    2.2.4.3 - Move to the next repository.
    2.3 - Are there any? No.
    2.3.1 - Move to the next repository and repeat the loop until all repositories are complete.

    MODE 2 - PHONE INTERVIEW (New Enhanced Mode):
    1 - Obtain repositories with access
    2 - For each repository:
    2.1 - Check for user commits and analyze the code
    2.2 - Generate contextual questions based on code analysis (maximum 4 questions total across all repositories)
    2.3 - Instead of asking questions via chat, use conduct_interview() to:
        2.3.1 - Automatically call the user's phone number
        2.3.2 - Conduct a real phone interview with the generated questions
        2.3.3 - Get transcribed responses automatically
        2.3.4 - Generate knowledge documents (JSON + MD) automatically
    2.4 - The phone interview will handle all the Q&A flow automatically
    2.5 - You'll receive the complete interview results with transcriptions and generated documents

    IMPORTANT INSTRUCTIONS FOR PHONE INTERVIEW MODE:
    - When you receive an instruction like "Realiza una entrevista al usuario [userId]", automatically switch to MODE 2
    - After analyzing repositories and generating questions, call conduct_interview(user_id, phone_number, analysis_text)
    - The phone interview system will handle the entire conversation flow
    - You will receive complete results including transcriptions and generated knowledge files
    - No need to ask questions manually - the phone system handles everything

    Available phone interview tools:
    - conduct_interview(): Complete phone interview with automatic question flow
    - initialize_call(): Start a phone call (used internally by conduct_interview)
    - monitor_call_status(): Check call status (used internally)
    - update_call_message(): Send new questions during call (used internally)
    - finalize_call(): End call and get transcription (used internally)
    - get_interview_status(): Get current interview status

    When creating the report, be as objective as possible.
    You don't need to notify the user about the actions you are performing behind the scenes.

    - Ask for their phone number before proceeding with phone interview if you need

    Once you finish the call, do not redial, just generate the relevant documents.
"""

previously_history = load_history(conversationId)
agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    tools=[
        list_repositories, get_commits, analyze_code, file_read, file_write, current_time,
        conduct_interview, initialize_call, monitor_call_status, update_call_message, 
        finalize_call, get_call_state, process_agent_questions, get_interview_status
    ]
)
agent.messages = previously_history

#Sustituir INGRESAR_USUARIO por un usuario que tenga acceso con el token de github
#Sustituir INGRESAR_TELEFONO por el teléfono del usuario a marcar (+525512345678)
agent("Realiza una entrevista al usuario Rmx21, su número telefónico es +525562161001")

save_history(conversationId, list(agent.messages))
