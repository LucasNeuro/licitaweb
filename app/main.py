from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import asyncio
import os
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .core.config import settings
from .core.extractor import PNCPExtractor
from .models.schemas import (
    ConfigScheduler, 
    ExtrairDiaRequest, 
    EditalResponse, 
    StatusSchedulerResponse,
    HealthResponse
)


# Configuração FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
import os
static_dir = os.path.join(os.path.dirname(__file__), "..", "public")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Sistema de Scheduler
class SchedulerSimples:
    def __init__(self, extrator):
        self.extrator = extrator
        self.scheduler = AsyncIOScheduler()
        self.config = {"ativo": False, "hora": "06:00", "ultima_execucao": None}
        self.scheduler_id = 1
        self._config_carregada = False
    
    def _carregar_config_banco(self):
        """Carrega configuração do scheduler do banco"""
        try:
            result = self.extrator.supabase.table("scheduler_horario")\
                .select("*")\
                .eq("id", self.scheduler_id)\
                .execute()
            
            if result.data:
                config = result.data[0]
                hora_exec = str(config['hora_execucao'])[:5]
                self.config = {
                    "ativo": config.get('ativo', False),
                    "hora": hora_exec,
                    "ultima_execucao": config.get('ultima_execucao')
                }
                print(f"✅ Config carregada do banco: {hora_exec}, Ativo: {config.get('ativo')}")
            else:
                # Se não existe, cria com valores padrão
                self.config = {"ativo": False, "hora": "06:00", "ultima_execucao": None}
                print("⚠️ Config não encontrada no banco, usando padrão")
        except Exception as e:
            print(f"❌ Erro ao carregar config do banco: {e}")
            # Usa valores padrão em caso de erro
            self.config = {"ativo": False, "hora": "06:00", "ultima_execucao": None}
    
    def _salvar_config_banco(self):
        """Salva configuração do scheduler no banco"""
        try:
            hora_time = f"{self.config['hora']}:00"
            
            # Tenta atualizar
            result = self.extrator.supabase.table("scheduler_horario")\
                .update({
                    "hora_execucao": hora_time,
                    "ativo": self.config['ativo'],
                    "ultima_execucao": self.config.get('ultima_execucao'),
                    "updated_at": datetime.now().isoformat()
                })\
                .eq("id", self.scheduler_id)\
                .execute()
            
            if not result.data:
                # Se não existe, cria
                self.extrator.supabase.table("scheduler_horario").insert({
                    "id": self.scheduler_id,
                    "hora_execucao": hora_time,
                    "ativo": self.config['ativo'],
                    "ultima_execucao": self.config.get('ultima_execucao')
                }).execute()
            
            print(f"✅ Config salva no banco: {hora_time}, Ativo: {self.config['ativo']}")
        except Exception as e:
            print(f"❌ Erro ao salvar config no banco: {e}")
            raise e
    
    def _registrar_execucao_inicio(self):
        """Registra início de execução"""
        try:
            result = self.extrator.supabase.table("scheduler_execucoes").insert({
                "scheduler_id": self.scheduler_id,
                "data_inicio": datetime.now().isoformat(),
                "status": "em_andamento"
            }).execute()
            
            if result.data:
                return result.data[0]['id']
        except Exception as e:
            print(f"Erro ao registrar início: {e}")
        return None
    
    def _registrar_execucao_fim(self, execucao_id, resultado):
        """Registra fim de execução"""
        try:
            self.extrator.supabase.table("scheduler_execucoes").update({
                "data_fim": datetime.now().isoformat(),
                "status": "concluido" if resultado.get('success') else "erro",
                "total_encontrados": resultado.get('total_encontrados', 0),
                "total_novos": resultado.get('total_novos', 0),
                "total_atualizados": resultado.get('total_atualizados', 0),
                "total_erros": resultado.get('total_erros', 0),
                "tempo_execucao": resultado.get('tempo_execucao', 0),
                "mensagem": resultado.get('message', ''),
                "detalhes": resultado
            }).eq("id", execucao_id).execute()
        except Exception as e:
            print(f"Erro ao registrar fim: {e}")
    
    def inicializar_scheduler(self):
        """Inicializa o scheduler carregando configuração do banco"""
        try:
            print("🔧 Inicializando scheduler...")
            
            # Carrega config do banco
            self._carregar_config_banco()
            self._config_carregada = True
            
            # Se estiver ativo, configura o job
            if self.config.get('ativo', False):
                print(f"✅ Scheduler ativo - configurando execução para {self.config['hora']}")
                self._configurar_job()
            else:
                print("⚠️ Scheduler inativo")
            
            # Inicia o scheduler se não estiver rodando
            if not self.scheduler.running:
                self.scheduler.start()
                print("🚀 Scheduler iniciado!")
        except Exception as e:
            print(f"❌ Erro ao inicializar scheduler: {e}")
            # Continua mesmo com erro
    
    def configurar(self, ativo, hora):
        try:
            # Carrega config do banco na primeira vez
            if not self._config_carregada:
                self._carregar_config_banco()
                self._config_carregada = True
            
            self.config = {"ativo": ativo, "hora": hora, "ultima_execucao": self.config.get("ultima_execucao")}
            
            # Salva no banco
            self._salvar_config_banco()
            
            # Configura o job
            self._configurar_job()
            
            print(f"✅ Scheduler configurado: Ativo={ativo}, Hora={hora}")
            
        except Exception as e:
            print(f"❌ Erro ao configurar scheduler: {e}")
            raise e
    
    def _configurar_job(self):
        """Configura o job de extração automática"""
        try:
            # Remove job existente
            if self.scheduler.get_job("extracao_diaria"):
                self.scheduler.remove_job("extracao_diaria")
            
            if self.config.get('ativo', False):
                hora = self.config.get('hora', '06:00')
                h, m = hora.split(":")
                
                print(f"Configurando scheduler para {hora} (Brasil)")
                print(f"Timezone: America/Sao_Paulo")
                
                self.scheduler.add_job(
                    self.executar_automatico,
                    CronTrigger(hour=int(h), minute=int(m), timezone="America/Sao_Paulo"),
                    id="extracao_diaria",
                    replace_existing=True
                )
                
                # Mostra próxima execução
                job = self.scheduler.get_job("extracao_diaria")
                if job and hasattr(job, 'next_run_time') and job.next_run_time:
                    print(f"Próxima execução: {job.next_run_time}")
                else:
                    print("⚠️ Job criado mas próxima execução não disponível")
            else:
                print("Scheduler desativado")
                
        except Exception as e:
            print(f"❌ Erro ao configurar job: {e}")
            raise e
    
    async def executar_automatico(self):
        print("EXECUÇÃO AUTOMÁTICA INICIADA (método inteligente)")
        
        # Registra início
        execucao_id = self._registrar_execucao_inicio()
        
        # Atualiza última execução no banco
        try:
            self.extrator.supabase.table("scheduler_horario").update({
                "ultima_execucao": datetime.now().isoformat()
            }).eq("id", self.scheduler_id).execute()
        except:
            pass
        
        # Executa extração INTELIGENTE (apenas dia anterior)
        resultado = await self.extrator.executar_extracao_inteligente(
            dias_retroativos=1,
            salvar_arquivos=False
        )
        
        # Registra fim
        if execucao_id:
            self._registrar_execucao_fim(execucao_id, resultado)
        
        return resultado
    
    def get_status(self):
        try:
            job = self.scheduler.get_job("extracao_diaria")
            
            # Informações detalhadas
            status = {
                "ativo": self.config.get("ativo", False),
                "configuracao": self.config,
                "scheduler_running": self.scheduler.running,
                "job_exists": job is not None,
                "proxima_execucao": None,
                "proxima_execucao_brasil": None,
                "ultima_execucao": None,
                "hora_atual_utc": datetime.utcnow().isoformat(),
                "hora_atual_brasil": datetime.now().isoformat(),
                "estatisticas": {"total_extraidos": 0, "total_erros": 0}
            }
            
            if job and hasattr(job, 'next_run_time') and job.next_run_time:
                status["proxima_execucao"] = job.next_run_time.isoformat()
                # Converte para horário do Brasil para visualização
                import pytz
                brasil_tz = pytz.timezone('America/Sao_Paulo')
                proxima_brasil = job.next_run_time.astimezone(brasil_tz)
                status["proxima_execucao_brasil"] = proxima_brasil.strftime("%d/%m/%Y %H:%M:%S %Z")
            
            # Busca última execução
            status["ultima_execucao"] = self.config.get("ultima_execucao")
            
            return status
        except Exception as e:
            print(f"Erro ao obter status do scheduler: {e}")
            return {
                "ativo": False,
                "configuracao": {},
                "scheduler_running": False,
                "job_exists": False,
                "proxima_execucao": None,
                "proxima_execucao_brasil": None,
                "ultima_execucao": None,
                "hora_atual_utc": datetime.utcnow().isoformat(),
                "hora_atual_brasil": datetime.now().isoformat(),
                "estatisticas": {"total_extraidos": 0, "total_erros": 0},
                "erro": str(e)
            }


# Instâncias globais (lazy initialization)
extrator = None
scheduler = None

# Sistema de eventos em tempo real
extraction_events = {}
active_extractions = {}

def get_extrator():
    """Inicializa extrator apenas quando necessário"""
    global extrator
    if extrator is None:
        extrator = PNCPExtractor()
    return extrator

def get_scheduler():
    """Inicializa scheduler apenas quando necessário"""
    global scheduler
    if scheduler is None:
        scheduler = SchedulerSimples(get_extrator())
    return scheduler

def generate_task_id():
    """Gera ID único para tarefa de extração"""
    import uuid
    return str(uuid.uuid4())[:8]

def add_extraction_event(task_id, event_type, message, data=None):
    """Adiciona evento de extração"""
    global extraction_events
    if task_id not in extraction_events:
        extraction_events[task_id] = []
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,  # info, success, warning, error, progress
        "message": message,
        "data": data or {}
    }
    extraction_events[task_id].append(event)
    
    # Mantém apenas últimos 100 eventos por tarefa
    if len(extraction_events[task_id]) > 100:
        extraction_events[task_id] = extraction_events[task_id][-100:]

def get_extraction_events(task_id):
    """Retorna eventos de uma tarefa"""
    return extraction_events.get(task_id, [])

def clear_extraction_events(task_id=None):
    """Limpa eventos de extração"""
    global extraction_events
    if task_id:
        extraction_events.pop(task_id, None)
    else:
        extraction_events.clear()

async def executar_extracao_com_eventos(extrator, task_id, dias_retroativos=1, salvar_arquivos=False):
    """Executa extração com feedback em tempo real"""
    try:
        # Atualiza status
        active_extractions[task_id]["status"] = "buscando_editais"
        
        # Busca editais
        add_extraction_event(task_id, "info", f"📅 Buscando editais dos últimos {dias_retroativos} dia(s)...")
        
        data_final = datetime.now().date()
        data_inicial = data_final - timedelta(days=dias_retroativos)
        
        add_extraction_event(task_id, "info", f"📊 Período: {data_inicial} a {data_final}")
        
        # Busca editais para cada dia
        todos_editais = []
        for dia_offset in range(dias_retroativos, -1, -1):
            data_extracao = data_final - timedelta(days=dia_offset)
            add_extraction_event(task_id, "info", f"🔍 Buscando editais de {data_extracao}...")
            
            editais_encontrados = extrator.buscar_editais_recentes(
                data_filtro=data_extracao,
                max_paginas=50,
                limit_por_pagina=100
            )
            
            if editais_encontrados:
                todos_editais.extend(editais_encontrados)
                add_extraction_event(task_id, "success", f"✅ Encontrados {len(editais_encontrados)} editais em {data_extracao}")
            else:
                add_extraction_event(task_id, "warning", f"⚠️ Nenhum edital encontrado em {data_extracao}")
        
        if not todos_editais:
            add_extraction_event(task_id, "warning", "⚠️ Nenhum edital encontrado no período")
            return {
                "success": False,
                "message": "Nenhum edital encontrado no período",
                "total_encontrados": 0,
                "total_novos": 0,
                "total_atualizados": 0,
                "total_erros": 0,
                "tempo_execucao": 0
            }
        
        # Atualiza status
        active_extractions[task_id]["status"] = "processando_editais"
        active_extractions[task_id]["total_editais"] = len(todos_editais)
        
        add_extraction_event(task_id, "info", f"🚀 Iniciando processamento de {len(todos_editais)} editais...")
        
        # Processa cada edital
        novos_total = []
        atualizados_total = []
        erros_total = []
        
        for i, edital_basico in enumerate(todos_editais, 1):
            try:
                id_pncp = edital_basico.get("id_pncp")
                if not id_pncp:
                    continue
                
                # Atualiza progresso
                progresso = (i / len(todos_editais)) * 100
                add_extraction_event(task_id, "progress", f"📋 Processando {i}/{len(todos_editais)}: {id_pncp}", {
                    "progresso": round(progresso, 1),
                    "atual": i,
                    "total": len(todos_editais),
                    "id_pncp": id_pncp
                })
                
                # Verifica se já existe
                existing = extrator.supabase.table("editais_completos")\
                    .select("id, ultima_atualizacao, data_coleta")\
                    .eq("id_pncp", id_pncp)\
                    .execute()
                
                edital_existente = None
                deve_extrair = True
                
                if existing.data:
                    edital_existente = existing.data[0]
                    ultima_coleta = edital_existente.get("data_coleta")
                    
                    if ultima_coleta:
                        data_coleta = datetime.fromisoformat(ultima_coleta.replace('Z', '+00:00'))
                        hoje = datetime.now()
                        
                        if data_coleta.date() == hoje.date():
                            add_extraction_event(task_id, "info", f"⏭️ {id_pncp} já foi coletado hoje - pulando")
                            deve_extrair = False
                        else:
                            add_extraction_event(task_id, "info", f"🔄 {id_pncp} será atualizado")
                    else:
                        add_extraction_event(task_id, "info", f"🔄 {id_pncp} será atualizado (sem data de coleta)")
                else:
                    add_extraction_event(task_id, "info", f"✨ {id_pncp} é um novo edital")
                
                # Extrai se necessário
                if deve_extrair:
                    add_extraction_event(task_id, "info", f"🔍 Extraindo dados completos de {id_pncp}...")
                    
                    dados_completos = extrator.extrair_edital_completo_hibrido(id_pncp, salvar_arquivos=salvar_arquivos)
                    
                    if dados_completos:
                        add_extraction_event(task_id, "success", f"✅ Dados extraídos de {id_pncp}")
                        
                        # Salva no banco
                        supabase_id = extrator.salvar_supabase(dados_completos)
                        if supabase_id:
                            if edital_existente:
                                atualizados_total.append(id_pncp)
                                add_extraction_event(task_id, "success", f"💾 {id_pncp} atualizado (ID: {supabase_id})")
                            else:
                                novos_total.append(id_pncp)
                                add_extraction_event(task_id, "success", f"💾 {id_pncp} inserido (ID: {supabase_id})")
                        else:
                            add_extraction_event(task_id, "error", f"❌ Falha ao salvar {id_pncp}")
                            erros_total.append({"id_pncp": id_pncp, "erro": "Falha ao salvar no Supabase"})
                    else:
                        add_extraction_event(task_id, "error", f"❌ Falha na extração de {id_pncp}")
                        erros_total.append({"id_pncp": id_pncp, "erro": "Falha na extração de dados"})
                
                await asyncio.sleep(0.2)  # Pausa entre editais
                
            except Exception as e:
                add_extraction_event(task_id, "error", f"❌ Erro ao processar {id_pncp}: {str(e)}")
                erros_total.append({"id_pncp": id_pncp, "erro": str(e)})
        
        # Resultado final
        add_extraction_event(task_id, "success", f"🎉 Processamento concluído!", {
            "total_encontrados": len(todos_editais),
            "total_novos": len(novos_total),
            "total_atualizados": len(atualizados_total),
            "total_erros": len(erros_total)
        })
        
        return {
            "success": True,
            "message": f"Extração concluída: {len(novos_total)} novos, {len(atualizados_total)} atualizados, {len(erros_total)} erros",
            "total_encontrados": len(todos_editais),
            "total_novos": len(novos_total),
            "total_atualizados": len(atualizados_total),
            "total_erros": len(erros_total),
            "tempo_execucao": 0,  # Será calculado pelo extrator
            "editais_novos": novos_total,
            "editais_atualizados": atualizados_total,
            "erros": erros_total
        }
        
    except Exception as e:
        add_extraction_event(task_id, "error", f"❌ Erro geral na extração: {str(e)}")
        raise e


# ========================================
# ENDPOINTS
# ========================================

@app.get("/", 
         summary="Página inicial",
         description="Informações gerais da API e endpoints disponíveis")
async def root():
    return {
        "message": f"{settings.API_TITLE}",
        "version": settings.API_VERSION,
        "status": "Online",
        "fluxo_recomendado": {
            "1_primeira_vez": "POST /executar-historico (extrai últimos 15 dias)",
            "2_configurar": "POST /configurar-scheduler (ativa extração diária)",
            "3_automatico": "Scheduler roda às 06:00 diariamente"
        },
        "endpoints_principais": {
            "historico": "POST /executar-historico - Extrai 15 dias (primeira execução)",
            "agora": "POST /executar-agora - Extrai dia anterior (teste)",
            "scheduler": "POST /configurar-scheduler - Configura execução automática",
            "status": "GET /scheduler/status - Status do scheduler",
            "execucoes": "GET /scheduler/execucoes - Histórico de execuções"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "interface_web": "/dashboard",
        "estrategia": "Método inteligente: não duplica, atualiza apenas mudanças"
    }

@app.get("/dashboard")
async def dashboard():
    """Serve a interface web do dashboard"""
    from fastapi.responses import FileResponse
    import os
    html_path = os.path.join(os.path.dirname(__file__), "..", "public", "index.html")
    return FileResponse(html_path)


@app.get("/health", 
         response_model=HealthResponse,
         summary="Health Check",
         description="Verifica o status da API e conexões com serviços externos")
async def health():
    # Testa conexão com Supabase
    supabase_status = "disconnected"
    try:
        ext = get_extrator()
        result = ext.supabase.table("editais_completos").select("id").limit(1).execute()
        supabase_status = "connected"
    except:
        supabase_status = "error"
    
    return HealthResponse(
        status="healthy" if supabase_status == "connected" else " degraded",
        timestamp=datetime.now().isoformat(),
        services={
            "supabase": f" {supabase_status}" if supabase_status == "connected" else f"{supabase_status}",
            "selenium": " disponível",
            "storage_bucket": settings.STORAGE_BUCKET
        },
        environment={
            "python_version": "3.11+",
            "fastapi_version": "0.104+",
            "supabase_configured": settings.is_configured()
        }
    )


@app.post("/configurar-scheduler",
          response_model=EditalResponse,
          summary="⚙️ Configurar Scheduler",
          description="Configura a extração automática diária de editais")
async def configurar_scheduler(config: ConfigScheduler):
    """Configura extração automática diária"""
    try:
        print(f"🔧 Configurando scheduler: Ativo={config.ativo}, Hora={config.hora}")
        
        sch = get_scheduler()
        sch.configurar(config.ativo, config.hora)
        
        status = sch.get_status()
        
        return EditalResponse(
            success=True,
            message=f"Scheduler {'ativado' if config.ativo else 'desativado'}",
            data={
                "configuracao": config.dict(),
                "status": status
            }
        )
        
    except Exception as e:
        print(f"❌ Erro ao configurar scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scheduler/status",
         response_model=StatusSchedulerResponse,
         summary="Status do Scheduler",
         description="Retorna o status atual do scheduler")
async def status_scheduler():
    """Retorna status do scheduler"""
    try:
        sch = get_scheduler()
        status = sch.get_status()
        
        return StatusSchedulerResponse(
            ativo=status["ativo"],
            proxima_execucao=status["proxima_execucao"],
            ultima_execucao=status["ultima_execucao"],
            configuracao=status["configuracao"],
            estatisticas=status["estatisticas"]
        )
        
    except Exception as e:
        print(f"❌ Erro ao obter status do scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/executar-historico",
          response_model=EditalResponse,
          summary="Extração Histórica (15 dias)",
          description="Extrai TODOS os editais dos últimos 15 dias (primeira execução)")
async def executar_historico():
    """Extrai editais dos últimos 15 dias - USE NA PRIMEIRA VEZ"""
    task_id = generate_task_id()
    
    try:
        # Marca extração como ativa
        active_extractions[task_id] = {
            "tipo": "executar_historico",
            "inicio": datetime.now().isoformat(),
            "status": "iniciando"
        }
        
        add_extraction_event(task_id, "info", "🚀 Iniciando extração histórica (15 dias)...")
        
        ext = get_extrator()
        add_extraction_event(task_id, "info", "✅ Extrator inicializado com sucesso")
        
        add_extraction_event(task_id, "info", "🔍 Iniciando busca de editais históricos...")
        
        # Executa extração com eventos
        resultado = await executar_extracao_com_eventos(
            ext, task_id, dias_retroativos=15, salvar_arquivos=True
        )
        
        add_extraction_event(task_id, "success", f"🎉 Extração histórica concluída!", {
            "total_encontrados": resultado.get("total_encontrados", 0),
            "total_novos": resultado.get("total_novos", 0),
            "total_atualizados": resultado.get("total_atualizados", 0),
            "total_erros": resultado.get("total_erros", 0),
            "tempo_execucao": resultado.get("tempo_execucao", 0)
        })
        
        # Remove da lista de extrações ativas
        active_extractions.pop(task_id, None)
        
        return EditalResponse(
            success=resultado["success"],
            message=resultado["message"],
            data={**resultado, "task_id": task_id},
            tempo_execucao=resultado.get("tempo_execucao")
        )
        
    except Exception as e:
        add_extraction_event(task_id, "error", f"❌ Erro na extração histórica: {str(e)}")
        active_extractions.pop(task_id, None)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/executar-agora",
          response_model=EditalResponse,
          summary="Executar Agora (1 dia)",
          description="Executa a extração do dia anterior imediatamente (método inteligente)")
async def executar_agora():
    """Executa extração do dia anterior (teste rápido)"""
    task_id = generate_task_id()
    
    try:
        # Marca extração como ativa
        active_extractions[task_id] = {
            "tipo": "executar_agora",
            "inicio": datetime.now().isoformat(),
            "status": "iniciando"
        }
        
        add_extraction_event(task_id, "info", "🚀 Iniciando extração do dia anterior...")
        
        ext = get_extrator()
        add_extraction_event(task_id, "info", "✅ Extrator inicializado com sucesso")
        
        add_extraction_event(task_id, "info", "🔍 Iniciando busca de editais...")
        
        # Executa extração com eventos
        resultado = await executar_extracao_com_eventos(
            ext, task_id, dias_retroativos=1, salvar_arquivos=True
        )
        
        add_extraction_event(task_id, "success", f"🎉 Extração concluída com sucesso!", {
            "total_encontrados": resultado.get("total_encontrados", 0),
            "total_novos": resultado.get("total_novos", 0),
            "total_atualizados": resultado.get("total_atualizados", 0),
            "total_erros": resultado.get("total_erros", 0),
            "tempo_execucao": resultado.get("tempo_execucao", 0)
        })
        
        # Remove da lista de extrações ativas
        active_extractions.pop(task_id, None)
        
        return EditalResponse(
            success=resultado["success"],
            message=resultado["message"],
            data={**resultado, "task_id": task_id},
            tempo_execucao=resultado.get("tempo_execucao")
        )
        
    except Exception as e:
        add_extraction_event(task_id, "error", f"❌ Erro na extração: {str(e)}")
        active_extractions.pop(task_id, None)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scheduler/execucoes",
         summary="Histórico de Execuções",
         description="Retorna histórico das execuções do scheduler")
async def historico_execucoes(limit: int = 10):
    """Retorna últimas execuções do scheduler"""
    try:
        ext = get_extrator()
        result = ext.supabase.table("scheduler_execucoes")\
            .select("*")\
            .order("data_inicio", desc=True)\
            .limit(limit)\
            .execute()
        
        return EditalResponse(
            success=True,
            message=f"Últimas {limit} execuções",
            data={
                "execucoes": result.data or [],
                "total": len(result.data) if result.data else 0
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/estatisticas",
         summary="Estatísticas Gerais",
         description="Retorna estatísticas gerais da base de dados")
async def estatisticas_gerais():
    """Retorna estatísticas gerais"""
    try:
        ext = get_extrator()
        sch = get_scheduler()
        
        # Total de editais
        total_result = ext.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .execute()
        
        # Editais recentes
        data_limite = (datetime.now() - timedelta(days=7)).isoformat()
        recentes_result = ext.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .gte("created_at", data_limite)\
            .execute()
        
        return EditalResponse(
            success=True,
            message="Estatísticas gerais",
            data={
                "total_editais": total_result.count or 0,
                "editais_ultimos_7_dias": recentes_result.count or 0,
                "scheduler": {"total_extraidos": 0, "total_erros": 0},
                "ultima_atualizacao": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/editais", summary="Listar Editais", description="Retorna lista de editais extraídos")
async def listar_editais(limit: int = 20, offset: int = 0):
    """Retorna lista de editais"""
    try:
        ext = get_extrator()
        
        result = ext.supabase.table("editais_completos")\
            .select("id, id_pncp, edital, modalidade, valor, orgao, situacao, data_divulgacao_pncp, created_at, total_itens, total_anexos, total_historico, itens, anexos, historico, cnpj_orgao, ano, numero, local, objeto, link_licitacao")\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return {
            "editais": result.data,
            "total": len(result.data),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/editais/{id_pncp}")
async def buscar_edital_individual(id_pncp: str):
    """Retorna dados completos de um edital específico"""
    try:
        ext = get_extrator()
        
        result = ext.supabase.table("editais_completos")\
            .select("*")\
            .eq("id_pncp", id_pncp)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Edital não encontrado")
        
        edital = result.data[0]
        
        return {
            "success": True,
            "data": edital,
            "message": "Edital encontrado com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/editais/{id_pncp}/documentos")
async def listar_documentos_edital(id_pncp: str):
    """Retorna lista de documentos do edital"""
    try:
        ext = get_extrator()
        
        result = ext.supabase.table("editais_completos")\
            .select("anexos, id_pncp")\
            .eq("id_pncp", id_pncp)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Edital não encontrado")
        
        edital = result.data[0]
        anexos = edital.get("anexos", [])
        
        documentos = []
        if anexos:
            for anexo in anexos:
                documentos.append({
                    "nome": anexo.get("nome", "Documento"),
                    "url": anexo.get("url", ""),
                    "tamanho": anexo.get("tamanho", "N/A"),
                    "tipo": anexo.get("tipo", "application/octet-stream")
                })
        
        return {
            "id_pncp": id_pncp,
            "documentos": documentos,
            "total": len(documentos)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/editais/{id_pncp}/download/{documento_id}")
async def download_documento(id_pncp: str, documento_id: int):
    """Baixa um documento específico do edital"""
    try:
        ext = get_extrator()
        
        result = ext.supabase.table("editais_completos")\
            .select("anexos")\
            .eq("id_pncp", id_pncp)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Edital não encontrado")
        
        edital = result.data[0]
        anexos = edital.get("anexos", [])
        
        if documento_id >= len(anexos):
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        
        documento = anexos[documento_id]
        
        if documento.get("url"):
            return {
                "success": True,
                "url": documento["url"],
                "nome": documento.get("nome", "documento"),
                "tamanho": documento.get("tamanho", "N/A")
            }
        else:
            raise HTTPException(status_code=404, detail="Documento não disponível para download")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/extracao/progresso/{task_id}")
async def obter_progresso_extracao(task_id: str):
    """Obtém progresso da extração em tempo real"""
    try:
        # Por enquanto retorna status básico
        # Futuramente implementaremos WebSocket ou Server-Sent Events
        return {
            "task_id": task_id,
            "status": "em_andamento",
            "progresso": 0,
            "total_editais": 0,
            "processados": 0,
            "novos": 0,
            "atualizados": 0,
            "erros": 0,
            "logs": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/extracao/events/{task_id}")
async def obter_eventos_extracao(task_id: str):
    """Server-Sent Events para feedback em tempo real da extração"""
    async def gerar_eventos():
        # Envia eventos existentes primeiro
        eventos_existentes = get_extraction_events(task_id)
        for evento in eventos_existentes:
            yield f"data: {json.dumps(evento)}\n\n"
        
        # Monitora novos eventos
        ultimo_evento = len(eventos_existentes)
        while True:
            await asyncio.sleep(0.5)  # Verifica a cada 500ms
            
            eventos_atuais = get_extraction_events(task_id)
            
            # Se há novos eventos, envia
            if len(eventos_atuais) > ultimo_evento:
                for evento in eventos_atuais[ultimo_evento:]:
                    yield f"data: {json.dumps(evento)}\n\n"
                ultimo_evento = len(eventos_atuais)
            
            # Se a extração terminou, para o loop
            if task_id not in active_extractions:
                break
    
    return StreamingResponse(gerar_eventos(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control"
    })

@app.get("/extracao/logs/{task_id}")
async def obter_logs_extracao(task_id: str):
    """Stream de logs da extração em tempo real (legado)"""
    async def gerar_logs():
        eventos = get_extraction_events(task_id)
        for evento in eventos:
            yield f"data: [{evento['type'].upper()}] {evento['message']}\n\n"
            await asyncio.sleep(0.1)
    
    return StreamingResponse(gerar_logs(), media_type="text/plain")


# Inicialização
@app.on_event("startup")
async def startup_event():
    """Eventos de inicialização"""
    print("PNCP Extrator iniciado!")
    print(f"Ambiente: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Validar configurações
    from .core.config import settings
    try:
        settings.validate_config()
    except Exception as e:
        print(f"ERRO de configuracao: {e}")
        print("Verifique o arquivo .env")
        exit(1)
    
    # Inicializar scheduler
    try:
        print("Inicializando scheduler...")
        scheduler = get_scheduler()
        scheduler.inicializar_scheduler()
        print("Scheduler inicializado com sucesso!")
    except Exception as e:
        print(f"Erro ao inicializar scheduler: {e}")
    
    print("API pronta para receber requisições")


@app.on_event("shutdown")
async def shutdown_event():
    """Eventos de finalização"""
    global scheduler
    if scheduler and scheduler.scheduler.running:
        scheduler.scheduler.shutdown()
    print("PNCP Extrator finalizado!")