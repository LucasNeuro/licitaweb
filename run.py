#!/usr/bin/env python3
"""
🚀 PNCP Extrator Final
Sistema completo de extração automática de editais do PNCP
"""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    # Configurações
    host = "127.0.0.1"
    port = int(os.getenv("PORT", 8000))
    
    print("🚀 PNCP EXTRATOR FINAL")
    print("=" * 60)
    print("🎯 SISTEMA COMPLETO DE EXTRAÇÃO DE EDITAIS")
    print()
    print("✨ FUNCIONALIDADES:")
    print("   🔍 Busca automática de editais mais recentes")
    print("   📋 Extração completa via APIs + Selenium")
    print("   💾 Salvamento automático no Supabase")
    print("   📎 Upload de arquivos para Storage")
    print("   🤖 Scheduler configurável")
    print("   ⚡ Performance otimizada (1-2s por edital)")
    print("=" * 60)
    print("📋 ENDPOINTS PRINCIPAIS:")
    print(f"   🏠 Root: http://localhost:{port}/")
    print(f"   📚 Swagger: http://localhost:{port}/docs")
    print(f"   🏥 Health: http://localhost:{port}/health")
    print()
    print("🤖 EXTRAÇÃO AUTOMÁTICA:")
    print(f"   ⚙️ Configurar: POST http://localhost:{port}/configurar-scheduler")
    print(f"   ▶️ Executar: POST http://localhost:{port}/executar-agora")
    print(f"   📅 Dia anterior: POST http://localhost:{port}/extrair-dia-anterior")
    print("=" * 60)
    print("💡 COMO USAR:")
    print("   1. Configure o scheduler com horário desejado")
    print("   2. Sistema extrai TODOS os editais automaticamente")
    print("   3. Dados salvos no Supabase + arquivos no Storage")
    print("=" * 60)
    print("⚠️  REQUISITOS:")
    print("   - Chrome/Chromium instalado (para Selenium)")
    print("   - Variáveis SUPABASE_URL e SUPABASE_KEY configuradas")
    print("   - Tabela 'editais_completos' criada no Supabase")
    print("   - Bucket 'pncpfiles' criado no Storage")
    print("=" * 60)
    print("💡 Pressione Ctrl+C para parar o servidor")
    print("=" * 60)
    
    # Verifica variáveis de ambiente
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("⚠️  CONFIGURE AS VARIÁVEIS NO .env:")
        print("   SUPABASE_URL=sua_url_supabase")
        print("   SUPABASE_KEY=sua_chave_supabase")
        print("   STORAGE_BUCKET=pncpfiles")
        print()
    else:
        print("✅ Variáveis de ambiente configuradas")
        print()
    
    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Servidor parado pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")

if __name__ == "__main__":
    main()