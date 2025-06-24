#!/usr/bin/env python3
"""
Script para testar conexão com APIs compatíveis com OpenAI
"""
import os
from openai import OpenAI

def test_openai_compatible_api():
    """Testa conexão com API compatível"""
    print("🧪 Testando API compatível com OpenAI...")
    
    # Configuração de exemplo para ngrok
    base_url = "https://f00a89332e94.ngrok.app/v1/"
    model = "huihui-ai_-_qwen2.5-7b-instruct-abliterated-v2"
    api_key = "dummy-key"  # Muitas APIs locais não precisam de key real
    
    print(f"🔗 URL: {base_url}")
    print(f"🤖 Modelo: {model}")
    
    try:
        # Inicializa cliente
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        print("✅ Cliente OpenAI inicializado")
        
        # Testa uma requisição simples
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": "Olá! Como você está?"}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        print("✅ Requisição bem-sucedida!")
        print(f"📝 Resposta: {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_with_env_vars():
    """Testa usando variáveis de ambiente"""
    print("\n🌍 Testando com variáveis de ambiente...")
    
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    api_key = os.getenv("OPENAI_API_KEY", "dummy-key")
    
    if not base_url:
        print("⚠️ OPENAI_BASE_URL não configurada")
        return False
    
    print(f"🔗 URL: {base_url}")
    print(f"🤖 Modelo: {model}")
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Teste de conexão"}
            ],
            max_tokens=50
        )
        
        print("✅ Teste com variáveis de ambiente bem-sucedido!")
        print(f"📝 Resposta: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Teste de API Compatível com OpenAI")
    print("=" * 50)
    
    # Teste com configuração hard-coded
    success1 = test_openai_compatible_api()
    
    # Teste com variáveis de ambiente
    success2 = test_with_env_vars()
    
    print("\n" + "=" * 50)
    if success1 or success2:
        print("🎉 Pelo menos um teste foi bem-sucedido!")
        print("✅ Sua API compatível está funcionando!")
    else:
        print("❌ Ambos os testes falharam")
        print("💡 Verifique:")
        print("   - URL da API está correta")
        print("   - Servidor está rodando")
        print("   - Modelo está disponível")
        print("   - Firewall não está bloqueando") 