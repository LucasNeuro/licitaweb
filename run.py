import uvicorn
import os
from dotenv import load_dotenv

# Configura variáveis de ambiente diretamente (evita problemas de codificação)
os.environ['SUPABASE_URL'] = 'https://aomlquaeitmuqwihdnqn.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvbWxxdWFlaXRtdXF3aWhkbnFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzNDczNTUsImV4cCI6MjA2OTkyMzM1NX0.BB4j5ymmMmoavZ2SoZvrBgYY_K5rxEXh1ghPivgBOOk'
os.environ['STORAGE_BUCKET'] = 'pncpfiles'
os.environ['SELENIUM_HEADLESS'] = 'false'
os.environ['ENVIRONMENT'] = 'development'
os.environ['PORT'] = '8000'
print("OK - Configuracoes carregadas diretamente no codigo")

def main():
    # Configurações
    host = "127.0.0.1"
    port = int(os.getenv("PORT", 8000))
    
    print(" PNCP EXTRATOR FINAL")
    print("=" * 60)
    print(" SISTEMA COMPLETO DE EXTRACAO DE EDITAIS")
    print()
    print(" FUNCIONALIDADES:")
    print(f"Busca automatica de editais mais recentes")
    print(f"Extracao completa via APIs + Selenium")
    print(f"Salvamento automatico no Supabase")
    print(f"Upload de arquivos para Storage")
    print(f"Scheduler configuravel")
    print(f"Performance otimizada (-2s por edital)")
    print("=" * 60)
    print(" ENDPOINTS PRINCIPAIS:")
    print(f" Root: http://localhost:{port}/")
    print(f" Swagger: http://localhost:{port}/docs")
    print(f" Health: http://localhost:{port}/health")
    print()
    print(" EXTRACAO AUTOMATICA:")
    print(f" Configurar: POST http://localhost:{port}/configurar-scheduler")
    print(f" Executar: POST http://localhost:{port}/executar-agora")
    print(f" Dia anterior: POST http://localhost:{port}/extrair-dia-anterior")
    print("=" * 60)
    print(" COMO USAR:")
    print(f". Configure o scheduler com horario desejado")
    print(f"2. Sistema extrai TODOS os editais automaticamente")
    print(f"3. Dados salvos no Supabase + arquivos no Storage")
    print("=" * 60)
    print(f"REQUISITOS:")
    print(f"- Chrome/Chromium instalado (para Selenium)")
    print(f"- Variaveis SUPABASE_URL e SUPABASE_KEY configuradas")
    print(f"- Tabela 'editais_completos' criada no Supabase")
    print(f"- Bucket 'pncpfiles' criado no Storage")
    print("=" * 60)
    print(" Pressione Ctrl+C para parar o servidor")
    print("=" * 60)
    
    # Verifica variaveis de ambiente
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print(f"CONFIGURE AS VARIAVEIS NO .env:")
        print(f"SUPABASE_URL=sua_url_supabase")
        print(f"SUPABASE_KEY=sua_chave_supabase")
        print(f"STORAGE_BUCKET=pncpfiles")
        print()
    else:
        print(" Variaveis de ambiente configuradas")
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
        print("\n Servidor parado pelo usuário")
    except Exception as e:
        print(f" Erro ao iniciar servidor: {e}")

if __name__ == "__main__":
    main()