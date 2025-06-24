import os
import sqlite3
from googleapiclient.discovery import build
# Para OAuth, descomente as linhas abaixo:
# from google.auth.transport.requests import Request
# from google_auth_oauthlib.flow import InstalledAppFlow
# import pickle

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
# Importa as exceções de forma mais robusta
try:
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
except ImportError:
    try:
        from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound
    except ImportError:
        # Se nenhuma das abordagens funcionar, define exceções genéricas
        class TranscriptsDisabled(Exception):
            pass
        class NoTranscriptFound(Exception):
            pass

from datetime import datetime, timedelta

## Configurações
API_KEY = os.getenv("YOUTUBE_API_KEY") or "AIzaSyCxwP28gezkKP2uk9Kw6O6b9SlK7foRlqE"  # Configure sua chave de API no ambiente
# Para OAuth, descomente as linhas abaixo:
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
CLIENT_SECRETS_FILE = "credentials.json"  # Nome do arquivo JSON baixado do Google Console

MAX_RESULTS = 10  # Número máximo de vídeos a buscar (alterado para 10)
DB_NAME = "transcripts.db"

# Função alternativa para OAuth (descomente se quiser usar OAuth):
"""
def get_authenticated_service():
    credentials = None
    # O arquivo token.pickle armazena os tokens de acesso e atualização do usuário.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    
    # Se não há credenciais válidas disponíveis, deixe o usuário fazer login.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        # Salva as credenciais para a próxima execução
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)
    
    return build('youtube', 'v3', credentials=credentials)
"""

def create_database():
    """Cria o banco de dados SQLite e a tabela para armazenar transcrições."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            title TEXT NOT NULL,
            topic TEXT NOT NULL,
            transcript TEXT,
            published_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def search_youtube_videos(topic):
    """Busca vídeos no YouTube com base no assunto, limitando aos últimos 3 meses."""
    youtube = build("youtube", "v3", developerKey=API_KEY)
    
    # Calcula a data de 3 meses atrás
    three_months_ago = datetime.now() - timedelta(days=90)
    published_after = three_months_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    request = youtube.search().list(
        part="snippet",
        q=topic,
        type="video",
        maxResults=MAX_RESULTS,
        order="relevance",  # Mantém ordenação por relevância
        publishedAfter=published_after,  # Filtra por data dos últimos 3 meses
        regionCode="BR",  # Opcional: foca em conteúdo brasileiro
        relevanceLanguage="pt"  # Opcional: prioriza conteúdo em português
    )
    response = request.execute()
    videos = []
    for item in response["items"]:
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        published_date = item["snippet"]["publishedAt"]
        videos.append({
            "video_id": video_id,
            "title": title,
            "published_date": published_date
        })
    return videos

def get_transcript(video_id):
    """Obtém a transcrição de um vídeo do YouTube."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["pt", "en"])
        return " ".join([entry["text"] for entry in transcript])
    except Exception as e:
        # Captura qualquer erro relacionado à transcrição (transcrição desabilitada, não encontrada, etc.)
        print(f"Erro ao obter transcrição para vídeo {video_id}: {e}")
        return None

def save_transcript_to_db(video_id, title, topic, transcript, published_date):
    """Salva a transcrição no banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transcripts (video_id, title, topic, transcript, published_date)
        VALUES (?, ?, ?, ?, ?)
    """, (video_id, title, topic, transcript, published_date))
    conn.commit()
    conn.close()

def main(topic):
    """Função principal para buscar vídeos e salvar transcrições."""
    create_database()
    videos = search_youtube_videos(topic)
    
    for video in videos:
        video_id = video["video_id"]
        title = video["title"]
        published_date = video["published_date"]
        
        print(f"Processando vídeo: {title}")
        transcript = get_transcript(video_id)
        
        if transcript:
            save_transcript_to_db(video_id, title, topic, transcript, published_date)
            print(f"Transcrição salva para: {title}")
        else:
            print(f"Sem transcrição disponível para: {title}")

if __name__ == "__main__":
    topic = input("Digite o assunto para busca no YouTube: ")
    main(topic)