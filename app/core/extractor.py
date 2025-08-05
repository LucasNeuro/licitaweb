"""
Extrator principal do PNCP
"""

import os
import json
import time
import requests
import re
import asyncio
from datetime import datetime, timedelta, date
from supabase import create_client, Client
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

from .config import settings


class PNCPExtractor:
    """Extrator principal de editais do PNCP"""
    
    def __init__(self):
        # Supabase
        if not settings.is_configured():
            raise Exception("Configure SUPABASE_URL e SUPABASE_KEY no .env")
        
        self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.bucket_name = settings.STORAGE_BUCKET
        
        # Session para APIs
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Selenium
        self.driver = None
        
        # URLs
        self.url_base = f"{settings.PNCP_BASE_URL}/app/editais"
    
    def configurar_selenium(self):
        """Configura Selenium otimizado para Render"""
        chrome_options = Options()
        
        if settings.SELENIUM_HEADLESS:
            chrome_options.add_argument("--headless")
        
        # Configurações específicas para Render
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            print(f"❌ Erro ao configurar Selenium: {e}")
            return False
    
    def buscar_editais_recentes(self, data_filtro=None, max_paginas=3, limit_por_pagina=50):
        """Busca editais mais recentes do PNCP com limites otimizados"""
        if not data_filtro:
            data_filtro = (datetime.now() - timedelta(days=1)).date()
        
        print(f"🔍 Buscando editais mais recentes da data: {data_filtro}")
        print(f"📊 Configuração: {max_paginas} páginas x {limit_por_pagina} editais = máximo {max_paginas * limit_por_pagina} editais")
        
        if not self.configurar_selenium():
            return []
        
        editais_encontrados = []
        
        try:
            for pagina in range(1, max_paginas + 1):
                url_pagina = f"{self.url_base}?q=&pagina={pagina}&tam_pagina={limit_por_pagina}"
                
                print(f"   📄 Página {pagina}: {url_pagina}")
                
                self.driver.get(url_pagina)
                time.sleep(2)
                
                try:
                    time.sleep(1)
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    containers = soup.find_all("a", class_="br-item")
                    
                    if not containers:
                        print(f"   ❌ Nenhum container encontrado na página {pagina}")
                        break
                    
                    print(f"   📋 Encontrados {len(containers)} editais na página {pagina}")
                    
                    editais_pagina = []
                    data_mais_antiga_pagina = None
                    
                    for container in containers:
                        try:
                            edital_data = self.extrair_dados_container(container)
                            if edital_data:
                                try:
                                    # Tenta diferentes formatos de data
                                    data_str = edital_data['ultima_atualizacao']
                                    data_edital = None
                                    
                                    if data_str:
                                        # Tenta formato DD/MM/YYYY
                                        try:
                                            data_edital = datetime.strptime(data_str, "%d/%m/%Y").date()
                                        except ValueError:
                                            # Tenta formato DD-MM-YYYY
                                            try:
                                                data_edital = datetime.strptime(data_str, "%d-%m-%Y").date()
                                            except ValueError:
                                                # Tenta formato YYYY-MM-DD
                                                try:
                                                    data_edital = datetime.strptime(data_str, "%Y-%m-%d").date()
                                                except ValueError:
                                                    print(f"     ⚠️ {edital_data['id_pncp']} - formato de data não reconhecido: '{data_str}'")
                                    
                                    if data_edital:
                                        if not data_mais_antiga_pagina or data_edital < data_mais_antiga_pagina:
                                            data_mais_antiga_pagina = data_edital
                                        
                                        if data_edital >= data_filtro:
                                            editais_pagina.append(edital_data)
                                            print(f"     ✅ {edital_data['id_pncp']} - {data_edital}")
                                        else:
                                            print(f"     ⏭️ {edital_data['id_pncp']} - data muito antiga: {data_edital}")
                                    else:
                                        # Se não conseguiu converter a data, inclui mesmo assim
                                        editais_pagina.append(edital_data)
                                        print(f"     ⚠️ {edital_data['id_pncp']} - data inválida: '{data_str}'")
                                
                                except Exception as e:
                                    print(f"     ❌ Erro ao processar data: {e}")
                                    editais_pagina.append(edital_data)
                        
                        except Exception as e:
                            print(f"     ❌ Erro ao processar container: {e}")
                            continue
                    
                    editais_encontrados.extend(editais_pagina)
                    print(f"   ✅ {len(editais_pagina)} editais válidos na página {pagina}")
                    
                    # Para se encontrou muitos editais ou data muito antiga
                    if len(editais_encontrados) >= 100:
                        print(f"   🛑 Limite de 100 editais atingido, parando busca")
                        break
                    
                    if data_mais_antiga_pagina and data_mais_antiga_pagina < data_filtro:
                        print(f"   🛑 Data mais antiga da página ({data_mais_antiga_pagina}) é anterior ao filtro, parando")
                        break
                
                except Exception as e:
                    print(f"   ❌ Erro ao processar página {pagina}: {e}")
                    break
            
        finally:
            if self.driver:
                self.driver.quit()
        
        print(f"🎯 Total de editais encontrados: {len(editais_encontrados)}")
        return editais_encontrados
    
    def normalizar_data(self, data_str):
        """Normaliza diferentes formatos de data"""
        if not data_str:
            return ""
        
        # Remove espaços extras
        data_str = data_str.strip()
        
        # Padrões comuns de data
        padroes = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        ]
        
        for padrao in padroes:
            match = re.search(padrao, data_str)
            if match:
                if len(match.groups()) == 3:
                    if len(match.group(1)) == 4:  # YYYY-MM-DD
                        return f"{match.group(3)}/{match.group(2)}/{match.group(1)}"
                    else:  # DD/MM/YYYY ou DD-MM-YYYY
                        return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
        
        return data_str
    
    def extrair_dados_container(self, container):
        """Extrai dados básicos de um container"""
        try:
            link = container.get("href", "")
            id_pncp = ""
            if "/editais/" in link:
                id_pncp = link.split("/editais/")[-1]
            
            if not id_pncp:
                return None
            
            texto_completo = container.get_text(separator=" | ", strip=True)
            
            dados = {
                "link": f"{settings.PNCP_BASE_URL}{link}" if link.startswith("/") else link,
                "id_pncp": id_pncp,
                "texto_completo": texto_completo
            }
            
            # Extração com regex
            edital_match = re.search(r'Edital\s+n[°º]?\s*(\d+/\d+)', texto_completo, re.IGNORECASE)
            dados["edital"] = edital_match.group(0) if edital_match else ""
            
            modalidade_match = re.search(r'Modalidade[^:]*:\s*([^|]+)', texto_completo, re.IGNORECASE)
            dados["modalidade"] = modalidade_match.group(1).strip() if modalidade_match else ""
            
            # Regex mais robusto para data
            data_match = re.search(r'Última\s+Atualização[^:]*:\s*([^|]+)', texto_completo, re.IGNORECASE)
            data_extraida = data_match.group(1).strip() if data_match else ""
            dados["ultima_atualizacao"] = self.normalizar_data(data_extraida)
            
            # Debug: mostra o que foi extraído
            if not dados["ultima_atualizacao"]:
                print(f"     🔍 Debug - Data extraída: '{data_extraida}'")
                print(f"     🔍 Debug - Texto completo: {texto_completo[:200]}...")
            
            orgao_match = re.search(r'Órgão[^:]*:\s*([^|]+)', texto_completo, re.IGNORECASE)
            dados["orgao"] = orgao_match.group(1).strip() if orgao_match else ""
            
            local_match = re.search(r'Local[^:]*:\s*([^|]+)', texto_completo, re.IGNORECASE)
            dados["local"] = local_match.group(1).strip() if local_match else ""
            
            objeto_match = re.search(r'Objeto[^:]*:\s*(.+)', texto_completo, re.IGNORECASE)
            dados["objeto"] = objeto_match.group(1).strip() if objeto_match else ""
            
            return dados
            
        except Exception as e:
            print(f"   ⚠️ Erro ao extrair dados: {e}")
            return None
    
    def extrair_edital_completo_api(self, id_pncp, salvar_arquivos=False):
        """Extrai dados completos via APIs do PNCP"""
        try:
            if not id_pncp or "/" not in id_pncp:
                return None
            
            cnpj, ano, numero = id_pncp.split('/')
            base_url = f"{settings.PNCP_API_URL}/orgaos/{cnpj}/compras/{ano}/{numero}"
            
            # Busca dados das APIs
            itens = []
            historico = []
            arquivos = []
            
            try:
                itens_response = self.session.get(f"{base_url}/itens", timeout=10)
                if itens_response.status_code == 200:
                    itens = itens_response.json()
            except:
                pass
            
            try:
                historico_response = self.session.get(f"{base_url}/historico", timeout=10)
                if historico_response.status_code == 200:
                    historico = historico_response.json()
            except:
                pass
            
            try:
                arquivos_response = self.session.get(f"{base_url}/arquivos", timeout=10)
                if arquivos_response.status_code == 200:
                    arquivos = arquivos_response.json()
            except:
                pass
            
            # Dados do órgão
            dados_orgao = {}
            try:
                orgao_response = self.session.get(f"{settings.PNCP_API_URL}/orgaos/{cnpj}", timeout=10)
                if orgao_response.status_code == 200:
                    dados_orgao = orgao_response.json()
            except:
                pass
            
            # Monta dados para Supabase
            valor_total = sum(item.get('valorTotal', 0) for item in itens)
            valor_fmt = f"R$ {valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            return {
                "id_pncp": id_pncp,
                "edital": f"Edital {numero}/{ano}",
                "modalidade": itens[0].get('criterioJulgamentoNome', '') if itens else '',
                "ultima_atualizacao": datetime.now().strftime('%d/%m/%Y'),
                "orgao": dados_orgao.get('razaoSocial', ''),
                "local": f"{dados_orgao.get('municipio', '')}/{dados_orgao.get('uf', '')}",
                "objeto": self.inferir_objeto(itens),
                "link_licitacao": f"{settings.PNCP_BASE_URL}/app/editais/{id_pncp}",
                "valor": valor_fmt if valor_total > 0 else "NÃO INFORMADO",
                "data_abertura": "",
                "situacao": itens[0].get('situacaoCompraItemNome', 'Em andamento') if itens else 'Em andamento',
                "valor_sigiloso": any(item.get('orcamentoSigiloso', False) for item in itens),
                "informacoes_detalhadas": {
                    "metodo": "final_otimizado",
                    "data": datetime.now().isoformat(),
                    "apis_utilizadas": ["itens", "historico", "arquivos", "orgao"]
                },
                "itens": [
                    {
                        "numero": item.get('numeroItem'),
                        "descricao": item.get('descricao', ''),
                        "quantidade": item.get('quantidade', 0),
                        "valor_unitario": item.get('valorUnitarioEstimado', 0),
                        "valor_total": item.get('valorTotal', 0)
                    } for item in itens
                ],
                "anexos": [
                    self.processar_arquivo_storage(arq, id_pncp, salvar_arquivos) for arq in arquivos if arq
                ],
                "historico": [
                    {
                        "data": evento.get('logManutencaoDataInclusao', ''),
                        "usuario": evento.get('usuarioNome', ''),
                        "tipo": evento.get('tipoLogManutencaoNome', '')
                    } for evento in historico
                ],
                "total_itens": len(itens),
                "total_anexos": len(arquivos),
                "total_historico": len(historico),
                "itens_processados": len(itens) > 0,
                "anexos_processados": len(arquivos) > 0,
                "historico_processado": len(historico) > 0,
                "valor_total_numerico": float(valor_total),
                "cnpj_orgao": cnpj,
                "ano": int(ano),
                "numero": int(numero),
                "metodo_extracao": "final_otimizado",
                "tempo_extracao": 0,
                "data_coleta": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erro ao extrair via API {id_pncp}: {e}")
            return None
    
    def inferir_objeto(self, itens):
        """Infere objeto baseado nos itens"""
        if not itens:
            return "Não informado"
        
        descricoes = [item.get('descricao', '').upper() for item in itens]
        primeira_desc = descricoes[0] if descricoes else "Não informado"
        return f"Aquisição/Contratação: {primeira_desc[:100]}"
    
    def processar_arquivo_storage(self, arquivo_api, edital_id, fazer_upload=False):
        """Processa arquivo e opcionalmente faz upload para Storage"""
        try:
            url_original = arquivo_api.get('url')
            titulo = arquivo_api.get('titulo', 'arquivo')
            tipo = arquivo_api.get('tipo', 'PDF')
            
            arquivo_info = {
                "nome_original": titulo,
                "url_original": url_original,
                "tipo": tipo,
                "tamanho": 0,
                "storage_url": None,
                "upload_sucesso": False,
                "data_upload": datetime.now().isoformat()
            }
            
            if fazer_upload and url_original:
                try:
                    print(f"     📥 Baixando {titulo[:30]}...")
                    
                    response = self.session.get(url_original, timeout=30, stream=True)
                    response.raise_for_status()
                    
                    nome_limpo = re.sub(r'[<>:"/\\|?*]', '_', titulo)
                    nome_arquivo = f"{nome_limpo}.pdf"
                    
                    file_bytes = response.content
                    arquivo_info["tamanho"] = len(file_bytes)
                    arquivo_info["nome_arquivo"] = nome_arquivo
                    
                    print(f"     📊 Tamanho: {len(file_bytes):,} bytes")
                    
                    storage_path = f"editais/{edital_id}/{nome_arquivo}"
                    
                    print(f"     ☁️ Enviando para Storage...")
                    
                    try:
                        result = self.supabase.storage.from_(self.bucket_name).upload(
                            path=storage_path,
                            file=file_bytes,
                            file_options={"content-type": "application/pdf"}
                        )
                        upload_ok = True
                    except Exception as upload_error:
                        if "duplicate" in str(upload_error).lower():
                            print(f"     🔄 Arquivo existe, substituindo...")
                            try:
                                self.supabase.storage.from_(self.bucket_name).remove([storage_path])
                                result = self.supabase.storage.from_(self.bucket_name).upload(
                                    path=storage_path,
                                    file=file_bytes,
                                    file_options={"content-type": "application/pdf"}
                                )
                                upload_ok = True
                            except Exception as retry_error:
                                print(f"     ❌ Falha na substituição: {str(retry_error)[:50]}...")
                                upload_ok = False
                        else:
                            print(f"     ❌ Erro no upload: {str(upload_error)[:50]}...")
                            upload_ok = False
                    
                    if upload_ok:
                        storage_url = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
                        arquivo_info["storage_url"] = storage_url
                        arquivo_info["upload_sucesso"] = True
                        print(f"     ✅ Upload concluído!")
                    else:
                        print(f"     ❌ Falha no upload")
                        
                except Exception as e:
                    print(f"     ❌ Erro no upload: {str(e)[:50]}...")
                    arquivo_info["erro_upload"] = str(e)
            
            return arquivo_info
            
        except Exception as e:
            print(f"     ❌ Erro ao processar arquivo: {e}")
            return None
    
    def salvar_supabase(self, dados):
        """Salva dados na tabela editais_completos"""
        try:
            print(f"   🔄 Tentando salvar {dados['id_pncp']}...")
            
            try:
                result = self.supabase.table("editais_completos").insert(dados).execute()
                if result.data:
                    id_salvo = result.data[0].get("id")
                    print(f"   ✅ Inserido com ID: {id_salvo}")
                    return id_salvo
                else:
                    print(f"   ⚠️ Insert sem dados retornados")
                    return None
            except Exception as insert_error:
                print(f"   ⚠️ Insert falhou: {str(insert_error)[:100]}...")
                
                if "duplicate" in str(insert_error).lower() or "unique" in str(insert_error).lower():
                    print(f"   🔄 Tentando update...")
                    try:
                        result = self.supabase.table("editais_completos").update(dados).eq("id_pncp", dados["id_pncp"]).execute()
                        if result.data:
                            id_salvo = result.data[0].get("id")
                            print(f"   ✅ Atualizado com ID: {id_salvo}")
                            return id_salvo
                        else:
                            print(f"   ⚠️ Update sem dados retornados")
                            return None
                    except Exception as update_error:
                        print(f"   ❌ Update falhou: {str(update_error)[:100]}...")
                        raise Exception(f"Insert e Update falharam: {insert_error}")
                else:
                    raise Exception(f"Erro no insert: {insert_error}")
            
        except Exception as e:
            print(f"   ❌ ERRO CRÍTICO ao salvar: {e}")
            
            if "policy" in str(e).lower() or "rls" in str(e).lower():
                print(f"   💡 PROBLEMA: Row Level Security bloqueando")
            elif "permission" in str(e).lower():
                print(f"   💡 PROBLEMA: Permissões insuficientes")
            elif "network" in str(e).lower():
                print(f"   💡 PROBLEMA: Erro de rede")
            
            return None
    
    async def executar_extracao_dia(self, data_extracao=None, salvar_arquivos=False, max_editais=50):
        """Executa extração de um dia específico com limites otimizados"""
        print("🚀 INICIANDO EXTRAÇÃO DO DIA (OTIMIZADA)")
        print("=" * 50)
        
        start_time = time.time()
        
        if not data_extracao:
            data_extracao = (datetime.now() - timedelta(days=1)).date()
        elif isinstance(data_extracao, str):
            data_extracao = datetime.strptime(data_extracao, "%Y-%m-%d").date()
        
        print(f"📅 Data de extração: {data_extracao}")
        print(f"📊 Limite máximo de editais: {max_editais}")
        print(f"💾 Salvar arquivos: {salvar_arquivos}")
        
        # 1. Busca editais com limites reduzidos
        editais_encontrados = self.buscar_editais_recentes(
            data_filtro=data_extracao,
            max_paginas=2,  # Reduzido de 10 para 2
            limit_por_pagina=25  # Reduzido de 100 para 25
        )
        
        if not editais_encontrados:
            return {
                "success": False,
                "message": f"Nenhum edital encontrado para {data_extracao}",
                "total_encontrados": 0,
                "total_salvos": 0,
                "tempo_execucao": round(time.time() - start_time, 2)
            }
        
        # 2. Limita o número de editais processados
        if len(editais_encontrados) > max_editais:
            print(f"⚠️ Limitando processamento de {len(editais_encontrados)} para {max_editais} editais")
            editais_encontrados = editais_encontrados[:max_editais]
        
        # 3. Extrai e salva cada edital
        print(f"\n📋 Processando {len(editais_encontrados)} editais...")
        
        salvos = []
        erros = []
        
        for i, edital_basico in enumerate(editais_encontrados, 1):
            try:
                id_pncp = edital_basico.get("id_pncp")
                if not id_pncp:
                    continue
                
                print(f"[{i}/{len(editais_encontrados)}] 📋 {id_pncp}")
                
                # Verifica se já existe
                existing = self.supabase.table("editais_completos")\
                    .select("id")\
                    .eq("id_pncp", id_pncp)\
                    .execute()
                
                if existing.data:
                    print("   ⚠️ Já existe, pulando...")
                    continue
                
                # Extrai dados completos (sem arquivos por padrão)
                dados_completos = self.extrair_edital_completo_api(id_pncp, salvar_arquivos=salvar_arquivos)
                
                if dados_completos:
                    # Salva
                    supabase_id = self.salvar_supabase(dados_completos)
                    if supabase_id:
                        salvos.append(id_pncp)
                        print(f"   ✅ SALVO ID: {supabase_id}")
                    else:
                        print("   ❌ FALHA AO SALVAR NO SUPABASE")
                        erros.append({"id_pncp": id_pncp, "erro": "Falha ao salvar no Supabase"})
                else:
                    print("   ❌ Falha na extração de dados completos")
                    erros.append({"id_pncp": id_pncp, "erro": "Falha na extração de dados"})
                
                # Pausa reduzida
                await asyncio.sleep(0.2)  # Reduzido de 0.3 para 0.2
                
            except Exception as e:
                print(f"   ❌ Erro: {e}")
                erros.append({"id_pncp": id_pncp, "erro": str(e)})
        
        tempo_total = round(time.time() - start_time, 2)
        
        resultado = {
            "success": True,
            "message": f"Extração otimizada concluída em {tempo_total}s",
            "data_extracao": str(data_extracao),
            "total_encontrados": len(editais_encontrados),
            "total_salvos": len(salvos),
            "total_erros": len(erros),
            "tempo_execucao": tempo_total,
            "editais_salvos": salvos,
            "erros": erros,
            "configuracao": {
                "max_editais": max_editais,
                "salvar_arquivos": salvar_arquivos,
                "max_paginas": 2,
                "limit_por_pagina": 25
            }
        }
        
        print(f"\n🎉 EXTRAÇÃO OTIMIZADA CONCLUÍDA!")
        print(f"📊 Encontrados: {resultado['total_encontrados']}")
        print(f"💾 Salvos: {resultado['total_salvos']}")
        print(f"❌ Erros: {resultado['total_erros']}")
        print(f"⏱️ Tempo: {tempo_total}s")
        
        return resultado
    
    async def executar_extracao_inteligente(self, data_extracao=None, salvar_arquivos=False, max_editais=50):
        """Executa extração inteligente: sempre D-1, verifica existentes e atualiza mudanças"""
        print("🧠 INICIANDO EXTRAÇÃO INTELIGENTE")
        print("=" * 50)
        
        start_time = time.time()
        
        if not data_extracao:
            data_extracao = (datetime.now() - timedelta(days=1)).date()
        elif isinstance(data_extracao, str):
            data_extracao = datetime.strptime(data_extracao, "%Y-%m-%d").date()
        
        print(f"📅 Data de extração: {data_extracao}")
        print(f"📊 Limite máximo de editais: {max_editais}")
        print(f"💾 Salvar arquivos: {salvar_arquivos}")
        
        # 1. Busca editais do dia anterior
        editais_encontrados = self.buscar_editais_recentes(
            data_filtro=data_extracao,
            max_paginas=3,  # Busca mais páginas para garantir cobertura
            limit_por_pagina=25
        )
        
        if not editais_encontrados:
            return {
                "success": False,
                "message": f"Nenhum edital encontrado para {data_extracao}",
                "total_encontrados": 0,
                "total_novos": 0,
                "total_atualizados": 0,
                "total_erros": 0,
                "tempo_execucao": round(time.time() - start_time, 2)
            }
        
        # 2. Limita o número de editais processados
        if len(editais_encontrados) > max_editais:
            print(f"⚠️ Limitando processamento de {len(editais_encontrados)} para {max_editais} editais")
            editais_encontrados = editais_encontrados[:max_editais]
        
        # 3. Processa cada edital com verificação inteligente
        print(f"\n📋 Processando {len(editais_encontrados)} editais...")
        
        novos = []
        atualizados = []
        erros = []
        
        for i, edital_basico in enumerate(editais_encontrados, 1):
            try:
                id_pncp = edital_basico.get("id_pncp")
                if not id_pncp:
                    continue
                
                print(f"[{i}/{len(editais_encontrados)}] 📋 {id_pncp}")
                
                # Verifica se já existe na base
                existing = self.supabase.table("editais_completos")\
                    .select("id, ultima_atualizacao, updated_at")\
                    .eq("id_pncp", id_pncp)\
                    .execute()
                
                if existing.data:
                    edital_existente = existing.data[0]
                    print(f"   🔄 Já existe (ID: {edital_existente['id']})")
                    
                    # Verifica se precisa atualizar (comparando datas)
                    data_existente = edital_existente.get('ultima_atualizacao', '')
                    data_nova = edital_basico.get('ultima_atualizacao', '')
                    
                    if data_nova != data_existente:
                        print(f"   📅 Atualização detectada: {data_existente} → {data_nova}")
                        
                        # Extrai dados completos atualizados
                        dados_completos = self.extrair_edital_completo_api(id_pncp, salvar_arquivos=salvar_arquivos)
                        
                        if dados_completos:
                            # Atualiza registro existente
                            try:
                                result = self.supabase.table("editais_completos")\
                                    .update(dados_completos)\
                                    .eq("id_pncp", id_pncp)\
                                    .execute()
                                
                                if result.data:
                                    atualizados.append(id_pncp)
                                    print(f"   ✅ ATUALIZADO ID: {edital_existente['id']}")
                                else:
                                    print("   ❌ FALHA AO ATUALIZAR")
                                    erros.append({"id_pncp": id_pncp, "erro": "Falha ao atualizar"})
                            except Exception as e:
                                print(f"   ❌ Erro na atualização: {e}")
                                erros.append({"id_pncp": id_pncp, "erro": str(e)})
                        else:
                            print("   ❌ Falha na extração de dados atualizados")
                            erros.append({"id_pncp": id_pncp, "erro": "Falha na extração de dados"})
                    else:
                        print(f"   ⏭️ Sem mudanças, mantendo existente")
                        continue
                else:
                    print(f"   🆕 Novo edital detectado")
                    
                    # Extrai dados completos para novo edital
                    dados_completos = self.extrair_edital_completo_api(id_pncp, salvar_arquivos=salvar_arquivos)
                    
                    if dados_completos:
                        # Salva novo registro
                        supabase_id = self.salvar_supabase(dados_completos)
                        if supabase_id:
                            novos.append(id_pncp)
                            print(f"   ✅ NOVO SALVO ID: {supabase_id}")
                        else:
                            print("   ❌ FALHA AO SALVAR NOVO")
                            erros.append({"id_pncp": id_pncp, "erro": "Falha ao salvar novo"})
                    else:
                        print("   ❌ Falha na extração de dados para novo")
                        erros.append({"id_pncp": id_pncp, "erro": "Falha na extração de dados"})
                
                # Pausa reduzida
                await asyncio.sleep(0.2)
                
            except Exception as e:
                print(f"   ❌ Erro: {e}")
                erros.append({"id_pncp": id_pncp, "erro": str(e)})
        
        tempo_total = round(time.time() - start_time, 2)
        
        resultado = {
            "success": True,
            "message": f"Extração inteligente concluída em {tempo_total}s",
            "data_extracao": str(data_extracao),
            "total_encontrados": len(editais_encontrados),
            "total_novos": len(novos),
            "total_atualizados": len(atualizados),
            "total_erros": len(erros),
            "tempo_execucao": tempo_total,
            "editais_novos": novos,
            "editais_atualizados": atualizados,
            "erros": erros,
            "configuracao": {
                "max_editais": max_editais,
                "salvar_arquivos": salvar_arquivos,
                "max_paginas": 3,
                "limit_por_pagina": 25,
                "estrategia": "inteligente"
            }
        }
        
        print(f"\n🎉 EXTRAÇÃO INTELIGENTE CONCLUÍDA!")
        print(f"📊 Encontrados: {resultado['total_encontrados']}")
        print(f"🆕 Novos: {resultado['total_novos']}")
        print(f"🔄 Atualizados: {resultado['total_atualizados']}")
        print(f"❌ Erros: {resultado['total_erros']}")
        print(f"⏱️ Tempo: {tempo_total}s")
        
        return resultado