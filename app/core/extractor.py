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
        """Configura Selenium otimizado e seguro"""
        chrome_options = Options()
        
        if settings.SELENIUM_HEADLESS:
            chrome_options.add_argument("--headless")
        
        # Configurações de segurança e performance
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
        
        # 🚫 PREVENIR MÚLTIPLAS ABAS
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-new-tab-first-run")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        
        # Configurações de automação
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Preferências para evitar popups e novas abas
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,  # Bloquear notificações
                "popups": 2,         # Bloquear popups
                "geolocation": 2,    # Bloquear localização
                "media_stream": 2,   # Bloquear câmera/microfone
            },
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2,  # Bloquear imagens
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            # Tenta usar webdriver-manager para Render
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Selenium configurado com webdriver-manager")
            return True
            
        except Exception as e:
            print(f" Erro com webdriver-manager: {e}")
            try:
                # Fallback para configuração manual
                self.driver = webdriver.Chrome(options=chrome_options)
                print(" Selenium configurado manualmente")
                return True
            except Exception as e2:
                print(f" Erro ao configurar Selenium: {e2}")
                return False
    
    def buscar_editais_recentes(self, data_filtro=None, max_paginas=10, limit_por_pagina=50):
        """Busca editais específicos do dia no PNCP (estratégia otimizada)"""
        if not data_filtro:
            data_filtro = (datetime.now() - timedelta(days=1)).date()
        
        print(f" ESTRATEGIA OTIMIZADA: Buscando TODOS os editais de {data_filtro}")
        print(f" Configuracao: ate {max_paginas} paginas x {limit_por_pagina} editais = maximo {max_paginas * limit_por_pagina} editais")
        
        if not self.configurar_selenium():
            return []
        
        editais_encontrados = []
        
        try:
            # Busca com filtro de data específico (se o PNCP suportar)
            data_formatada = data_filtro.strftime("%d/%m/%Y")
            
            for pagina in range(1, max_paginas + 1):
                # URL otimizada - busca por editais mais recentes primeiro
                url_pagina = f"{self.url_base}?q=&pagina={pagina}&tam_pagina={limit_por_pagina}&ordenacao=data_desc"
                
                print(f"Pagina {pagina}: {url_pagina}")
                print(f"Buscando editais de: {data_formatada}")
                
                self.driver.get(url_pagina)
                time.sleep(2)
                
                try:
                    time.sleep(1)
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    containers = soup.find_all("a", class_="br-item")
                    
                    if not containers:
                        print(f"Nenhum container encontrado na pagina {pagina}")
                        break
                    
                    print(f"Encontrados {len(containers)} editais na pagina {pagina}")
                    
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
                                                    print(f"{edital_data['id_pncp']} - formato de data nao reconhecido: '{data_str}'")
                                    
                                    if data_edital:
                                        if not data_mais_antiga_pagina or data_edital < data_mais_antiga_pagina:
                                            data_mais_antiga_pagina = data_edital
                                        
                                        if data_edital >= data_filtro:
                                            editais_pagina.append(edital_data)
                                            print(f"{edital_data['id_pncp']} - {data_edital}")
                                        else:
                                            print(f"{edital_data['id_pncp']} - data muito antiga: {data_edital}")
                                    else:
                                        # Se nao conseguiu converter a data, inclui mesmo assim
                                        editais_pagina.append(edital_data)
                                        print(f"{edital_data['id_pncp']} - data invalida: '{data_str}'")
                                
                                except Exception as e:
                                    print(f"Erro ao processar data: {e}")
                                    editais_pagina.append(edital_data)
                        
                        except Exception as e:
                            print(f"Erro ao processar container: {e}")
                            continue
                    
                    editais_encontrados.extend(editais_pagina)
                    print(f"{len(editais_pagina)} editais validos na pagina {pagina}")
                    
                    # Limite de seguranca alto para pegar TODOS os editais
                    if len(editais_encontrados) >= 1000:  # Limite muito alto
                        print(f"Limite de seguranca (1000 editais) atingido, parando busca")
                        break
                    
                    # Para apenas se TODA a pagina for anterior ao filtro
                    if data_mais_antiga_pagina and data_mais_antiga_pagina < data_filtro and len(editais_pagina) == 0:
                        print(f"Pagina inteira anterior ao filtro ({data_mais_antiga_pagina}), parando")
                        break
                    
                    # Continua se ainda ha editais validos na pagina
                    if len(editais_pagina) > 0:
                        print(f"Pagina ainda tem editais validos, continuando...")
                    else:
                        print(f"Nenhum edital valido nesta pagina, mas continuando...")
                
                except Exception as e:
                    print(f"Erro ao processar pagina {pagina}: {e}")
                    break
        
        except Exception as e:
            print(f"Erro geral na busca: {e}")
            return []
        
        print(f"Total de editais encontrados: {len(editais_encontrados)}")
        return editais_encontrados
    
    def fechar_driver(self):
        """Fecha o driver Selenium"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                print(" Driver Selenium fechado")
            except Exception as e:
                print(f" Erro ao fechar driver: {e}")
                self.driver = None
    
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
            
            # Extração com regex - CORRIGIDO para lidar com " | " como separador
            edital_match = re.search(r'Edital\s+n[°º]?\s*(\d+/\d+)', texto_completo, re.IGNORECASE)
            dados["edital"] = edital_match.group(0) if edital_match else ""
            
            # CORRIGIDO: Remove " | " antes do valor
            modalidade_match = re.search(r'Modalidade[^:]*:\s*\|?\s*([^|]+)', texto_completo, re.IGNORECASE)
            dados["modalidade"] = modalidade_match.group(1).strip() if modalidade_match else ""
            
            # CORRIGIDO: Captura data mesmo com " | " antes
            data_match = re.search(r'Última\s+Atualização[^:]*:\s*\|?\s*(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            data_extraida = data_match.group(1).strip() if data_match else ""
            dados["ultima_atualizacao"] = self.normalizar_data(data_extraida)
            
            # CORRIGIDO: Remove " | " antes do valor
            orgao_match = re.search(r'Órgão[^:]*:\s*\|?\s*([^|]+)', texto_completo, re.IGNORECASE)
            dados["orgao"] = orgao_match.group(1).strip() if orgao_match else ""
            
            # CORRIGIDO: Remove " | " antes do valor
            local_match = re.search(r'Local[^:]*:\s*\|?\s*([^|]+)', texto_completo, re.IGNORECASE)
            dados["local"] = local_match.group(1).strip() if local_match else ""
            
            # CORRIGIDO: Remove " | " antes do valor
            objeto_match = re.search(r'Objeto[^:]*:\s*\|?\s*([^|]+)', texto_completo, re.IGNORECASE)
            dados["objeto"] = objeto_match.group(1).strip() if objeto_match else ""
            
            return dados
            
        except Exception as e:
            print(f"Erro ao extrair dados: {e}")
            return None
    
    def extrair_edital_completo_hibrido(self, id_pncp, salvar_arquivos=True):
        """Extrai dados COMPLETOS: Selenium (página) + APIs (dados estruturados) + Arquivos"""
        try:
            if not id_pncp or "/" not in id_pncp:
                return None
            
            print(f"EXTRAÇÃO COMPLETA HÍBRIDA: {id_pncp}")
            
            # Separa componentes do ID
            cnpj, ano, numero = id_pncp.split('/')
            
            # === 1. EXTRAÇÃO VIA SELENIUM (PÁGINA DETALHADA) ===
            url_detalhada = f"{settings.PNCP_BASE_URL}/app/editais/{id_pncp}"
            print(f"Acessando pagina: {url_detalhada}")
            
            # Configura Selenium se necessário
            if not self.driver:
                if not self.configurar_selenium():
                    return None
            
            # Acessa página
            self.driver.get(url_detalhada)
            time.sleep(3)  # Aguarda carregamento completo
            
            # Extrai HTML
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            texto_pagina = soup.get_text(separator=" ", strip=True)
            
            # === 2. EXTRAÇÃO VIA APIs (DADOS ESTRUTURADOS) ===
            base_url = f"{settings.PNCP_API_URL}/orgaos/{cnpj}/compras/{ano}/{numero}"
            print(f"Buscando APIs: {base_url}")
            
            # Busca dados das APIs
            itens = []
            historico = []
            arquivos = []
            dados_orgao = {}
            
            # API de Itens
            try:
                print(f"Buscando itens...")
                itens_response = self.session.get(f"{base_url}/itens", timeout=15)
                if itens_response.status_code == 200:
                    itens = itens_response.json()
                    print(f"{len(itens)} itens encontrados")
                else:
                    print(f"Itens: Status {itens_response.status_code}")
            except Exception as e:
                print(f"Erro itens: {e}")
            
            # API de Histórico
            try:
                print(f"Buscando historico...")
                historico_response = self.session.get(f"{base_url}/historico", timeout=15)
                if historico_response.status_code == 200:
                    historico = historico_response.json()
                    print(f"{len(historico)} eventos no historico")
                else:
                    print(f"Historico: Status {historico_response.status_code}")
            except Exception as e:
                print(f"Erro historico: {e}")
            
            # API de Arquivos
            try:
                print(f"Buscando arquivos...")
                arquivos_response = self.session.get(f"{base_url}/arquivos", timeout=15)
                if arquivos_response.status_code == 200:
                    arquivos = arquivos_response.json()
                    print(f"{len(arquivos)} arquivos encontrados")
                else:
                    print(f"Arquivos: Status {arquivos_response.status_code}")
            except Exception as e:
                print(f"Erro arquivos: {e}")
            
            # API do Órgão
            try:
                print(f"Buscando dados do orgao...")
                orgao_response = self.session.get(f"{settings.PNCP_API_URL}/orgaos/{cnpj}", timeout=15)
                if orgao_response.status_code == 200:
                    dados_orgao = orgao_response.json()
                    print(f"Dados do orgao obtidos")
                else:
                    print(f"Orgao: Status {orgao_response.status_code}")
            except Exception as e:
                print(f"Erro orgao: {e}")
            
            # === 3. MONTA DADOS COMPLETOS ===
            dados = {
                "id_pncp": id_pncp,
                "link_licitacao": url_detalhada,
                "metodo_extracao": "hibrido_completo",
                "data_coleta": datetime.now().isoformat(),
                "cnpj_orgao": cnpj,
                "ano": int(ano),
                "numero": int(numero)
            }
            
            # === 4. EXTRAÇÃO DE DADOS DA PÁGINA (SELENIUM) ===
            print(f"Extraindo dados da pagina HTML...")
            
            # Data de divulgação no PNCP
            data_divulgacao_match = re.search(r'Data\s+de\s+divulgação\s+no\s+PNCP[:\s]*(\d{2}/\d{2}/\d{4})', texto_pagina, re.IGNORECASE)
            if not data_divulgacao_match:
                data_divulgacao_match = re.search(r'divulgação\s+no\s+PNCP[:\s]*(\d{2}/\d{2}/\d{4})', texto_pagina, re.IGNORECASE)
            dados["data_divulgacao_pncp"] = data_divulgacao_match.group(1) if data_divulgacao_match else None
            
            # Última atualização
            ultima_atualizacao_match = re.search(r'Última\s+atualização[:\s]*(\d{2}/\d{2}/\d{4})', texto_pagina, re.IGNORECASE)
            dados["ultima_atualizacao"] = ultima_atualizacao_match.group(1) if ultima_atualizacao_match else datetime.now().strftime('%d/%m/%Y')
            
            # Órgão (prioriza dados da API, senão extrai da página)
            if dados_orgao.get('razaoSocial'):
                dados["orgao"] = dados_orgao['razaoSocial']
            else:
                orgao_match = re.search(r'Órgão[:\s]*([^\n\r]{1,200})', texto_pagina, re.IGNORECASE)
                dados["orgao"] = orgao_match.group(1).strip() if orgao_match else ""
            
            # Local
            if dados_orgao.get('municipio') and dados_orgao.get('uf'):
                dados["local"] = f"{dados_orgao['municipio']}/{dados_orgao['uf']}"
            else:
                local_match = re.search(r'Local[:\s]*([^\n\r]{1,100})', texto_pagina, re.IGNORECASE)
                dados["local"] = local_match.group(1).strip() if local_match else ""
            
            # Modalidade (prioriza dados dos itens)
            if itens and itens[0].get('criterioJulgamentoNome'):
                dados["modalidade"] = itens[0]['criterioJulgamentoNome']
            else:
                modalidade_match = re.search(r'Modalidade\s+da\s+contratação[:\s]*([^\n\r]{1,100})', texto_pagina, re.IGNORECASE)
                dados["modalidade"] = modalidade_match.group(1).strip() if modalidade_match else ""
            
            # Dados específicos da página
            amparo_match = re.search(r'Amparo\s+legal[:\s]*([^\n\r]{1,200})', texto_pagina, re.IGNORECASE)
            dados["amparo_legal"] = amparo_match.group(1).strip() if amparo_match else ""
            
            tipo_match = re.search(r'Tipo[:\s]*([^\n\r]{1,100})', texto_pagina, re.IGNORECASE)
            dados["tipo"] = tipo_match.group(1).strip() if tipo_match else ""
            
            modo_disputa_match = re.search(r'Modo\s+de\s+disputa[:\s]*([^\n\r]{1,100})', texto_pagina, re.IGNORECASE)
            dados["modo_disputa"] = modo_disputa_match.group(1).strip() if modo_disputa_match else ""
            
            # Datas
            data_inicio_match = re.search(r'Data\s+de\s+início\s+de\s+recebimento\s+de\s+propostas[:\s]*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})', texto_pagina, re.IGNORECASE)
            dados["data_inicio_propostas"] = data_inicio_match.group(1) if data_inicio_match else ""
            
            data_fim_match = re.search(r'Data\s+fim\s+de\s+recebimento\s+de\s+propostas[:\s]*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})', texto_pagina, re.IGNORECASE)
            dados["data_fim_propostas"] = data_fim_match.group(1) if data_fim_match else ""
            
            # Data de abertura (múltiplos padrões)
            data_abertura_match = re.search(r'Data\s+de\s+abertura\s+das?\s+propostas[:\s]*(\d{2}/\d{2}/\d{4}(?:\s+\d{2}:\d{2})?)', texto_pagina, re.IGNORECASE)
            if not data_abertura_match:
                data_abertura_match = re.search(r'Data\s+da\s+sessão[:\s]*(\d{2}/\d{2}/\d{4}(?:\s+\d{2}:\d{2})?)', texto_pagina, re.IGNORECASE)
            dados["data_abertura"] = data_abertura_match.group(1) if data_abertura_match else None
            
            situacao_match = re.search(r'Situação[:\s]*([^\n\r]{1,100})', texto_pagina, re.IGNORECASE)
            dados["situacao"] = situacao_match.group(1).strip() if situacao_match else ""
            
            # Objeto (prioriza inferência dos itens)
            if itens:
                dados["objeto"] = self.inferir_objeto(itens)
            else:
                objeto_match = re.search(r'Objeto[:\s]*([^\n\r]{1,500})', texto_pagina, re.IGNORECASE)
                dados["objeto"] = objeto_match.group(1).strip() if objeto_match else ""
            
            registro_preco_match = re.search(r'Registro\s+de\s+preço[:\s]*([^\n\r]{1,50})', texto_pagina, re.IGNORECASE)
            dados["registro_preco"] = registro_preco_match.group(1).strip() if registro_preco_match else ""
            
            fonte_orcamentaria_match = re.search(r'Fonte\s+orçamentária[:\s]*([^\n\r]{1,200})', texto_pagina, re.IGNORECASE)
            dados["fonte_orcamentaria"] = fonte_orcamentaria_match.group(1).strip() if fonte_orcamentaria_match else ""
            
            unidade_compradora_match = re.search(r'Unidade\s+compradora[:\s]*([^\n\r]{1,200})', texto_pagina, re.IGNORECASE)
            dados["unidade_compradora"] = unidade_compradora_match.group(1).strip() if unidade_compradora_match else ""
            
            id_contratacao_match = re.search(r'Id\s+contratação\s+PNCP[:\s]*([^\n\r]{1,100})', texto_pagina, re.IGNORECASE)
            dados["id_contratacao_pncp"] = id_contratacao_match.group(1).strip() if id_contratacao_match else ""
            
            fonte_match = re.search(r'Fonte[:\s]*([^\n\r]{1,200})', texto_pagina, re.IGNORECASE)
            dados["fonte"] = fonte_match.group(1).strip() if fonte_match else ""
            
            # === 5. DADOS ESTRUTURADOS (APIs) ===
            print(f"Processando dados estruturados...")
            
            # Edital básico
            dados["edital"] = f"Edital {numero}/{ano}"
            
            # Valor total
            valor_total = sum(item.get('valorTotal', 0) for item in itens)
            dados["valor_total_numerico"] = valor_total
            dados["valor"] = f"R$ {valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if valor_total > 0 else ""
            
            # Contadores
            dados["total_itens"] = len(itens)
            dados["total_anexos"] = len(arquivos)
            dados["total_historico"] = len(historico)
            
            # Dados processados
            dados["itens"] = itens
            dados["anexos"] = arquivos
            dados["historico"] = historico
            dados["itens_processados"] = len(itens) > 0
            dados["anexos_processados"] = len(arquivos) > 0
            dados["historico_processado"] = len(historico) > 0
            
            # Informações detalhadas
            dados["informacoes_detalhadas"] = {
                "metodo": "hibrido_completo",
                "data": datetime.now().isoformat(),
                "selenium": True,
                "apis_utilizadas": ["itens", "historico", "arquivos", "orgao"],
                "total_apis_sucesso": sum([
                    1 if itens else 0,
                    1 if historico else 0,
                    1 if arquivos else 0,
                    1 if dados_orgao else 0
                ])
            }
            
            # === 6. SALVAMENTO DE ARQUIVOS (SE SOLICITADO) ===
            if salvar_arquivos and arquivos:
                print(f"Processando {len(arquivos)} arquivos...")
                for i, arquivo in enumerate(arquivos, 1):
                    try:
                        print(f"[{i}/{len(arquivos)}] {arquivo.get('nome', 'arquivo')}...")
                        arquivo_info = self.processar_arquivo(arquivo, id_pncp)
                        if arquivo_info:
                            arquivo.update(arquivo_info)
                            print(f"Arquivo processado e salvo no bucket")
                        else:
                            print(f"Falha no processamento do arquivo")
                    except Exception as e:
                        print(f"Erro no arquivo {i}: {e}")
            
            # === 7. RESUMO DOS DADOS EXTRAÍDOS ===
            print(f"EXTRAÇÃO COMPLETA FINALIZADA:")
            print(f"Data divulgacao PNCP: {dados.get('data_divulgacao_pncp', 'N/A')}")
            print(f"Data abertura: {dados.get('data_abertura', 'N/A')}")
            print(f"Orgao: {dados.get('orgao', 'N/A')[:50]}...")
            print(f"Modalidade: {dados.get('modalidade', 'N/A')}")
            print(f"Situacao: {dados.get('situacao', 'N/A')}")
            print(f"Valor: {dados.get('valor', 'N/A')}")
            print(f"Itens: {dados.get('total_itens', 0)}")
            print(f"Anexos: {dados.get('total_anexos', 0)}")
            print(f"Historico: {dados.get('total_historico', 0)}")
            
            return dados
            
        except Exception as e:
            print(f"Erro ao extrair pagina detalhada: {e}")
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
            print(f" Erro ao extrair via API {id_pncp}: {e}")
            return None
    
    def inferir_objeto(self, itens):
        """Infere objeto baseado nos itens"""
        if not itens:
            return "Não informado"
        
        descricoes = [item.get('descricao', '').upper() for item in itens]
        primeira_desc = descricoes[0] if descricoes else "Não informado"
        return f"Aquisição/Contratação: {primeira_desc[:100]}"
    
    def processar_arquivo(self, arquivo, id_pncp):
        """Processa arquivo: download + upload para bucket"""
        try:
            nome_arquivo = arquivo.get('nome', 'arquivo_sem_nome')
            url_download = arquivo.get('url', '')
            tamanho = arquivo.get('tamanho', 0)
            
            print(f"Processando: {nome_arquivo}")
            print(f"URL: {url_download}")
            print(f"Tamanho: {tamanho} bytes")
            
            if not url_download:
                print(f"URL de download não encontrada")
                return {
                    "nome": nome_arquivo,
                    "tamanho": tamanho,
                    "upload_sucesso": False,
                    "erro": "URL não encontrada",
                    "storage_url": None,
                    "data_upload": datetime.now().isoformat()
                }
            
            # === 1. DOWNLOAD DO ARQUIVO ===
            print(f"Fazendo download...")
            
            try:
                response = self.session.get(url_download, timeout=30, stream=True)
                response.raise_for_status()
                
                # Lê conteúdo do arquivo
                conteudo_arquivo = response.content
                tamanho_real = len(conteudo_arquivo)
                
                print(f"Download concluído: {tamanho_real} bytes")
                
            except Exception as e:
                print(f"Erro no download: {e}")
                return {
                    "nome": nome_arquivo,
                    "tamanho": tamanho,
                    "upload_sucesso": False,
                    "erro": f"Erro no download: {e}",
                    "storage_url": None,
                    "data_upload": datetime.now().isoformat()
                }
            
            # === 2. UPLOAD PARA BUCKET ===
            print(f"Fazendo upload para bucket...")
            
            try:
                # Nome único para o arquivo no bucket
                import uuid
                nome_unico = f"{id_pncp.replace('/', '_')}_{uuid.uuid4().hex[:8]}_{nome_arquivo}"
                
                # Upload para Supabase Storage
                resultado_upload = self.supabase.storage.from_(self.bucket_name).upload(
                    file=conteudo_arquivo,
                    path=nome_unico,
                    file_options={
                        "content-type": self.detectar_content_type(nome_arquivo)
                    }
                )
                
                if resultado_upload:
                    # Gera URL pública
                    url_publica = self.supabase.storage.from_(self.bucket_name).get_public_url(nome_unico)
                    
                    print(f"Upload concluído!")
                    print(f"URL pública: {url_publica[:80]}...")
                    
                    return {
                        "nome": nome_arquivo,
                        "nome_bucket": nome_unico,
                        "tamanho": tamanho_real,
                        "upload_sucesso": True,
                        "storage_url": url_publica,
                        "bucket": self.bucket_name,
                        "data_upload": datetime.now().isoformat(),
                        "url_original": url_download
                    }
                else:
                    print(f"Falha no upload")
                    return {
                        "nome": nome_arquivo,
                        "tamanho": tamanho_real,
                        "upload_sucesso": False,
                        "erro": "Falha no upload para bucket",
                        "storage_url": None,
                        "data_upload": datetime.now().isoformat()
                    }
                    
            except Exception as e:
                print(f"Erro no upload: {e}")
                return {
                    "nome": nome_arquivo,
                    "tamanho": tamanho_real if 'tamanho_real' in locals() else tamanho,
                    "upload_sucesso": False,
                    "erro": f"Erro no upload: {e}",
                    "storage_url": None,
                    "data_upload": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"Erro geral no processamento: {e}")
            return {
                "nome": arquivo.get('nome', 'erro'),
                "tamanho": 0,
                "upload_sucesso": False,
                "erro": f"Erro geral: {e}",
                "storage_url": None,
                "data_upload": datetime.now().isoformat()
            }
    
    def detectar_content_type(self, nome_arquivo):
        """Detecta content-type baseado na extensão"""
        extensao = nome_arquivo.lower().split('.')[-1] if '.' in nome_arquivo else ''
        
        tipos = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'zip': 'application/zip',
            'rar': 'application/x-rar-compressed'
        }
        
        return tipos.get(extensao, 'application/octet-stream')
    
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
                    print(f"Baixando {titulo[:30]}...")
                    
                    response = self.session.get(url_original, timeout=30, stream=True)
                    response.raise_for_status()
                    
                    nome_limpo = re.sub(r'[<>:"/\\|?*]', '_', titulo)
                    nome_arquivo = f"{nome_limpo}.pdf"
                    
                    file_bytes = response.content
                    arquivo_info["tamanho"] = len(file_bytes)
                    arquivo_info["nome_arquivo"] = nome_arquivo
                    
                    print(f"Tamanho: {len(file_bytes):,} bytes")
                    
                    storage_path = f"editais/{edital_id}/{nome_arquivo}"
                    
                    print(f"Enviando para Storage...")
                    
                    try:
                        result = self.supabase.storage.from_(self.bucket_name).upload(
                            path=storage_path,
                            file=file_bytes,
                            file_options={"content-type": "application/pdf"}
                        )
                        upload_ok = True
                    except Exception as upload_error:
                        if "duplicate" in str(upload_error).lower():
                            print(f"Arquivo existe, substituindo...")
                            try:
                                self.supabase.storage.from_(self.bucket_name).remove([storage_path])
                                result = self.supabase.storage.from_(self.bucket_name).upload(
                                    path=storage_path,
                                    file=file_bytes,
                                    file_options={"content-type": "application/pdf"}
                                )
                                upload_ok = True
                            except Exception as retry_error:
                                print(f"Falha na substituição: {str(retry_error)[:50]}...")
                                upload_ok = False
                        else:
                            print(f"Erro no upload: {str(upload_error)[:50]}...")
                            upload_ok = False
                    
                    if upload_ok:
                        storage_url = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
                        arquivo_info["storage_url"] = storage_url
                        arquivo_info["upload_sucesso"] = True
                        print(f"Upload concluído!")
                    else:
                        print(f"Falha no upload")
                        
                except Exception as e:
                    print(f"Erro no upload: {str(e)[:50]}...")
                    arquivo_info["erro_upload"] = str(e)
            
            return arquivo_info
            
        except Exception as e:
            print(f"Erro ao processar arquivo: {e}")
            return None
    
    def salvar_supabase(self, dados):
        """Salva dados na tabela editais_completos"""
        try:
            print(f"Tentando salvar {dados['id_pncp']}...")
            
            try:
                result = self.supabase.table("editais_completos").insert(dados).execute()
                if result.data:
                    id_salvo = result.data[0].get("id")
                    print(f"Inserido com ID: {id_salvo}")
                    return id_salvo
                else:
                    print(f"Insert sem dados retornados")
                    return None
            except Exception as insert_error:
                print(f"Insert falhou: {str(insert_error)[:100]}...")
                
                if "duplicate" in str(insert_error).lower() or "unique" in str(insert_error).lower():
                    print(f"Tentando update...")
                    try:
                        result = self.supabase.table("editais_completos").update(dados).eq("id_pncp", dados["id_pncp"]).execute()
                        if result.data:
                            id_salvo = result.data[0].get("id")
                            print(f"Atualizado com ID: {id_salvo}")
                            return id_salvo
                        else:
                            print(f"Update sem dados retornados")
                            return None
                    except Exception as update_error:
                        print(f"Update falhou: {str(update_error)[:100]}...")
                        raise Exception(f"Insert e Update falharam: {insert_error}")
                else:
                    raise Exception(f"Erro no insert: {insert_error}")
            
        except Exception as e:
            print(f"ERRO CRÍTICO ao salvar: {e}")
            
            if "policy" in str(e).lower() or "rls" in str(e).lower():
                print(f"PROBLEMA: Row Level Security bloqueando")
            elif "permission" in str(e).lower():
                print(f"PROBLEMA: Permissões insuficientes")
            elif "network" in str(e).lower():
                print(f"PROBLEMA: Erro de rede")
            
            return None
    
    async def executar_extracao_dia(self, data_extracao=None, salvar_arquivos=False, max_editais=50):
        """Executa extração de um dia específico com limites otimizados"""
        print(" INICIANDO EXTRAÇÃO DO DIA (OTIMIZADA)")
        print("=" * 50)
        
        start_time = time.time()
        
        if not data_extracao:
            data_extracao = (datetime.now() - timedelta(days=1)).date()
        elif isinstance(data_extracao, str):
            data_extracao = datetime.strptime(data_extracao, "%Y-%m-%d").date()
        
        print(f"Data de extracao: {data_extracao}")
        print(f" Limite maximo de editais: {max_editais}")
        print(f" Salvar arquivos: {salvar_arquivos}")
        
        # 1. Busca TODOS os editais do dia anterior (sem limites)
        editais_encontrados = self.buscar_editais_recentes(
            data_filtro=data_extracao,
            max_paginas=20,  # Aumentado para garantir cobertura TOTAL
            limit_por_pagina=100  # Máximo por página para eficiência
        )
        
        if not editais_encontrados:
            return {
                "success": False,
                "message": f"Nenhum edital encontrado para {data_extracao}",
                "total_encontrados": 0,
                "total_salvos": 0,
                "tempo_execucao": round(time.time() - start_time, 2)
            }
        
        # 2. PROCESSA TODOS OS EDITAIS (sem limite)
        print(f" Processando TODOS os {len(editais_encontrados)} editais do dia anterior")
        
        # 3. Extrai e salva cada edital
        print(f"\n Processando {len(editais_encontrados)} editais...")
        
        salvos = []
        erros = []
        
        for i, edital_basico in enumerate(editais_encontrados, 1):
            try:
                id_pncp = edital_basico.get("id_pncp")
                if not id_pncp:
                    continue
                
                print(f"[{i}/{len(editais_encontrados)}]  {id_pncp}")
                
                # Verifica se já existe (VERIFICAÇÃO INTELIGENTE)
                existing = self.supabase.table("editais_completos")\
                    .select("id, ultima_atualizacao, data_coleta")\
                    .eq("id_pncp", id_pncp)\
                    .execute()
                
                edital_existente = None
                deve_extrair = True
                
                if existing.data:
                    edital_existente = existing.data[0]
                    ultima_coleta = edital_existente.get("data_coleta")
                    
                    # Se foi coletado hoje, pula
                    if ultima_coleta:
                        data_coleta = datetime.fromisoformat(ultima_coleta.replace('Z', '+00:00'))
                        hoje = datetime.now()
                        
                        if data_coleta.date() == hoje.date():
                            print(f"Ja existe e foi coletado hoje (ID: {edital_existente['id']}) - PULANDO...")
                            deve_extrair = False
                        else:
                            print(f"Ja existe mas foi coletado antes (ID: {edital_existente['id']}) - ATUALIZANDO...")
                    else:
                        print(f"Ja existe sem data de coleta (ID: {edital_existente['id']}) - ATUALIZANDO...")
                else:
                    print(f"Novo edital - EXTRAINDO PARA INSERIR...")
                
                # Só extrai se necessário
                dados_completos = None
                if deve_extrair:
                    dados_completos = self.extrair_edital_completo_hibrido(id_pncp, salvar_arquivos=salvar_arquivos)
                else:
                    # Pula este edital
                    print(f"Pulando edital {id_pncp} - ja foi processado hoje")
                    continue
                
                if dados_completos:
                    # Salva (INSERT ou UPDATE automático)
                    supabase_id = self.salvar_supabase(dados_completos)
                    if supabase_id:
                        salvos.append(id_pncp)
                        if edital_existente:
                            print(f"ATUALIZADO ID: {supabase_id}")
                        else:
                            print(f"INSERIDO ID: {supabase_id}")
                    else:
                        print(f"FALHA AO SALVAR NO SUPABASE")
                        erros.append({"id_pncp": id_pncp, "erro": "Falha ao salvar no Supabase"})
                else:
                    print(f"Falha na extracao de dados completos")
                    erros.append({"id_pncp": id_pncp, "erro": "Falha na extracao de dados"})
                
                # Pausa reduzida
                await asyncio.sleep(0.2)  # Reduzido de 0.3 para 0.2
                
            except Exception as e:
                print(f" Erro: {e}")
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
        
        print(f"\nEXTRAÇÃO OTIMIZADA CONCLUÍDA!")
        print(f"Encontrados: {resultado['total_encontrados']}")
        print(f"Salvos: {resultado['total_salvos']}")
        print(f"Erros: {resultado['total_erros']}")
        print(f"Tempo: {tempo_total}s")
        
        # Fecha o driver Selenium
        self.fechar_driver()
        
        return resultado
    
    async def executar_extracao_inteligente(self, dias_retroativos=1, salvar_arquivos=False):
        """Executa extração inteligente com dias retroativos configurável"""
        print("INICIANDO EXTRAÇÃO INTELIGENTE")
        print("=" * 50)
        
        start_time = time.time()
        
        data_final = datetime.now().date()
        data_inicial = data_final - timedelta(days=dias_retroativos)
        
        print(f"Periodo: {data_inicial} a {data_final}")
        print(f"Dias retroativos: {dias_retroativos}")
        print(f"Salvar arquivos: {salvar_arquivos}")
        print()
        
        todos_editais = []
        novos_total = []
        atualizados_total = []
        erros_total = []
        
        # Processa cada dia do período
        for dia_offset in range(dias_retroativos, -1, -1):
            data_extracao = data_final - timedelta(days=dia_offset)
            
            print(f"Processando {data_extracao}...")
            
            # Busca editais do dia - SEMPRE extração completa
            editais_encontrados = self.buscar_editais_recentes(
                data_filtro=data_extracao,
                max_paginas=50,  # Sempre máximo para pegar TODOS
                limit_por_pagina=100
            )
            
            if not editais_encontrados:
                print(f"  Nenhum edital encontrado em {data_extracao}")
                continue
            
            print(f"  Encontrados: {len(editais_encontrados)} editais")
            todos_editais.extend(editais_encontrados)
        
        if not todos_editais:
            self.fechar_driver()
            return {
                "success": False,
                "message": f"Nenhum edital encontrado no período",
                "total_encontrados": 0,
                "total_novos": 0,
                "total_atualizados": 0,
                "total_erros": 0,
                "tempo_execucao": round(time.time() - start_time, 2)
            }
        
        print()
        print(f"TOTAL no período: {len(todos_editais)} editais")
        print(f"Processando com verificação inteligente...")
        print()
        
        for i, edital_basico in enumerate(todos_editais, 1):
            try:
                id_pncp = edital_basico.get("id_pncp")
                if not id_pncp:
                    continue
                
                print(f"[{i}/{len(todos_editais)}] {id_pncp}")
                
                # Verifica se já existe na base (VERIFICAÇÃO INTELIGENTE)
                existing = self.supabase.table("editais_completos")\
                    .select("id, ultima_atualizacao, data_coleta")\
                    .eq("id_pncp", id_pncp)\
                    .execute()
                
                edital_existente = None
                deve_extrair = True
                
                if existing.data:
                    edital_existente = existing.data[0]
                    ultima_coleta = edital_existente.get("data_coleta")
                    
                    # Se foi coletado hoje, pula
                    if ultima_coleta:
                        data_coleta = datetime.fromisoformat(ultima_coleta.replace('Z', '+00:00'))
                        hoje = datetime.now()
                        
                        if data_coleta.date() == hoje.date():
                            print(f" Ja existe e foi coletado hoje (ID: {edital_existente['id']}) - PULANDO...")
                            deve_extrair = False
                        else:
                            print(f" Ja existe mas foi coletado antes (ID: {edital_existente['id']}) - ATUALIZANDO...")
                    else:
                        print(f" Ja existe sem data de coleta (ID: {edital_existente['id']}) - ATUALIZANDO...")
                else:
                    print(f" Novo edital - EXTRAINDO PARA INSERIR...")
                
                # Só extrai se necessário
                dados_completos = None
                if deve_extrair:
                    dados_completos = self.extrair_edital_completo_hibrido(id_pncp, salvar_arquivos=salvar_arquivos)
                else:
                    # Pula este edital
                    print(f" Pulando edital {id_pncp} - ja foi processado hoje")
                    continue
                
                # Processa dados extraídos
                if dados_completos:
                    # Salva (INSERT ou UPDATE automático)
                    supabase_id = self.salvar_supabase(dados_completos)
                    if supabase_id:
                        if edital_existente:
                            atualizados_total.append(id_pncp)
                            print(f"ATUALIZADO ID: {supabase_id}")
                        else:
                            novos_total.append(id_pncp)
                            print(f"INSERIDO ID: {supabase_id}")
                    else:
                        print(f"FALHA AO SALVAR NO SUPABASE")
                        erros_total.append({"id_pncp": id_pncp, "erro": "Falha ao salvar no Supabase"})
                else:
                    print(f"Falha na extracao de dados completos")
                    erros_total.append({"id_pncp": id_pncp, "erro": "Falha na extracao de dados"})
                
                # Pausa reduzida
                await asyncio.sleep(0.2)
                
            except Exception as e:
                print(f"Erro: {e}")
                erros_total.append({"id_pncp": id_pncp, "erro": str(e)})
        
        tempo_total = round(time.time() - start_time, 2)
        
        # Fecha driver
        self.fechar_driver()
        
        resultado = {
            "success": True,
            "message": f"Extração inteligente concluída em {tempo_total}s",
            "periodo": f"{data_inicial} a {data_final}",
            "dias_retroativos": dias_retroativos,
            "total_encontrados": len(todos_editais),
            "total_novos": len(novos_total),
            "total_atualizados": len(atualizados_total),
            "total_erros": len(erros_total),
            "tempo_execucao": tempo_total,
            "editais_novos": novos_total,
            "editais_atualizados": atualizados_total,
            "erros": erros_total,
            "configuracao": {
                "salvar_arquivos": salvar_arquivos,
                "max_paginas": 50,
                "limit_por_pagina": 100,
                "estrategia": "inteligente_multiplos_dias"
            }
        }
        
        print()
        print("EXTRAÇÃO INTELIGENTE CONCLUÍDA!")
        print(f"Periodo: {data_inicial} a {data_final}")
        print(f"Encontrados: {resultado['total_encontrados']}")
        print(f"Novos: {resultado['total_novos']}")
        print(f"Atualizados: {resultado['total_atualizados']}")
        print(f"Erros: {resultado['total_erros']}")
        print(f"Tempo: {tempo_total}s")
        
        return resultado