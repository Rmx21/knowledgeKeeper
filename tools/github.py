import requests
import os
import base64
import json
from pydantic import BaseModel, Field
from strands.tools import tool
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

class ContributorInfo(BaseModel):
    login: str = Field(description="Nombre de usuario del contribuidor")
    html_url: str = Field(description="URL del perfil del contribuidor")
    contributions: int = Field(description="Número de contribuciones")
    avatar_url: str = Field(description="URL del avatar del contribuidor")

class ListRepositoriesInput(BaseModel):
    include_private: bool = Field(default=True, description="Incluir repositorios privados")
    per_page: int = Field(default=50, description="Número de repositorios por página")

class CommitInfo(BaseModel):
    sha: str = Field(description="Hash SHA del commit")
    message: str = Field(description="Mensaje del commit")
    author: str = Field(description="Autor del commit")
    date: str = Field(description="Fecha del commit")
    url: str = Field(description="URL del commit")

class GetCommitsInput(BaseModel):
    repo_name: str = Field(description="Nombre del repositorio en formato 'owner/repo'")
    per_page: int = Field(default=10, description="Número de commits a obtener")

class GetCommitsOutput(BaseModel):
    commits: list[CommitInfo] = Field(description="Lista de commits del repositorio")
    total_commits: int = Field(description="Número total de commits analizados")

class LanguageInfo(BaseModel):
    language: str = Field(description="Nombre del lenguaje")
    percentage: float = Field(description="Porcentaje del código total")

class FileInfo(BaseModel):
    name: str = Field(description="Nombre del archivo o directorio")
    type: str = Field(description="Tipo: 'file' o 'dir'")
    size: int = Field(default=0, description="Tamaño en bytes de archivos")

class RepositoryAnalysis(BaseModel):
    name: str = Field(description="Nombre del repositorio")
    full_name: str = Field(description="Nombre completo del repositorio")
    description: str = Field(default="", description="Descripción del repositorio")
    is_private: bool = Field(description="Si el repositorio es privado")
    size_kb: int = Field(description="Tamaño del repositorio en KB")
    primary_language: str = Field(default="", description="Lenguaje principal")
    created_at: str = Field(description="Fecha de creación")
    updated_at: str = Field(description="Fecha de última actualización")
    languages: list[LanguageInfo] = Field(description="Análisis de lenguajes")
    root_files: list[FileInfo] = Field(description="Archivos y directorios en la raíz")
    recent_commits: list[CommitInfo] = Field(description="Commits recientes")
    contributors: list[ContributorInfo] = Field(description="Lista de contribuidores")
    readme_content: str = Field(default="", description="Contenido del README si existe")
    package_info: dict = Field(default={}, description="Información del package.json si existe")

class AnalyzeCodeInput(BaseModel):
    repo_name: str = Field(description="Nombre del repositorio en formato 'owner/repo'")

class RepoInfo(BaseModel):
    name: str = Field(description="Nombre del repositorio")
    full_name: str = Field(description="Nombre completo del repositorio (owner/repo)")
    html_url: str = Field(description="URL del repositorio en GitHub")
    description: str | None = Field(description="Descripción del repositorio")
    language: str | None = Field(description="Lenguaje principal del repositorio")
    private: bool = Field(description="Indica si el repositorio es privado")

class ListReposOutput(BaseModel):
    repos: list[RepoInfo] = Field(description="Lista de repositorios encontrados")

def _get_auth_headers():
    """Obtiene headers de autenticación si está disponible el token."""
    if GITHUB_TOKEN:
        return {"Authorization": f"token {GITHUB_TOKEN}"}
    return {}

@tool
def list_repositories(input: ListRepositoriesInput) -> ListReposOutput:
    """
    Obtiene la lista de repositorios a los que tienes acceso con tu token de GitHub.
    
    Args:
        input: Configuración para incluir repositorios privados y paginación
        
    Returns:
        Lista de repositorios accesibles
    """
    if isinstance(input, dict):
        input = ListRepositoriesInput(**input)
    elif not isinstance(input, ListRepositoriesInput):
        input = ListRepositoriesInput()
    if not GITHUB_TOKEN:
        print("❌ No se encontró token de GitHub")
        return ListReposOutput(repos=[])
    headers = _get_auth_headers()
    print(f"Obteniendo repositorios...")
    try:
        url = "https://api.github.com/user/repos"
        params = { "per_page": input.per_page, "sort": "updated", "type": "all" if input.include_private else "public" }
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        repos = [
            RepoInfo(
                name=item["name"],
                full_name=item["full_name"],
                html_url=item["html_url"],
                description=item.get("description"),
                language=item.get("language"),
                private=item.get("private", False),
            )
            for item in data
        ]
        
        print(f"Encontrados {len(repos)} repositorios accesibles")
        return ListReposOutput(repos=repos)
        
    except Exception as e:
        print(f"Error obteniendo repositorios: {e}")
        return ListReposOutput(repos=[])


@tool
def get_commits(input: GetCommitsInput) -> GetCommitsOutput:
    """
    Obtiene los commits de un repositorio específico.
    
    Args:
        input: Configuración con el nombre del repositorio y número de commits
        
    Returns:
        Lista de commits con información detallada
    """
    if isinstance(input, dict):
        input = GetCommitsInput(**input)
    elif isinstance(input, str):
        input = GetCommitsInput(repo_name=input)
    if not GITHUB_TOKEN:
        print("No se encontró token de GitHub")
        return GetCommitsOutput(commits=[], total_commits=0)
    headers = _get_auth_headers()
    print(f"Obteniendo commits de {input.repo_name}...")
    try:
        commits_url = f"https://api.github.com/repos/{input.repo_name}/commits"
        params = {"per_page": input.per_page}
        response = requests.get(commits_url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            print(f"Error accediendo al repositorio: {response.status_code}")
            return GetCommitsOutput(commits=[], total_commits=0)
        commits_data = response.json()
        commits = []
        for commit in commits_data:
            commit_info = CommitInfo(
                sha=commit['sha'][:8],
                message=commit['commit']['message'].split('\n')[0],
                author=commit['commit']['author']['name'],
                date=commit['commit']['author']['date'].split('T')[0],
                url=commit['html_url']
            )
            commits.append(commit_info)
        print(f"Encontrados {len(commits)} commits en {input.repo_name}")
        return GetCommitsOutput(commits=commits, total_commits=len(commits))
    except Exception as e:
        print(f"Error obteniendo commits: {e}")
        return GetCommitsOutput(commits=[], total_commits=0)


@tool
def analyze_code(input: AnalyzeCodeInput) -> RepositoryAnalysis:
    """
    Realiza un análisis completo del código de un repositorio específico.
    
    Args:
        input: Configuración con el nombre del repositorio a analizar
        
    Returns:
        Análisis completo del repositorio incluyendo estructura, lenguajes, commits y colaboradores
    """
    if isinstance(input, dict):
        input = AnalyzeCodeInput(**input)
    elif isinstance(input, str):
        input = AnalyzeCodeInput(repo_name=input)
    
    if not GITHUB_TOKEN:
        print("No se encontró token de GitHub")
        return None
    headers = _get_auth_headers()
    repo_name = input.repo_name
    print(f"Analizando repositorio: {repo_name}")
    try:
        repo_url = f"https://api.github.com/repos/{repo_name}"
        repo_response = requests.get(repo_url, headers=headers, timeout=10)
        if repo_response.status_code != 200:
            print(f"❌ Error accediendo al repositorio: {repo_response.status_code}")
            return None
        repo_data = repo_response.json()
        basic_info = {
            "name": repo_data.get('name', ''),
            "full_name": repo_data.get('full_name', ''),
            "description": repo_data.get('description') or '',
            "is_private": repo_data.get('private', False),
            "size_kb": repo_data.get('size', 0),
            "primary_language": repo_data.get('language') or '',
            "created_at": repo_data.get('created_at', '').split('T')[0],
            "updated_at": repo_data.get('updated_at', '').split('T')[0]
        }
    except Exception as e:
        print(f"❌ Error obteniendo información básica: {e}")
        return None
    
    # 2. Análisis de lenguajes
    languages = []
    try:
        languages_url = f"https://api.github.com/repos/{repo_name}/languages"
        languages_response = requests.get(languages_url, headers=headers, timeout=10)
        if languages_response.status_code == 200:
            languages_data = languages_response.json()
            if languages_data:
                total_bytes = sum(languages_data.values())
                for language, bytes_count in sorted(languages_data.items(), key=lambda x: x[1], reverse=True):
                    percentage = (bytes_count / total_bytes) * 100
                    languages.append(LanguageInfo(
                        language=language,
                        bytes_count=bytes_count,
                        percentage=round(percentage, 1)
                    ))
    except Exception as e:
        print(f"Error analizando lenguajes: {e}")
    
    # 3. Estructura de archivos en la raíz
    root_files = []
    try:
        contents_url = f"https://api.github.com/repos/{repo_name}/contents"
        contents_response = requests.get(contents_url, headers=headers, timeout=10)
        if contents_response.status_code == 200:
            contents_data = contents_response.json()
            for item in contents_data:
                root_files.append(FileInfo(
                    name=item['name'],
                    type=item['type'],
                    size=item.get('size', 0)
                ))
    except Exception as e:
        print(f"Error analizando estructura: {e}")

    # 4. Commits recientes
    recent_commits = []
    try:
        commits_url = f"https://api.github.com/repos/{repo_name}/commits"
        commits_response = requests.get(commits_url, headers=headers, params={"per_page": 5}, timeout=10)
        if commits_response.status_code == 200:
            commits_data = commits_response.json()
            for commit in commits_data[:5]:
                recent_commits.append(CommitInfo(
                    sha=commit['sha'][:8],
                    message=commit['commit']['message'].split('\n')[0],
                    author=commit['commit']['author']['name'],
                    date=commit['commit']['author']['date'].split('T')[0],
                    url=commit['html_url']
                ))
    except Exception as e:
        print(f"Error obteniendo commits: {e}")

    # 5. Colaboradores
    contributors = []
    try:
        contributors_url = f"https://api.github.com/repos/{repo_name}/contributors"
        contributors_response = requests.get(contributors_url, headers=headers, timeout=10)
        if contributors_response.status_code == 200:
            contributors_data = contributors_response.json()
            for contributor in contributors_data[:10]:
                contributors.append(ContributorInfo(
                    login=contributor['login'],
                    html_url=contributor['html_url'],
                    contributions=contributor['contributions'],
                    avatar_url=contributor['avatar_url']
                ))
    except Exception as e:
        print(f"Error obteniendo colaboradores: {e}")

    # 6. Análisis de README y package.json
    readme_content = ""
    package_info = {}
    try:
        readme_files = ['README.md', 'README.txt', 'README', 'package.json']
        for file_name in readme_files:
            file_url = f"https://api.github.com/repos/{repo_name}/contents/{file_name}"
            file_response = requests.get(file_url, headers=headers, timeout=10)
            if file_response.status_code == 200:
                file_data = file_response.json()
                if file_data.get('encoding') == 'base64':
                    content = base64.b64decode(file_data['content']).decode('utf-8')
                    if file_name == 'package.json':
                        try:
                            package_info = json.loads(content)
                        except:
                            pass
                    elif file_name.startswith('README'):
                        readme_content = content[:1000]
                        break
    except Exception as e:
        print(f"Error analizando archivos específicos: {e}")

    # Crear el análisis completo
    analysis = RepositoryAnalysis(
        **basic_info,
        languages=languages,
        root_files=root_files,
        recent_commits=recent_commits,
        contributors=contributors,
        readme_content=readme_content,
        package_info=package_info
    )
    
    print(f"✅ Análisis completo de {repo_name} terminado")
    return analysis

