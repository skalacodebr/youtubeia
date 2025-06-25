# 🎥 YouTube AI Chat com RAG

Sistema inteligente que busca vídeos do YouTube, extrai transcrições e permite conversar sobre o conteúdo usando IA com Retrieval-Augmented Generation (RAG).

## 🚀 Funcionalidades

- **Busca Inteligente**: Encontra os 10 vídeos mais relevantes dos últimos 3 meses
- **Extração de Transcrições**: Coleta automaticamente legendas dos vídeos
- **Chat Rápido**: Conversa sobre o conteúdo usando IA com RAG
- **🧠 Pesquisa Profunda Iterativa**: Análise sistemática inteligente
  - Análise individual de cada vídeo
  - 🔬 **Identificação automática de lacunas**
  - 🤔 **Pergunta ao usuário sobre aprofundamentos**
  - 📚 **Busca direcionada de conteúdo específico**
  - Síntese profissional expandida
  - Scripts, resumos, análises e artigos aprimorados
- **APIs Compatíveis**: Suporte para OpenAI, LM Studio, Ollama e outros
- **Interface Web**: Interface moderna com tabs organizadas
- **🔧 Otimização 32K Tokens**: Análise inteligente para modelos limitados

## 📋 Pré-requisitos

### APIs Necessárias

1. **YouTube Data API v3**
   - Acesse: https://console.developers.google.com/
   - Crie um projeto e ative a YouTube Data API v3
   - Gere uma chave de API

2. **OpenAI API ou Compatível**
   - **OpenAI Oficial**: https://platform.openai.com/api-keys
   - **APIs Locais**: LM Studio, Ollama, ou outros servidores compatíveis
   - **APIs Customizadas**: Qualquer endpoint compatível com OpenAI API

## 🛠️ Instalação

### 1. Clone o repositório
```bash
git clone <seu-repositorio>
cd youtubeia
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

**Para OpenAI Oficial:**
```env
# YouTube Data API v3 Key
YOUTUBE_API_KEY=sua_chave_youtube_aqui

# OpenAI API Key
OPENAI_API_KEY=sua_chave_openai_aqui
```

**Para APIs Compatíveis (Local/Custom):**
```env
# YouTube Data API v3 Key
YOUTUBE_API_KEY=sua_chave_youtube_aqui

# API Compatível com OpenAI
OPENAI_BASE_URL=http://localhost:1234/v1/
OPENAI_MODEL=seu-modelo-aqui
OPENAI_API_KEY=sua_chave_se_necessaria
```

**Exemplos de APIs Compatíveis:**
- **LM Studio**: `http://localhost:1234/v1/`
- **Ollama**: `http://localhost:11434/v1/`
- **ngrok tunnel**: `https://abc123.ngrok.app/v1/`
- **Servidor customizado**: `https://sua-api.com/v1/`

## 🎯 Como Usar

### 1. Execute a aplicação
```bash
streamlit run app.py
```

### 2. Acesse a interface
- A aplicação abrirá automaticamente no navegador
- URL padrão: http://localhost:8501

### 3. Busque um assunto
- Digite um tópico de interesse (ex: "inteligência artificial")
- Clique em "🚀 Buscar e Processar"
- Aguarde o processamento das transcrições

### 4. Use as funcionalidades

**Chat Rápido:**
- Faça perguntas diretas sobre o conteúdo
- Respostas baseadas em RAG das transcrições

**🧠 Pesquisa Profunda:**
- Análise sistemática de múltiplos vídeos
- Digite uma pergunta de pesquisa específica
- Escolha o formato: Script, Resumo, Análise ou Artigo
- **🔧 Marque "Modo Otimizado" para modelos limitados (32K)**
- Acompanhe o processo em tempo real
- Baixe o resultado final

## 🔧 Configurações Avançadas

### Parâmetros Personalizáveis

No arquivo `app.py`, você pode ajustar:

```python
MAX_RESULTS = 10        # Número de vídeos por busca
DB_NAME = "transcripts.db"  # Nome do banco de dados
```

### Filtros de Busca

- **Período**: Últimos 3 meses (90 dias)
- **Região**: Brasil (regionCode="BR")
- **Idioma**: Português prioritário
- **Ordenação**: Relevância

## 📊 Arquitetura

### Componentes Principais

1. **YouTubeRAGSystem**: Classe principal que gerencia:
   - Busca de vídeos
   - Extração de transcrições
   - Sistema RAG
   - Integração com OpenAI

2. **Banco de Dados**: SQLite para armazenar:
   - Metadados dos vídeos
   - Transcrições completas
   - Histórico de buscas

3. **Sistema RAG**: 
   - TF-IDF para vetorização
   - Similaridade coseno para recuperação
   - Contexto relevante para IA

## 📁 Estrutura do Projeto

```
youtubeia/
├── app.py              # Aplicação Streamlit principal
├── teste.py            # Script original de teste
├── requirements.txt    # Dependências Python
├── README.md          # Este arquivo
├── transcripts.db     # Banco SQLite (criado automaticamente)
└── .env              # Variáveis de ambiente (criar)
```

## 🔍 Detalhes Técnicos

### RAG (Retrieval-Augmented Generation)

1. **Indexação**: Transcrições são vetorizadas usando TF-IDF
2. **Recuperação**: Busca por similaridade coseno
3. **Geração**: IA usa contexto relevante para responder

### 🧠 Pesquisa Profunda - Como Funciona

A pesquisa profunda simula o processo que um pesquisador humano faria:

**Passo 1: Coleta de Fontes**
```
Busca → Vídeos Relacionados → Validação de Relevância
```

**Passo 2: Análise Individual**
```
Para cada vídeo:
├── Extrai insights principais
├── Identifica dados/estatísticas
├── Captura opiniões/perspectivas
├── Anota exemplos práticos
└── Avalia relevância (1-10)
```

**Passo 3: Síntese Inteligente**
```
Insights Individuais → Análise Comparativa → Síntese Final
                   ↓
Templates Específicos (Script/Resumo/Análise/Artigo)
```

### 🔧 Sistema de Otimização para Modelos Limitados (32K Tokens)

**PROBLEMA COMUM:**
- Modelos locais: limitação de ~32.000 tokens
- Transcrições YouTube: 5.000 - 50.000 tokens cada
- 10 vídeos: pode passar de 200.000 tokens
- Resultado: Erro ou truncamento de conteúdo

**SOLUÇÕES IMPLEMENTADAS:**

**1. Chunking Inteligente**
```
Transcrição Longa → Chunks de 2K → Análise Separada → Síntese Final
(50K tokens)     (25 chunks)    (300 tokens cada)  (500 tokens)
```

**2. Análise Progressiva**
```
10 Análises → Lotes de 3 → Resumos → Síntese Final
(5K tokens)   (1K tokens)  (600 each)  (1.5K tokens)
```

**3. Filtragem Inteligente**
- Remove chunks sem conteúdo relevante
- Elimina redundâncias automaticamente
- Foca apenas no essencial

**RESULTADO:**
- ❌ 150K tokens → ✅ 8K tokens (94.7% economia)
- Compatível com todos os modelos locais
- Qualidade mantida alta

**QUANDO USAR:**
- ☑️ Modo Otimizado: Modelos locais (LM Studio, Ollama)
- ☑️ Modo Normal: APIs grandes (GPT-4, Claude Pro)

### Fluxo de Dados

```
Busca → YouTube API → Transcrições → Banco SQLite → RAG/Deep Research → IA
```

## 🚨 Troubleshooting

### Problemas Comuns

1. **Erro de API Key**
   - Verifique se as chaves estão corretas no `.env`
   - Confirme que as APIs estão ativas

2. **Sem transcrições**
   - Nem todos os vídeos têm legendas
   - Tente tópicos mais populares

3. **Erro de quota**
   - YouTube API tem limites diários
   - OpenAI API tem limites de tokens

### Logs e Debug

- Streamlit mostra erros no terminal
- Verifique o banco `transcripts.db` para dados salvos
- Use `st.write()` para debug durante desenvolvimento

## 💡 Dicas de Uso

1. **Tópicos Eficazes**: Use termos específicos e populares
2. **Perguntas Diretas**: Faça perguntas claras e objetivas
3. **Contexto**: Verifique sempre o contexto usado pela IA
4. **Iteração**: Refine suas perguntas baseado nas respostas

## 🔮 Próximos Passos

- [x] **Pesquisa Profunda**: Análise sistemática multi-vídeo ✅
- [x] **APIs Compatíveis**: LM Studio, Ollama, ngrok ✅
- [x] **Otimização 32K Tokens**: Chunking e análise progressiva ✅
- [ ] Suporte a mais idiomas
- [ ] Embeddings mais avançados (OpenAI Embeddings)
- [ ] Cache inteligente de análises
- [ ] Filtros de qualidade de vídeo
- [ ] Exportação de pesquisas em PDF
- [ ] Templates customizáveis
- [ ] Interface mobile
- [ ] Análise de sentimentos
- [ ] Comparação entre criadores

## 📜 Licença

Este projeto é de código aberto. Use e modifique conforme necessário.

---

**Desenvolvido com ❤️ usando Streamlit, OpenAI e YouTube API** 