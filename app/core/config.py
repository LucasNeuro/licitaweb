"""
Configurações do sistema
"""

import os
from dotenv import load_dotenv

# Carrega .env do diretório raiz
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class Settings:
    """Configurações da aplicação"""
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "pncpfiles")
    
    # API
    API_TITLE: str = "🚀 PNCP Extrator Final"
    API_VERSION: str = "3.0.0"
    API_DESCRIPTION: str = """
    ## Sistema completo de extração automática de editais do PNCP
    
    ### ✨ Funcionalidades:
    - 🔍 **Busca automática** de editais mais recentes
    - 📋 **Extração completa** via APIs + Selenium
    - 💾 **Salvamento automático** no Supabase
    - 📎 **Upload de arquivos** para Storage
    - 🤖 **Scheduler configurável**
    - ⚡ **Performance otimizada** (1-2s por edital)
    
    ### 🎯 Endpoints Principais:
    1. **POST /configurar-scheduler** - Configura extração automática
    2. **POST /executar-agora** - Executa extração imediatamente  
    3. **POST /extrair-dia-anterior** - Extrai editais do dia anterior
    """
    
    # Servidor - Compatível com Render
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Selenium - Configuração para Render
    SELENIUM_HEADLESS: bool = os.getenv("SELENIUM_HEADLESS", "true").lower() == "true"
    SELENIUM_TIMEOUT: int = 30
    
    # PNCP
    PNCP_BASE_URL: str = "https://pncp.gov.br"
    PNCP_API_URL: str = "https://pncp.gov.br/api/pncp/v1"
    
    def is_configured(self) -> bool:
        """Verifica se as configurações essenciais estão definidas"""
        return bool(self.SUPABASE_URL and self.SUPABASE_KEY)

# Instância global das configurações
settings = Settings()