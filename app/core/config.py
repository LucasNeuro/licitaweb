"""
Configurações do sistema
"""

import os
from dotenv import load_dotenv

# As variáveis já foram configuradas no run.py
print("OK - Config.py usando variaveis do run.py")

class Settings:
    """Configurações da aplicação"""
    
    # Supabase - Valores do arquivo .env (segurança)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "pncpfiles")
    
    # API
    API_TITLE: str = "PNCP Extrator"
    API_VERSION: str = "3.0.0"
    API_DESCRIPTION: str = """Sistema de extração automática de editais do PNCP"""
    
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
    
    def validate_config(self):
        """Valida se todas as configurações obrigatórias estão presentes"""
        print(f"DEBUG - SUPABASE_URL: '{self.SUPABASE_URL}'")
        print(f"DEBUG - SUPABASE_KEY: '{self.SUPABASE_KEY[:20]}...'")
        
        if not self.SUPABASE_URL:
            raise Exception("SUPABASE_URL não configurado no arquivo .env")
        if not self.SUPABASE_KEY:
            raise Exception("SUPABASE_KEY não configurado no arquivo .env")
        print("OK - Todas as configuracoes validadas com sucesso")

# Instância global das configurações
settings = Settings()