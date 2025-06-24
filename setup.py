#!/usr/bin/env python3
"""
Script de setup para YouTube AI Chat
Facilita a instalação e configuração inicial do projeto.
"""
import os
import subprocess
import sys

def install_requirements():
    """Instala as dependências do requirements.txt"""
    print("📦 Instalando dependências...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--break-system-packages"])
        print("✅ Dependências instaladas com sucesso!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Erro ao instalar dependências!")
        return False

def create_env_file():
    """Cria o arquivo .env se não existir"""
    env_path = ".env"
    
    if os.path.exists(env_path):
        print("⚠️ Arquivo .env já existe!")
        return True
    
    print("📝 Criando arquivo .env...")
    
    youtube_key = input("Digite sua YouTube API Key: ").strip()
    openai_key = input("Digite sua OpenAI API Key: ").strip()
    
    env_content = f"""# YouTube Data API v3 Key
# Obtenha em: https://console.developers.google.com/
YOUTUBE_API_KEY={youtube_key}

# OpenAI API Key  
# Obtenha em: https://platform.openai.com/api-keys
OPENAI_API_KEY={openai_key}
"""
    
    try:
        with open(env_path, "w") as f:
            f.write(env_content)
        print("✅ Arquivo .env criado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar arquivo .env: {e}")
        return False

def check_api_keys():
    """Verifica se as API keys estão configuradas"""
    print("🔑 Verificando configuração das APIs...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    youtube_key = os.getenv("YOUTUBE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not youtube_key or youtube_key == "your_youtube_api_key_here":
        print("❌ YouTube API Key não configurada!")
        return False
    
    if not openai_key or openai_key == "your_openai_api_key_here":
        print("❌ OpenAI API Key não configurada!")
        return False
    
    print("✅ APIs configuradas corretamente!")
    return True

def run_app():
    """Executa a aplicação Streamlit"""
    print("🚀 Iniciando YouTube AI Chat...")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Aplicação encerrada!")
    except Exception as e:
        print(f"❌ Erro ao executar aplicação: {e}")

def main():
    """Função principal do setup"""
    print("🎥 YouTube AI Chat - Setup")
    print("=" * 40)
    
    # 1. Instalar dependências
    if not install_requirements():
        return
    
    # 2. Configurar .env
    if not os.path.exists(".env"):
        if not create_env_file():
            return
    
    # 3. Verificar APIs
    try:
        if not check_api_keys():
            print("\n⚠️ Configure suas API keys no arquivo .env antes de continuar!")
            return
    except ImportError:
        print("⚠️ Execute novamente após instalar as dependências!")
        return
    
    # 4. Pergunta se quer executar
    print("\n🎯 Setup concluído!")
    run_now = input("Deseja executar a aplicação agora? (s/n): ").lower().strip()
    
    if run_now in ['s', 'sim', 'y', 'yes']:
        run_app()
    else:
        print("\n📖 Para executar posteriormente, use: streamlit run app.py")
        print("📚 Consulte o README.md para mais informações!")

if __name__ == "__main__":
    main() 