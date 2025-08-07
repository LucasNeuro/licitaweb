"""
Teste COMPLETO de extração híbrida (Selenium + APIs + Arquivos)
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

# Adiciona app ao path
sys.path.append('app')

from app.core.extractor import PNCPExtractor

async def teste_completo():
    """Teste completo com todos os dados"""
    
    # ID do edital que você quer testar
    ID_TESTE = "76247329000113/2025/69"  # Testando outro edital
    
    print(f"🚀 TESTE COMPLETO HÍBRIDO: {ID_TESTE}")
    print("=" * 60)
    
    try:
        # Cria extrator
        extrator = PNCPExtractor()
        
        # Extrai dados COMPLETOS (Selenium + APIs + Arquivos)
        print("🔍 Iniciando extração COMPLETA...")
        dados = extrator.extrair_edital_completo_hibrido(ID_TESTE, salvar_arquivos=True)
        
        if dados:
            print("\n" + "="*60)
            print("✅ DADOS COMPLETOS EXTRAÍDOS:")
            print("="*60)
            
            # Dados da página (Selenium)
            print("📄 DADOS DA PÁGINA:")
            print(f"   📅 Data divulgação PNCP: {dados.get('data_divulgacao_pncp', 'N/A')}")
            print(f"   📅 Data abertura: {dados.get('data_abertura', 'N/A')}")
            print(f"   🏢 Órgão: {dados.get('orgao', 'N/A')}")
            print(f"   📋 Modalidade: {dados.get('modalidade', 'N/A')}")
            print(f"   📍 Situação: {dados.get('situacao', 'N/A')}")
            print(f"   ⚖️ Amparo legal: {dados.get('amparo_legal', 'N/A')}")
            print(f"   📄 Tipo: {dados.get('tipo', 'N/A')}")
            print(f"   🥊 Modo disputa: {dados.get('modo_disputa', 'N/A')}")
            
            # Datas importantes
            print(f"\n📅 DATAS:")
            print(f"   📅 Início propostas: {dados.get('data_inicio_propostas', 'N/A')}")
            print(f"   📅 Fim propostas: {dados.get('data_fim_propostas', 'N/A')}")
            print(f"   📅 Abertura: {dados.get('data_abertura', 'N/A')}")
            
            # Dados estruturados (APIs)
            print(f"\n📊 DADOS ESTRUTURADOS:")
            print(f"   💰 Valor total: {dados.get('valor', 'N/A')}")
            print(f"   📊 Total itens: {dados.get('total_itens', 0)}")
            print(f"   📎 Total anexos: {dados.get('total_anexos', 0)}")
            print(f"   📜 Total histórico: {dados.get('total_historico', 0)}")
            
            # Detalhes dos itens
            if dados.get('itens'):
                print(f"\n📋 ITENS:")
                for i, item in enumerate(dados['itens'][:3], 1):  # Mostra só os 3 primeiros
                    print(f"   {i}. {item.get('descricao', 'N/A')[:80]}...")
                    print(f"      💰 Valor: R$ {item.get('valorTotal', 0):,.2f}")
                if len(dados['itens']) > 3:
                    print(f"   ... e mais {len(dados['itens']) - 3} itens")
            
            # Detalhes dos anexos
            if dados.get('anexos'):
                print(f"\n📎 ANEXOS:")
                for i, anexo in enumerate(dados['anexos'][:5], 1):  # Mostra só os 5 primeiros
                    nome = anexo.get('nome', 'N/A')
                    tamanho = anexo.get('tamanho', 0)
                    status_upload = "✅ Salvo" if anexo.get('upload_sucesso') else "❌ Erro"
                    print(f"   {i}. {nome} ({tamanho} bytes) - {status_upload}")
                if len(dados['anexos']) > 5:
                    print(f"   ... e mais {len(dados['anexos']) - 5} anexos")
            
            # Histórico
            if dados.get('historico'):
                print(f"\n📜 HISTÓRICO (últimos 3):")
                for i, evento in enumerate(dados['historico'][-3:], 1):  # Últimos 3
                    data_evento = evento.get('data', 'N/A')
                    tipo_evento = evento.get('tipo', 'N/A')
                    print(f"   {i}. {data_evento} - {tipo_evento}")
            
            # Informações técnicas
            info_detalhadas = dados.get('informacoes_detalhadas', {})
            print(f"\n🔧 INFORMAÇÕES TÉCNICAS:")
            print(f"   📊 Método: {info_detalhadas.get('metodo', 'N/A')}")
            print(f"   🔗 APIs utilizadas: {info_detalhadas.get('apis_utilizadas', [])}")
            print(f"   ✅ APIs com sucesso: {info_detalhadas.get('total_apis_sucesso', 0)}/4")
            
            # Salva no banco
            print(f"\n💾 SALVANDO NO BANCO...")
            print("-" * 40)
            id_salvo = extrator.salvar_supabase(dados)
            
            if id_salvo:
                print(f"✅ SALVO COM SUCESSO!")
                print(f"🆔 ID no banco: {id_salvo}")
                print(f"📊 Total de campos salvos: {len(dados)} campos")
            else:
                print("❌ Erro ao salvar no banco")
        else:
            print("❌ Falha na extração")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(extrator, 'driver') and extrator.driver:
            extrator.driver.quit()
            print("\n🔒 Navegador fechado")

if __name__ == "__main__":
    asyncio.run(teste_completo())