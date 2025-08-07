"""
Verifica estrutura da tabela editais_completos
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def verificar_estrutura():
    """Verifica estrutura atual da tabela"""
    print("🔍 VERIFICANDO ESTRUTURA DA TABELA")
    print("=" * 50)
    
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        supabase = create_client(url, key)
        
        # Pega um registro para ver estrutura
        result = supabase.table("editais_completos").select("*").limit(1).execute()
        
        if result.data:
            colunas = list(result.data[0].keys())
            print(f"📊 COLUNAS EXISTENTES ({len(colunas)}):")
            for i, coluna in enumerate(sorted(colunas), 1):
                print(f"   {i:2d}. {coluna}")
            
            print(f"\n📋 EXEMPLO DE REGISTRO:")
            registro = result.data[0]
            for campo, valor in registro.items():
                valor_str = str(valor)[:50] if valor else "NULL"
                print(f"   {campo}: {valor_str}")
                
        else:
            print("⚠️ Tabela vazia, não é possível verificar estrutura")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    verificar_estrutura()