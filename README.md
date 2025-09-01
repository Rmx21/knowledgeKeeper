# KnowledgeKeeper 🧠📞

**Sistema inteligente de construcción de bases de conocimiento mediante análisis de código y entrevistas telefónicas automatizadas**

KnowledgeKeeper es una solución avanzada que combina análisis automatizado de repositorios de código con entrevistas telefónicas inteligentes para crear bases de conocimiento comprensivas sobre desarrolladores y sus contribuciones técnicas.

## 🎯 Características Principales

- **Análisis de código automatizado** via GitHub API
- **Entrevistas telefónicas automatizadas** con Amazon Connect
- **Detección DTMF inteligente** para flujo interactivo
- **Transcripción automática** con Amazon Transcribe
- **Generación de documentos** en JSON y Markdown
- **Integración con Strands Agent Framework**

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub API    │    │ Amazon Connect  │    │ Amazon Transcribe│
│   (Análisis)    │    │ (Llamadas)      │    │ (Transcripción) │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │              ┌───────▼───────┐              │
          └──────────────►│ KnowledgeKeeper│◄─────────────┘
                         │     Agent      │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │  S3 Storage   │
                         │ (Grabaciones & │
                         │  Documentos)   │
                         └───────────────┘
```

## 🔧 Servicios AWS Utilizados

### Amazon Connect
- **Propósito**: Gestión de llamadas telefónicas salientes
- **Funcionalidades**:
  - Inicio de llamadas outbound
  - Reproducción de prompts dinámicos
  - Captura de entrada DTMF del usuario
  - Control de flujo de conversación

### Amazon S3
- **Propósito**: Almacenamiento de grabaciones y documentos
- **Funcionalidades**:
  - Almacenamiento automático de grabaciones de llamadas
  - Guardado de reportes de entrevistas (JSON)
  - Almacenamiento de documentos de conocimiento (MD)

### Amazon Transcribe
- **Propósito**: Transcripción de audio a texto
- **Funcionalidades**:
  - Transcripción automática de grabaciones
  - Análisis de segmentos de audio
  - Extracción de interacciones conversacionales

## 🔐 Permisos de AWS Requeridos

### IAM Policy Mínima Requerida

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ConnectPermissions",
            "Effect": "Allow",
            "Action": [
                "connect:StartOutboundVoiceContact",
                "connect:StopContact",
                "connect:DescribeContact",
                "connect:GetContactAttributes",
                "connect:UpdateContactAttributes",
                "connect:ListInstanceStorageConfigs"
            ],
            "Resource": [
                "arn:aws:connect:*:*:instance/*",
                "arn:aws:connect:*:*:contact/*"
            ]
        },
        {
            "Sid": "S3Permissions",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::your-connect-recordings-bucket",
                "arn:aws:s3:::your-connect-recordings-bucket/*"
            ]
        },
        {
            "Sid": "TranscribePermissions",
            "Effect": "Allow",
            "Action": [
                "transcribe:StartTranscriptionJob",
                "transcribe:GetTranscriptionJob",
                "transcribe:ListTranscriptionJobs"
            ],
            "Resource": "*"
        }
    ]
}
```

### Configuración de Usuario IAM

1. **Crear usuario IAM**:
   ```bash
   aws iam create-user --user-name knowledgekeeper-user
   ```

2. **Adjuntar política**:
   ```bash
   aws iam attach-user-policy --user-name knowledgekeeper-user --policy-arn arn:aws:iam::ACCOUNT:policy/KnowledgeKeeperPolicy
   ```

3. **Generar claves de acceso**:
   ```bash
   aws iam create-access-key --user-name knowledgekeeper-user
   ```

## 📋 Prerrequisitos

### Software
- Python 3.8+
- pip (gestor de paquetes de Python)
- Cuenta de AWS con permisos apropiados
- Instancia de Amazon Connect configurada

### Cuentas y Servicios
- **AWS Account** con los servicios habilitados:
  - Amazon Connect
  - Amazon S3
  - Amazon Transcribe
- **GitHub Account** con token de acceso personal
- **Número telefónico** registrado en Amazon Connect

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd knowledgeKeeper
```

### 2. Crear entorno virtual
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Copiar `.env-demo` a `.env` y configurar:

```bash
cp .env-demo .env
```

Editar `.env`:
```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-west-2

# GitHub Configuration
GITHUB_TOKEN=your_github_token

# Amazon Connect Configuration
CONNECT_INSTANCE_ID=your_instance_id
CONTACT_FLOW_ID=your_flow_id
SOURCE_PHONE_NUMBER=+1234567890
```

## ⚙️ Configuración de Amazon Connect

### 1. Crear Contact Flow

El sistema requiere un flujo específico en Amazon Connect:

```
[Set voice] → [Set recording] → [Play prompt] → [Store customer input (DTMF)] → [Set contact attributes] → [Loop back]
```

### 2. Configuración del bloque "Store customer input"
- **Tipo**: DTMF
- **Configuración**: Text-to-speech or chat text

### 3. Configuración del bloque "Set contact attributes"
- **Namespace**: System
- **Key**: userResponse
- **Value**: Stored customer input

### 4. Configuración de S3 para grabaciones
Asegurar que la instancia de Connect tenga configurado el almacenamiento en S3 para grabaciones.

## 📚 Uso

### Modo Análisis de Código
```python
python agent.py
# Seleccionar: "Analizar repositorios y generar base de conocimiento"
```

### Modo Entrevista Telefónica
```python
python agent.py
# Seleccionar: "Conducir entrevista telefónica"
# Proporcionar: user_id, número telefónico, análisis previo
```

### Ejemplo de uso programático
```python
from interview_orchestrator import conduct_interview

result = conduct_interview(
    user_id="dev001",
    phone_number="+1234567890",
    agent_analysis="Análisis previo del desarrollador...",
    max_questions=4
)
```

## 🔄 Flujo de Entrevista

1. **Inicio**: Sistema llama al número proporcionado
2. **Introducción**: Reproduce mensaje de bienvenida
3. **Preguntas dinámicas**: Basadas en análisis de código previo
4. **Interacción DTMF**: Usuario presiona '1' para continuar
5. **Transcripción**: Audio convertido a texto automáticamente
6. **Finalización**: Mensaje de agradecimiento y colgado automático
7. **Documentación**: Generación de reportes JSON y Markdown

## 📄 Estructura de Archivos

```
knowledgeKeeper/
├── tools/
│   ├── github.py              # Integración con GitHub API
│   ├── amazon_connect_tool.py # Wrapper de Strands para Connect
│   └── connect_runtime.py     # Runtime principal de Connect
├── interview_orchestrator.py  # Orquestador de entrevistas
├── knowledge_generator.py     # Generador de documentos
├── agent.py       # Agente principal mejorado
├── requirements.txt          # Dependencias
├── .env-demo                # Plantilla de configuración
└── knowledge_output/        # Documentos generados
```

## 📊 Salidas del Sistema

### Reportes de Entrevista (JSON)
```json
{
  "user_id": "dev001",
  "timestamp": "2025-01-01T10:00:00Z",
  "contact_id": "12345",
  "questions_asked": 4,
  "transcript": "...",
  "customer_responses": [...],
  "analysis_summary": "..."
}
```

### Documentos de Conocimiento (Markdown)
- Resumen del desarrollador
- Habilidades técnicas identificadas
- Proyectos destacados
- Recomendaciones de entrevista

## 🛠️ Desarrollo y Extensión

### Agregar nuevas preguntas
Modificar `extract_questions_from_agent_analysis()` en `interview_orchestrator.py`

### Personalizar flujo de llamada
Editar `manage_call_flow()` para cambiar la lógica DTMF

### Integrar nuevos servicios
Extender el módulo `tools/` con nuevos conectores

## 🐛 Troubleshooting

### Problemas comunes

**Error: "No se encontró contact_id activo"**
- Verificar configuración de Amazon Connect
- Revisar permisos IAM
- Confirmar que el número destino es válido

**Error: "userResponse no se detecta"**
- Verificar configuración del Contact Flow
- Confirmar configuración de "Set contact attributes"
- Revisar que el bloque "Get customer input" esté en modo DTMF

**Error de transcripción**
- Verificar permisos de Amazon Transcribe
- Confirmar que las grabaciones se guardan en S3
- Revisar configuración de bucket de Connect

### Logs y debugging
El sistema incluye logging detallado en cada paso:
```
🎯 Iniciando entrevista para usuario: dev001
📞 Llamada iniciada. Contact ID: abc123
🔤 DTMF detectado: userResponse = '1'
📤 Enviando pregunta 2: ¿Cuál es tu experiencia...
```

## 📋 TODO - Mejoras Futuras

### 🚀 Optimizaciones de Performance
- [ ] **Optimizar latencia en cambio de preguntas y recepción de respuestas**
  - Reducir tiempo entre detección DTMF y reproducción de siguiente pregunta
  - Implementar cache de prompts para respuesta más rápida
  - Optimizar polling de atributos de contacto

- [ ] **Implementar detección de voz en tiempo real**
  - Eliminar necesidad de presionar teclas DTMF
  - Integración con Amazon Lex para NLU en tiempo real
  - Detección automática de fin de respuesta del usuario

### 🧠 Funcionalidades de Conocimiento
- [ ] **Sistema de consulta de base de conocimiento**
  - API para consultar conocimiento almacenado por usuario
  - Búsqueda semántica en documentos generados
  - Dashboard web para visualización de conocimientos

- [ ] **Análisis avanzado de código**
  - Integración con más plataformas (GitLab, Bitbucket)
  - Análisis de patrones de código y arquitectura
  - Detección automática de tecnologías y frameworks

### 🔄 Mejoras de Flujo
- [ ] **Flujo de entrevista adaptativo**
  - Preguntas dinámicas basadas en respuestas anteriores
  - Scoring automático de respuestas técnicas
  - Recomendaciones inteligentes de seguimiento

- [ ] **Manejo de interrupciones y errores**
  - Recuperación automática de llamadas perdidas
  - Guardado de progreso para continuar entrevistas
  - Manejo de timeouts y reconexiones

### 📊 Analytics y Reporting
- [ ] **Dashboard de métricas**
  - Estadísticas de entrevistas realizadas
  - Análisis de calidad de respuestas
  - Reportes de tendencias tecnológicas

- [ ] **Integración con CRM/ATS**
  - Exportación automática a sistemas HR
  - Sincronización con calendarios
  - Notificaciones automáticas a reclutadores

### 🔒 Seguridad y Compliance
- [ ] **Cumplimiento de regulaciones**
  - Implementación de GDPR/CCPA
  - Encriptación end-to-end de grabaciones
  - Retención configurable de datos

- [ ] **Autenticación y autorización**
  - Sistema de roles y permisos
  - Single Sign-On (SSO)
  - Audit logs completos

### 🛠️ Desarrollo y DevOps
- [ ] **Containerización**
  - Docker containers para deployment
  - Orquestación con Kubernetes
  - CI/CD pipeline automatizado

- [ ] **Monitoreo y observabilidad**
  - Métricas en tiempo real con CloudWatch
  - Alertas proactivas de errores
  - Tracing distribuido de llamadas

### 🌐 Escalabilidad
- [ ] **Arquitectura serverless**
  - Migración a AWS Lambda
  - API Gateway para endpoints
  - DynamoDB para storage escalable

- [ ] **Multi-tenancy**
  - Soporte para múltiples organizaciones
  - Aislamiento de datos por tenant
  - Configuración personalizable por cliente

### 🎯 UX/UI
- [ ] **Interfaz web administrativa**
  - Panel de control para configurar entrevistas
  - Preview de preguntas generadas
  - Gestión de contactos y números

- [ ] **Aplicación móvil para entrevistados**
  - App nativa para mejor experiencia
  - Notificaciones push
  - Feedback post-entrevista

## 🤝 Contribución

1. Fork del proyecto
2. Crear branch para feature (`git checkout -b feature/AmazingFeature`)
3. Commit de cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📞 Soporte

Para soporte técnico o preguntas:
- Crear un issue en GitHub
- Contactar al equipo de desarrollo

---

**Desarrollado durante el Hackathon de IA, DaCodes 2025 🚀**
