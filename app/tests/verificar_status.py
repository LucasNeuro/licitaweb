"""
Verifica status da aplicação e scheduler
"""

import requests
import json
from datetime import datetime

def verificar_aplicacao_local():
    """Verifica se aplicação local está rodando"""
    print("🔍 VERIFICANDO APLICAÇÃO LOCAL")
    print("=" * 50)
    
    try:
        # Testa se aplicação está rodando
        response = requests.get("http://localhost:8000/", timeout=5)
        
        if response.status_code == 200:
            print("✅ Aplicação LOCAL está rodando!")
            
            # Verifica scheduler
            try:
                scheduler_response = requests.get("http://localhost:8000/debug/scheduler", timeout=5)
                if scheduler_response.status_code == 200:
                    scheduler_data = scheduler_response.json()
                    
                    print(f"📊 STATUS DO SCHEDULER:")
                    print(f"   🔄 Ativo: {scheduler_data.get('scheduler_running', False)}")
                    print(f"   ⚙️ Configurado: {scheduler_data.get('config', {}).get('ativo', False)}")
                    print(f"   ⏰ Próxima execução: {scheduler_data.get('proxima_execucao_brasil', 'N/A')}")
                    print(f"   🕐 Hora atual: {scheduler_data.get('hora_atual_brasil', 'N/A')}")
                    
                else:
                    print("⚠️ Não foi possível verificar o scheduler")
                    
            except Exception as e:
                print(f"⚠️ Erro ao verificar scheduler: {e}")
                
        else:
            print(f"❌ Aplicação local não está respondendo (Status: {response.status_code})")
            
    except requests.exceptions.ConnectionError:
        print("❌ Aplicação LOCAL não está rodando")
        print("💡 Execute: python run.py")
    except Exception as e:
        print(f"❌ Erro ao verificar aplicação local: {e}")

def verificar_aplicacao_render():
    """Verifica aplicação no Render"""
    print("\n🌐 VERIFICANDO APLICAÇÃO NO RENDER")
    print("=" * 50)
    
    # Você precisa colocar a URL do seu app no Render aqui
    render_url = "https://seu-app.onrender.com"  # MUDE AQUI
    
    try:
        response = requests.get(render_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Aplicação RENDER está rodando!")
            
            # Verifica scheduler no Render
            try:
                scheduler_response = requests.get(f"{render_url}/debug/scheduler", timeout=10)
                if scheduler_response.status_code == 200:
                    scheduler_data = scheduler_response.json()
                    
                    print(f"📊 STATUS DO SCHEDULER (RENDER):")
                    print(f"   🔄 Ativo: {scheduler_data.get('scheduler_running', False)}")
                    print(f"   ⚙️ Configurado: {scheduler_data.get('config', {}).get('ativo', False)}")
                    print(f"   ⏰ Próxima execução: {scheduler_data.get('proxima_execucao_brasil', 'N/A')}")
                    
            except Exception as e:
                print(f"⚠️ Erro ao verificar scheduler no Render: {e}")
                
        else:
            print(f"❌ Aplicação Render não está respondendo (Status: {response.status_code})")
            
    except requests.exceptions.ConnectionError:
        print("❌ Aplicação RENDER não está acessível")
        print("💡 Verifique se o deploy foi feito")
    except Exception as e:
        print(f"❌ Erro ao verificar aplicação Render: {e}")

def main():
    """Função principal"""
    print("🚀 VERIFICAÇÃO DE STATUS DAS APLICAÇÕES")
    print("=" * 60)
    print(f"⏰ Verificação em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Verifica aplicação local
    verificar_aplicacao_local()
    
    # Verifica aplicação no Render
    verificar_aplicacao_render()
    
    print("\n" + "=" * 60)
    print("📋 RESUMO:")
    print("✅ Se ambas estão rodando: Tudo funcionando!")
    print("⚠️ Se só local: Precisa fazer deploy no Render")
    print("❌ Se nenhuma: Precisa iniciar aplicações")
    print("=" * 60)

if __name__ == "__main__":
    main()