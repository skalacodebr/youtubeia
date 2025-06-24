import streamlit as st
import sqlite3
import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

# Configurações
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or "AIzaSyCxwP28gezkKP2uk9Kw6O6b9SlK7foRlqE"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Configure sua chave OpenAI
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # URL customizada para APIs compatíveis
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo"  # Modelo customizado
DB_NAME = "transcripts.db"
MAX_RESULTS = 10

# Configuração da página
st.set_page_config(
    page_title="YouTube AI Chat",
    page_icon="🎥",
    layout="wide"
)

# Inicializar OpenAI
openai_client = None
if OPENAI_API_KEY or OPENAI_BASE_URL:
    # Configuração para APIs OpenAI compatíveis
    client_config = {}
    
    if OPENAI_API_KEY:
        client_config["api_key"] = OPENAI_API_KEY
    else:
        # Para APIs locais que não precisam de key, usa uma dummy
        client_config["api_key"] = "dummy-key"
    
    if OPENAI_BASE_URL:
        client_config["base_url"] = OPENAI_BASE_URL
    
    openai_client = OpenAI(**client_config)

def create_openai_client(api_key: str, base_url: Optional[str] = None) -> Optional[OpenAI]:
    """Cria cliente OpenAI de forma segura."""
    try:
        if base_url:
            return OpenAI(api_key=api_key, base_url=base_url)
        else:
            return OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"Erro ao criar cliente OpenAI: {e}")
        return None

class YouTubeRAGSystem:
    def __init__(self):
        self.create_database()
        
    def create_database(self):
        """Cria o banco de dados SQLite."""
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

    def search_youtube_videos(self, topic: str) -> List[Dict]:
        """Busca vídeos no YouTube."""
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        
        three_months_ago = datetime.now() - timedelta(days=90)
        published_after = three_months_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        request = youtube.search().list(
            part="snippet",
            q=topic,
            type="video",
            maxResults=MAX_RESULTS,
            order="relevance",
            publishedAfter=published_after,
            regionCode="BR",
            relevanceLanguage="pt"
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

    def get_transcript(self, video_id: str) -> Optional[str]:
        """Obtém transcrição de um vídeo."""
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["pt", "en"])
            return " ".join([entry["text"] for entry in transcript])
        except Exception as e:
            return None

    def process_videos(self, topic: str) -> int:
        """Processa vídeos e salva transcrições."""
        videos = self.search_youtube_videos(topic)
        saved_count = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, video in enumerate(videos):
            video_id = video["video_id"]
            title = video["title"]
            published_date = video["published_date"]
            
            status_text.text(f"Processando: {title[:50]}...")
            
            # Verifica se já existe no banco
            if not self.video_exists(video_id):
                transcript = self.get_transcript(video_id)
                
                if transcript:
                    self.save_transcript(video_id, title, topic, transcript, published_date)
                    saved_count += 1
            
            progress_bar.progress((i + 1) / len(videos))
        
        status_text.text(f"Processamento concluído! {saved_count} novas transcrições salvas.")
        return saved_count

    def video_exists(self, video_id: str) -> bool:
        """Verifica se o vídeo já existe no banco."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transcripts WHERE video_id = ?", (video_id,))
        exists = cursor.fetchone()[0] > 0
        conn.close()
        return exists

    def save_transcript(self, video_id: str, title: str, topic: str, transcript: str, published_date: str):
        """Salva transcrição no banco."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transcripts (video_id, title, topic, transcript, published_date)
            VALUES (?, ?, ?, ?, ?)
        """, (video_id, title, topic, transcript, published_date))
        conn.commit()
        conn.close()

    def get_transcripts_by_topic(self, topic: str) -> List[Dict]:
        """Obtém transcrições por tópico."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT video_id, title, transcript, published_date 
            FROM transcripts 
            WHERE topic LIKE ? AND transcript IS NOT NULL
        """, (f"%{topic}%",))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "video_id": row[0],
                "title": row[1],
                "transcript": row[2],
                "published_date": row[3]
            }
            for row in results
        ]

    def find_relevant_context(self, query: str, topic: str, max_context: int = 3) -> str:
        """Encontra contexto relevante usando TF-IDF."""
        transcripts = self.get_transcripts_by_topic(topic)
        
        if not transcripts:
            return "Nenhuma transcrição encontrada para este tópico."
        
        # Prepara textos para vectorização
        documents = [t["transcript"] for t in transcripts]
        titles = [t["title"] for t in transcripts]
        
        # Se há poucos documentos, retorna todos
        if len(documents) <= max_context:
            context_parts = []
            for i, (title, doc) in enumerate(zip(titles, documents)):
                context_parts.append(f"**{title}**\n{doc[:800]}...")
            return "\n\n".join(context_parts)
        
        try:
            # Adiciona a query aos documentos
            all_docs = documents + [query.lower()]
            
            # Vectorização TF-IDF com configurações para português
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=None,  # Remove stop_words específicas
                min_df=1,
                ngram_range=(1, 2)  # Inclui bigramas
            )
            tfidf_matrix = vectorizer.fit_transform(all_docs)
            
            # Calcula similaridade entre query e documentos
            query_vec = tfidf_matrix[-1]  # Último é a query
            doc_vecs = tfidf_matrix[:-1]  # Todos exceto a query
            
            similarities = cosine_similarity(query_vec, doc_vecs).flatten()
            
            # Ordena por similaridade
            top_indices = similarities.argsort()[-max_context:][::-1]
            
            # Constrói contexto com threshold mais baixo
            context_parts = []
            for idx in top_indices:
                if similarities[idx] > 0.01:  # Threshold muito menor
                    context_parts.append(f"**{titles[idx]}**\n{documents[idx][:800]}...")
            
            # Se ainda não encontrou nada, pega os melhores mesmo assim
            if not context_parts:
                for idx in top_indices[:max_context]:
                    context_parts.append(f"**{titles[idx]}**\n{documents[idx][:800]}...")
                    
            return "\n\n".join(context_parts) if context_parts else "Erro na busca de contexto."
            
        except Exception as e:
            # Fallback: retorna os primeiros documentos
            context_parts = []
            for i, (title, doc) in enumerate(zip(titles[:max_context], documents[:max_context])):
                context_parts.append(f"**{title}**\n{doc[:800]}...")
            return "\n\n".join(context_parts)

    def chat_with_openai(self, query: str, context: str) -> str:
        """Chat com OpenAI usando contexto RAG."""
        # Usa o cliente do session_state se disponível, senão usa o global
        client = getattr(st.session_state, 'openai_client', None) or openai_client
        model = getattr(st.session_state, 'current_model', None) or OPENAI_MODEL
        
        if not client:
            return "Por favor, configure sua API OpenAI ou compatível."
        
        prompt = f"""
        Você é um assistente especializado em responder perguntas baseadas em transcrições de vídeos do YouTube.
        
        CONTEXTO (das transcrições dos vídeos):
        {context}
        
        PERGUNTA DO USUÁRIO: {query}
        
        Responda de forma útil e informativa, baseando-se principalmente no contexto fornecido. 
        Se a informação não estiver no contexto, mencione isso claramente.
        """
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em analisar conteúdo de vídeos do YouTube."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content or "Desculpe, não consegui gerar uma resposta."
        except Exception as e:
            return f"Erro ao comunicar com a API: {str(e)}"

class DeepResearchSystem:
    def __init__(self, rag_system):
        self.rag_system = rag_system
    
    def analyze_individual_video(self, video_data: Dict, research_query: str) -> Dict:
        """Analisa um vídeo individual para extrair insights específicos."""
        client = getattr(st.session_state, 'openai_client', None) or openai_client
        model = getattr(st.session_state, 'current_model', None) or OPENAI_MODEL
        
        if not client:
            return {"error": "Cliente OpenAI não configurado"}
        
        # Pega uma amostra do transcript para análise
        transcript_sample = video_data["transcript"][:3000]  # Primeiros 3000 chars
        
        analysis_prompt = f"""
        Você é um pesquisador especializado em análise de conteúdo de vídeos.
        
        VÍDEO ANALISADO: {video_data["title"]}
        
        TRANSCRIÇÃO (AMOSTRA):
        {transcript_sample}
        
        PERGUNTA DE PESQUISA: {research_query}
        
        Por favor, analise este vídeo e extraia:
        1. **INSIGHTS PRINCIPAIS**: 3-5 pontos principais relacionados à pergunta
        2. **DADOS/ESTATÍSTICAS**: Números, fatos concretos mencionados
        3. **OPINIÕES/PERSPECTIVAS**: Pontos de vista únicos do autor
        4. **EXEMPLOS PRÁTICOS**: Casos ou exemplos específicos
        5. **RELEVÂNCIA**: Como este vídeo contribui para responder a pergunta (1-10)
        
        Seja específico e objetivo. Foque apenas no que é relevante para a pergunta de pesquisa.
        """
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Você é um analista de conteúdo especializado em extrair insights de vídeos do YouTube."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=800,
                temperature=0.3  # Mais determinístico para análise
            )
            
            return {
                "video_id": video_data["video_id"],
                "title": video_data["title"],
                "analysis": response.choices[0].message.content,
                "status": "success"
            }
            
        except Exception as e:
            return {
                "video_id": video_data["video_id"],
                "title": video_data["title"],
                "error": str(e),
                "status": "error"
            }
    
    def synthesize_insights(self, analyses: List[Dict], research_query: str, output_type: str) -> str:
        """Sintetiza todos os insights em um resultado final."""
        client = getattr(st.session_state, 'openai_client', None) or openai_client
        model = getattr(st.session_state, 'current_model', None) or OPENAI_MODEL
        
        if not client:
            return "Erro: Cliente OpenAI não configurado"
        
        # Prepara o contexto com todas as análises
        context = "## ANÁLISES INDIVIDUAIS DOS VÍDEOS:\n\n"
        for i, analysis in enumerate(analyses, 1):
            if analysis["status"] == "success":
                context += f"### VÍDEO {i}: {analysis['title']}\n"
                context += f"{analysis['analysis']}\n\n"
        
        # Templates para diferentes tipos de saída
        templates = {
            "script": """
            Crie um SCRIPT DE VÍDEO profissional baseado nas análises. O script deve:
            - Ter introdução cativante
            - Desenvolver os pontos principais de forma lógica
            - Incluir dados e exemplos das análises
            - Ter transições naturais entre tópicos
            - Terminar com conclusão impactante
            - Duração estimada: 5-8 minutos
            
            Formato: [INTRODUÇÃO] [DESENVOLVIMENTO] [CONCLUSÃO]
            """,
            
            "resumo": """
            Crie um RESUMO EXECUTIVO abrangente que:
            - Sintetize os principais insights
            - Destaque consensus e divergências
            - Inclua dados e estatísticas relevantes
            - Apresente conclusões claras
            - Sugira próximos passos ou recomendações
            
            Formato: Texto corrido, bem estruturado e profissional
            """,
            
            "analise": """
            Faça uma ANÁLISE PROFUNDA que:
            - Compare diferentes perspectivas dos vídeos
            - Identifique padrões e tendências
            - Analise lacunas ou contradições
            - Avalie a qualidade das fontes
            - Forneça insights únicos baseados na síntese
            
            Formato: Análise acadêmica estruturada
            """,
            
            "artigo": """
            Escreva um ARTIGO COMPLETO que:
            - Tenha título atrativo
            - Introduza o tema de forma envolvente
            - Desenvolva argumentos com base nas análises
            - Use dados e exemplos dos vídeos
            - Inclua subtópicos bem organizados
            - Termine com reflexões finais
            
            Formato: Artigo de blog profissional
            """
        }
        
        synthesis_prompt = f"""
        Você é um pesquisador sênior especializado em síntese de informações.
        
        PERGUNTA DE PESQUISA: {research_query}
        
        TIPO DE SAÍDA SOLICITADA: {output_type.upper()}
        
        CONTEXTO COM ANÁLISES:
        {context}
        
        INSTRUÇÃO ESPECÍFICA:
        {templates.get(output_type, templates["resumo"])}
        
        Com base nas análises individuais dos vídeos, crie um {output_type} abrangente que responda à pergunta de pesquisa de forma completa e profissional. Use os insights, dados e exemplos extraídos das análises para fundamentar sua resposta.
        """
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"Você é um especialista em criar {output_type}s profissionais baseados em pesquisa de múltiplas fontes."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                max_tokens=2000,
                temperature=0.4
            )
            
            return response.choices[0].message.content or f"Erro ao gerar {output_type}"
            
        except Exception as e:
            return f"Erro na síntese: {str(e)}"
    
    def identify_research_gaps(self, analyses: List[Dict], research_query: str) -> List[str]:
        """Identifica pontos que precisam de mais aprofundamento."""
        client = getattr(st.session_state, 'openai_client', None) or openai_client
        model = getattr(st.session_state, 'current_model', None) or OPENAI_MODEL
        
        if not client:
            return []
        
        # Prepara contexto das análises
        context = "## ANÁLISES REALIZADAS:\n\n"
        for i, analysis in enumerate(analyses, 1):
            if analysis["status"] == "success":
                context += f"### VÍDEO {i}: {analysis['title']}\n"
                context += f"{analysis['analysis'][:500]}...\n\n"
        
        gap_analysis_prompt = f"""
        Você é um pesquisador especializado em identificar lacunas de conhecimento.
        
        PERGUNTA DE PESQUISA: {research_query}
        
        ANÁLISES ATUAIS:
        {context}
        
        Com base nas análises realizadas, identifique 3-5 PONTOS ESPECÍFICOS que precisam de mais aprofundamento para responder completamente à pergunta de pesquisa.
        
        Para cada ponto, forneça:
        1. **Tópico específico** (máximo 6 palavras)
        2. **Por que precisa ser aprofundado** (1 frase)
        
        Formato de resposta:
        PONTO 1: [tópico específico]
        RAZÃO: [por que precisa ser aprofundado]
        
        PONTO 2: [tópico específico]
        RAZÃO: [por que precisa ser aprofundado]
        
        Seja específico e focado em aspectos que realmente faltam na análise atual.
        """
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em identificar lacunas de pesquisa e pontos que precisam de aprofundamento."},
                    {"role": "user", "content": gap_analysis_prompt}
                ],
                max_tokens=600,
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content or ""
            
            # Extrai pontos específicos da resposta
            gaps = []
            lines = response_text.split('\n')
            current_point = None
            current_reason = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("PONTO"):
                    if current_point and current_reason:
                        gaps.append(f"{current_point} ({current_reason})")
                    # Extrai o tópico após os dois pontos
                    current_point = line.split(":", 1)[1].strip() if ":" in line else line
                    current_reason = None
                elif line.startswith("RAZÃO"):
                    current_reason = line.split(":", 1)[1].strip() if ":" in line else line
            
            # Adiciona o último ponto se existir
            if current_point and current_reason:
                gaps.append(f"{current_point} ({current_reason})")
            
            return gaps[:5]  # Máximo 5 pontos
            
        except Exception as e:
            st.warning(f"Erro ao identificar lacunas: {e}")
            return []

    def search_focused_videos(self, focus_topic: str, original_topic: str) -> List[Dict]:
        """Busca vídeos focados em um tópico específico."""
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        
        # Combina o tópico original com o foco específico
        search_query = f"{original_topic} {focus_topic}"
        
        three_months_ago = datetime.now() - timedelta(days=90)
        published_after = three_months_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        try:
            request = youtube.search().list(
                part="snippet",
                q=search_query,
                type="video",
                maxResults=5,  # Menos vídeos, mais específicos
                order="relevance",
                publishedAfter=published_after,
                regionCode="BR",
                relevanceLanguage="pt"
            )
            
            response = request.execute()
            videos = []
            
            for item in response["items"]:
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                published_date = item["snippet"]["publishedAt"]
                
                # Verifica se já temos este vídeo no banco
                if not self.rag_system.video_exists(video_id):
                    transcript = self.rag_system.get_transcript(video_id)
                    if transcript:
                        # Salva no banco
                        self.rag_system.save_transcript(video_id, title, search_query, transcript, published_date)
                        videos.append({
                            "video_id": video_id,
                            "title": title,
                            "transcript": transcript,
                            "published_date": published_date
                        })
            
            return videos
            
        except Exception as e:
            st.error(f"Erro ao buscar vídeos focados: {e}")
            return []

    def conduct_deep_research(self, topic: str, research_query: str, output_type: str) -> Dict:
        """Conduz uma pesquisa profunda completa."""
        
        # Passo 1: Obter vídeos relacionados
        st.write("### 🔍 Passo 1: Buscando vídeos relacionados...")
        transcripts = self.rag_system.get_transcripts_by_topic(topic)
        
        if not transcripts:
            return {
                "status": "error",
                "message": f"Nenhum vídeo encontrado para o tópico '{topic}'. Faça uma busca primeiro."
            }
        
        st.write(f"✅ Encontrados {len(transcripts)} vídeos para análise")
        
        # Passo 2: Análise individual de cada vídeo
        st.write("### 🧠 Passo 2: Analisando cada vídeo individualmente...")
        
        analyses = []
        progress_bar = st.progress(0)
        
        for i, video in enumerate(transcripts):
            st.write(f"🎥 Analisando: {video['title'][:60]}...")
            
            analysis = self.analyze_individual_video(video, research_query)
            analyses.append(analysis)
            
            # Mostra o progresso
            progress_bar.progress((i + 1) / len(transcripts))
            
            # Mostra resultado da análise individual
            if analysis["status"] == "success":
                with st.expander(f"📊 Análise: {video['title'][:50]}..."):
                    st.write(analysis["analysis"])
            else:
                st.warning(f"⚠️ Erro na análise: {analysis.get('error', 'Erro desconhecido')}")
        
        successful_analyses = [a for a in analyses if a["status"] == "success"]
        
        if not successful_analyses:
            return {
                "status": "error",
                "message": "Nenhuma análise foi bem-sucedida. Verifique a configuração da API."
            }
        
        # Passo 3: Identificar lacunas de pesquisa
        st.write("### 🔬 Passo 3: Identificando pontos para aprofundamento...")
        
        research_gaps = self.identify_research_gaps(successful_analyses, research_query)
        
        if research_gaps:
            st.write("🎯 **Pontos identificados que podem ser aprofundados:**")
            for i, gap in enumerate(research_gaps, 1):
                st.write(f"   {i}. {gap}")
            
            # Interface para seleção de pontos para aprofundar
            st.write("### 🤔 Deseja aprofundar algum destes pontos?")
            
            selected_gaps = []
            cols = st.columns(min(len(research_gaps), 3))
            
            for i, gap in enumerate(research_gaps):
                with cols[i % 3]:
                    gap_topic = gap.split(" (")[0]  # Remove a razão para mostrar só o tópico
                    if st.button(f"🔍 Aprofundar: {gap_topic}", key=f"gap_{i}"):
                        selected_gaps.append(gap_topic)
            
            # Se usuário selecionou pontos para aprofundar
            if selected_gaps:
                st.write("### 📚 Passo 4: Buscando conteúdo adicional...")
                
                additional_analyses = []
                for gap_topic in selected_gaps:
                    st.write(f"🎯 Buscando vídeos sobre: **{gap_topic}**")
                    
                    focused_videos = self.search_focused_videos(gap_topic, topic)
                    
                    if focused_videos:
                        st.write(f"   ✅ Encontrados {len(focused_videos)} vídeos específicos")
                        
                        for video in focused_videos:
                            analysis = self.analyze_individual_video(video, f"{research_query} - foco em {gap_topic}")
                            if analysis["status"] == "success":
                                additional_analyses.append(analysis)
                                st.write(f"   📊 Analisado: {video['title'][:50]}...")
                    else:
                        st.write(f"   ⚠️ Nenhum vídeo adicional encontrado para {gap_topic}")
                
                # Combina análises originais com as adicionais
                if additional_analyses:
                    st.write(f"✅ Adicionadas {len(additional_analyses)} análises específicas")
                    successful_analyses.extend(additional_analyses)
                
                st.write("### 🔗 Passo 5: Síntese final expandida...")
            else:
                st.write("### 🔗 Passo 4: Síntese final...")
        else:
            st.write("### 🔗 Passo 4: Síntese final...")
        
        st.write(f"✅ Sintetizando insights de {len(successful_analyses)} análises...")
        
        final_result = self.synthesize_insights(successful_analyses, research_query, output_type)
        
        return {
            "status": "success",
            "analyses_count": len(successful_analyses),
            "total_videos": len(transcripts),
            "final_result": final_result,
            "individual_analyses": successful_analyses,
            "research_gaps": research_gaps if research_gaps else []
        }

# Interface Streamlit
def main():
    st.title("🎥 YouTube AI Chat com RAG")
    st.markdown("Busque vídeos do YouTube e converse sobre o conteúdo usando IA!")
    
    rag_system = YouTubeRAGSystem()
    
    # Inicializar configurações no session_state
    if "api_configured" not in st.session_state:
        st.session_state.api_configured = bool(OPENAI_API_KEY or OPENAI_BASE_URL)
        st.session_state.api_type = "OpenAI Official" if OPENAI_API_KEY else "OpenAI Compatible"
        st.session_state.openai_client = openai_client
        st.session_state.current_model = OPENAI_MODEL
        st.session_state.current_base_url = OPENAI_BASE_URL

    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Configurações da API
        st.subheader("🤖 API Configuration")
        
        if not st.session_state.api_configured:
            st.warning("⚠️ Configure sua API OpenAI ou compatível")
            
            # Opções de configuração
            api_type = st.selectbox(
                "Tipo de API:",
                ["OpenAI Official", "OpenAI Compatible (Local/Custom)"],
                key="api_type_selector"
            )
            
            if api_type == "OpenAI Official":
                openai_key = st.text_input(
                    "OpenAI API Key", 
                    type="password",
                    key="openai_key_input"
                )
                if openai_key:
                    client = create_openai_client(openai_key)
                    if client:
                        st.session_state.openai_client = client
                        st.session_state.current_model = "gpt-3.5-turbo"
                        st.session_state.current_base_url = None
                        st.session_state.api_configured = True
                        st.session_state.api_type = "OpenAI Official"
                        st.success("✅ OpenAI configurado")
                        st.rerun()
            else:
                custom_url = st.text_input(
                    "Base URL:", 
                    placeholder="http://localhost:1234/v1/ ou https://your-api.ngrok.app/v1/",
                    key="custom_url_input"
                )
                custom_model = st.text_input(
                    "Nome do Modelo:", 
                    placeholder="huihui-ai_-_qwen2.5-7b-instruct-abliterated-v2",
                    key="custom_model_input"
                )
                custom_key = st.text_input(
                    "API Key (opcional):", 
                    type="password",
                    help="Deixe vazio se a API local não precisar de key",
                    key="custom_key_input"
                )
                
                if custom_url and custom_model:
                    api_key = custom_key if custom_key else "dummy-key"
                    client = create_openai_client(api_key, custom_url)
                    
                    if client:
                        st.session_state.openai_client = client
                        st.session_state.current_model = custom_model
                        st.session_state.current_base_url = custom_url
                        st.session_state.api_configured = True
                        st.session_state.api_type = "OpenAI Compatible"
                        st.success(f"✅ API Customizada configurada")
                        st.info(f"🔗 URL: {custom_url}")
                        st.info(f"🤖 Modelo: {custom_model}")
                        st.rerun()
        else:
            # Mostra configuração atual
            if st.session_state.api_type == "OpenAI Compatible":
                st.success("✅ API Customizada configurada")
                st.info(f"🔗 URL: {st.session_state.current_base_url}")
                st.info(f"🤖 Modelo: {st.session_state.current_model}")
            else:
                st.success("✅ OpenAI Oficial configurada")
                st.info(f"🤖 Modelo: {st.session_state.current_model}")
            
            # Botão para reconfigurar
            if st.button("🔄 Reconfigurar API"):
                st.session_state.api_configured = False
                st.session_state.openai_client = None
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Estatísticas")
        
        # Mostrar estatísticas do banco
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transcripts")
        total_transcripts = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT topic) FROM transcripts")
        total_topics = cursor.fetchone()[0]
        conn.close()
        
        st.metric("Total de Transcrições", total_transcripts)
        st.metric("Tópicos Únicos", total_topics)
    
    # Tabs para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs(["🔍 Buscar Vídeos", "💬 Chat Rápido", "🧠 Pesquisa Profunda"])
    
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.header("🔍 Buscar Vídeos")
            
            topic = st.text_input("Digite o assunto:", placeholder="Ex: inteligência artificial", key="search_topic")
            
            if st.button("🚀 Buscar e Processar", type="primary"):
                if topic:
                    with st.spinner("Buscando vídeos e processando transcrições..."):
                        saved_count = rag_system.process_videos(topic)
                    st.rerun()
                else:
                    st.warning("Por favor, digite um assunto.")
        
        with col2:
            # Mostrar vídeos processados
            if topic:
                transcripts = rag_system.get_transcripts_by_topic(topic)
                if transcripts:
                    st.subheader(f"📹 Vídeos encontrados ({len(transcripts)})")
                    for t in transcripts[:8]:  # Mostra mais vídeos
                        st.write(f"• {t['title'][:60]}...")
    
    with tab2:
        st.header("💬 Chat Rápido com IA")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Input do tópico para chat
        chat_topic = st.text_input("Tópico para conversar:", value=topic if 'topic' in locals() else "", key="chat_topic")
        
        # Mostrar histórico do chat
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Input do chat
        if prompt := st.chat_input("Faça uma pergunta sobre os vídeos..."):
            if not chat_topic:
                st.warning("Primeiro digite um tópico!")
            else:
                # Adiciona mensagem do usuário
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Busca contexto relevante
                with st.chat_message("assistant"):
                    with st.spinner("Pensando..."):
                        context = rag_system.find_relevant_context(prompt, chat_topic)
                        response = rag_system.chat_with_openai(prompt, context)
                    
                    st.markdown(response)
                    
                    # Mostra contexto usado (opcional)
                    with st.expander("📝 Ver contexto usado"):
                        st.text(context[:1000] + "..." if len(context) > 1000 else context)
                
                # Adiciona resposta do assistente
                st.session_state.messages.append({"role": "assistant", "content": response})
    
    with tab3:
        st.header("🧠 Pesquisa Profunda")
        st.markdown("*Análise sistemática que simula o processo humano de pesquisa*")
        
        deep_research = DeepResearchSystem(rag_system)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📋 Configuração da Pesquisa")
            
            research_topic = st.text_input(
                "Tópico base:", 
                value=topic if 'topic' in locals() else "",
                placeholder="Ex: inteligência artificial",
                help="O tópico dos vídeos que serão analisados",
                key="research_topic"
            )
            
            research_query = st.text_area(
                "Pergunta de pesquisa:",
                placeholder="Ex: Como a IA está impactando o mercado de trabalho? Quais são os principais riscos e benefícios?",
                help="A pergunta específica que você quer responder",
                height=100
            )
            
            output_type = st.selectbox(
                "Tipo de saída:",
                options=["resumo", "script", "analise", "artigo"],
                format_func=lambda x: {
                    "resumo": "📄 Resumo Executivo",
                    "script": "🎥 Script de Vídeo", 
                    "analise": "📊 Análise Profunda",
                    "artigo": "📝 Artigo Completo"
                }[x]
            )
        
        with col2:
            st.subheader("⚙️ Processo Inteligente")
            st.write("**1.** 🔍 Busca vídeos relacionados")
            st.write("**2.** 🧠 Analisa cada vídeo individualmente")
            st.write("**3.** 🔬 Identifica pontos para aprofundar")
            st.write("**4.** 🤔 Pergunta se quer buscar mais conteúdo")
            st.write("**5.** 📚 Busca vídeos específicos (opcional)")
            st.write("**6.** 🔗 Síntese final expandida")
            st.write("**7.** ✨ Gera conteúdo profissional")
            
            st.info("💡 **Novo**: O sistema identifica automaticamente lacunas e sugere aprofundamentos!")
            st.success("🚀 **Resultado**: Pesquisa mais completa e detalhada")
        
        if st.button("🚀 Iniciar Pesquisa Profunda", type="primary", key="deep_research_btn"):
            if not research_topic:
                st.error("❌ Por favor, digite um tópico base")
            elif not research_query:
                st.error("❌ Por favor, faça uma pergunta de pesquisa")
            else:
                st.divider()
                st.header("🔬 Processo de Pesquisa em Andamento")
                
                # Executa a pesquisa profunda
                with st.spinner("Iniciando pesquisa profunda..."):
                    result = deep_research.conduct_deep_research(
                        topic=research_topic,
                        research_query=research_query,
                        output_type=output_type
                    )
                
                if result["status"] == "success":
                    st.success(f"✅ Pesquisa concluída! Analisados {result['analyses_count']}/{result['total_videos']} vídeos")
                    
                    st.divider()
                    st.header(f"📋 Resultado Final: {output_type.title()}")
                    
                    # Mostra o resultado final
                    st.markdown(result["final_result"])
                    
                    # Botão para baixar resultado
                    st.download_button(
                        label=f"⬇️ Baixar {output_type.title()}",
                        data=result["final_result"],
                        file_name=f"{output_type}_{research_topic.replace(' ', '_')}.txt",
                        mime="text/plain"
                    )
                    
                    # Mostra estatísticas
                    with st.expander("📊 Estatísticas da Pesquisa"):
                        st.metric("Vídeos Analisados", result['analyses_count'])
                        st.metric("Total de Vídeos Encontrados", result['total_videos'])
                        st.metric("Taxa de Sucesso", f"{(result['analyses_count']/result['total_videos']*100):.1f}%")
                
                else:
                    st.error(f"❌ {result['message']}")

if __name__ == "__main__":
    main() 