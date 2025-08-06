from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
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


# Sistema de Scheduler
class SchedulerSimples:
    def __init__(self, extrator):
        self.extrator = extrator
        self.scheduler = AsyncIOScheduler()
        self.config = {"ativo": False, "hora": "06:00"}
    
    def configurar(self, ativo, hora):
        self.config = {"ativo": ativo, "hora": hora}
        
        # Remove job existente
        if self.scheduler.get_job("extracao_diaria"):
            self.scheduler.remove_job("extracao_diaria")
        
        if ativo:
            h, m = hora.split(":")
            
            # Log para debug
            print(f"🕐 Configurando scheduler para {hora} (Brasil)")
            print(f"🌍 Timezone: America/Sao_Paulo")
            
            self.scheduler.add_job(
                self.executar_automatico,
                CronTrigger(hour=int(h), minute=int(m), timezone="America/Sao_Paulo"),
                id="extracao_diaria",
                replace_existing=True
            )
            
            # Força inicialização
            if not self.scheduler.running:
                self.scheduler.start()
                print("✅ Scheduler iniciado com sucesso!")
            
            # Mostra próxima execução
            job = self.scheduler.get_job("extracao_diaria")
            if job and job.next_run_time:
                print(f"⏰ Próxima execução: {job.next_run_time}")
        else:
            print("❌ Scheduler desativado")
    
    async def executar_automatico(self):
        print("🤖 EXECUÇÃO AUTOMÁTICA INICIADA")
        await self.extrator.executar_extracao_dia()
    
    def get_status(self):
        job = self.scheduler.get_job("extracao_diaria")
        
        # Informações detalhadas
        status = {
            "ativo": self.config["ativo"],
            "configuracao": self.config,
            "scheduler_running": self.scheduler.running,
            "job_exists": job is not None,
            "proxima_execucao": None,
            "proxima_execucao_brasil": None,
            "hora_atual_utc": datetime.utcnow().isoformat(),
            "hora_atual_brasil": datetime.now().isoformat(),
            "estatisticas": {"total_extraidos": 0, "total_erros": 0}
        }
        
        if job and job.next_run_time:
            status["proxima_execucao"] = job.next_run_time.isoformat()
            # Converte para horário do Brasil para visualização
            import pytz
            brasil_tz = pytz.timezone('America/Sao_Paulo')
            proxima_brasil = job.next_run_time.astimezone(brasil_tz)
            status["proxima_execucao_brasil"] = proxima_brasil.strftime("%d/%m/%Y %H:%M:%S %Z")
        
        return status


# Instâncias globais
extrator = PNCPExtractor()
scheduler = SchedulerSimples(extrator)


# ========================================
# ENDPOINTS
# ========================================

@app.get("/", 
         summary="🏠 Página inicial",
         description="Informações gerais da API e endpoints disponíveis")
async def root():
    return {
        "message": f"{settings.API_TITLE}",
        "version": settings.API_VERSION,
        "status": "🟢 Online",
        "endpoints": {
            "1": "POST /configurar-scheduler - Configura extração automática",
            "2": "POST /executar-agora - Executa extração imediatamente",
            "3": "POST /extrair-dia-anterior - Extrai editais do dia anterior"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "exemplo_uso": {
            "configurar_scheduler": {
                "ativo": True,
                "hora": "06:00",
                "salvar_arquivos": True
            }
        }
    }


@app.get("/health", 
         response_model=HealthResponse,
         summary="🏥 Health Check",
         description="Verifica o status da API e conexões com serviços externos")
async def health():
    # Testa conexão com Supabase
    supabase_status = "disconnected"
    try:
        result = extrator.supabase.table("editais_completos").select("id").limit(1).execute()
        supabase_status = "connected"
    except:
        supabase_status = "error"
    
    return HealthResponse(
        status="🟢 healthy" if supabase_status == "connected" else "🟡 degraded",
        timestamp=datetime.now().isoformat(),
        services={
            "supabase": f"🟢 {supabase_status}" if supabase_status == "connected" else f"🔴 {supabase_status}",
            "selenium": "🟢 disponível",
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
    """1️⃣ Configura extração automática diária"""
    try:
        scheduler.configurar(config.ativo, config.hora)
        
        return EditalResponse(
            success=True,
            message=f"Scheduler {'ativado' if config.ativo else 'desativado'}",
            data={
                "configuracao": config.dict(),
                "status": scheduler.get_status()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scheduler/status",
         response_model=StatusSchedulerResponse,
         summary="📊 Status do Scheduler",
         description="Retorna o status atual do scheduler")
async def status_scheduler():
    """Retorna status do scheduler"""
    try:
        status = scheduler.get_status()
        
        return StatusSchedulerResponse(
            ativo=status["ativo"],
            proxima_execucao=status["proxima_execucao"],
            ultima_execucao=status["ultima_execucao"],
            configuracao=status["configuracao"],
            estatisticas=status["estatisticas"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/executar-agora",
          response_model=EditalResponse,
          summary="▶️ Executar Agora",
          description="Executa a extração do dia anterior imediatamente")
async def executar_agora():
    """2️⃣ Executa extração do dia anterior imediatamente"""
    try:
        # Executa em background
        task = asyncio.create_task(extrator.executar_extracao_dia())
        
        return EditalResponse(
            success=True,
            message="Extração iniciada em background",
            data={
                "data_extracao": str((datetime.now() - timedelta(days=1)).date()),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extrair-dia-anterior",
          response_model=EditalResponse,
          summary="📅 Extrair Dia Anterior",
          description="Extrai editais do dia anterior (ou data específica)")
async def extrair_dia_anterior(request: ExtrairDiaRequest):
    """3️⃣ Extrai editais do dia anterior (ou data específica)"""
    try:
        data_extracao = request.data
        if not data_extracao:
            data_extracao = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        resultado = await extrator.executar_extracao_dia(data_extracao)
        
        return EditalResponse(
            success=resultado["success"],
            message=resultado["message"],
            data=resultado,
            tempo_execucao=resultado.get("tempo_execucao")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/estatisticas",
         summary="📊 Estatísticas Gerais",
         description="Retorna estatísticas gerais da base de dados")
async def estatisticas_gerais():
    """Retorna estatísticas gerais"""
    try:
        # Total de editais
        total_result = extrator.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .execute()
        
        # Editais recentes
        data_limite = (datetime.now() - timedelta(days=7)).isoformat()
        recentes_result = extrator.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .gte("created_at", data_limite)\
            .execute()
        
        return EditalResponse(
            success=True,
            message="Estatísticas gerais",
            data={
                "total_editais": total_result.count or 0,
                "editais_ultimos_7_dias": recentes_result.count or 0,
                "scheduler": scheduler.get_status()["estatisticas"],
                "ultima_atualizacao": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/scheduler",
         summary="🔧 Debug Scheduler",
         description="Informações detalhadas do scheduler para debug")
async def debug_scheduler():
    """Debug completo do scheduler"""
    import pytz
    
    job = scheduler.scheduler.get_job("extracao_diaria")
    brasil_tz = pytz.timezone('America/Sao_Paulo')
    utc_now = datetime.utcnow()
    brasil_now = utc_now.replace(tzinfo=pytz.UTC).astimezone(brasil_tz)
    
    debug_info = {
        "scheduler_running": scheduler.scheduler.running,
        "config": scheduler.config,
        "job_exists": job is not None,
        "horarios": {
            "utc_atual": utc_now.isoformat(),
            "brasil_atual": brasil_now.strftime("%d/%m/%Y %H:%M:%S %Z"),
            "render_timezone": "UTC (padrão)"
        }
    }
    
    if job:
        debug_info["job_info"] = {
            "id": job.id,
            "next_run_utc": job.next_run_time.isoformat() if job.next_run_time else None,
            "next_run_brasil": job.next_run_time.astimezone(brasil_tz).strftime("%d/%m/%Y %H:%M:%S %Z") if job.next_run_time else None,
            "trigger": str(job.trigger)
        }
    
    return debug_info


@app.post("/debug/test-scheduler",
          summary="🧪 Testar Scheduler",
          description="Configura scheduler para executar em 2 minutos (teste)")
async def test_scheduler():
    """Configura scheduler para teste em 2 minutos"""
    import pytz
    
    # Calcula horário 2 minutos no futuro (Brasil)
    brasil_tz = pytz.timezone('America/Sao_Paulo')
    agora_brasil = datetime.now(brasil_tz)
    teste_horario = agora_brasil + timedelta(minutes=2)
    hora_teste = teste_horario.strftime("%H:%M")
    
    # Configura scheduler
    scheduler.configurar(True, hora_teste)
    
    return {
        "message": f"Scheduler configurado para teste em 2 minutos",
        "horario_atual_brasil": agora_brasil.strftime("%d/%m/%Y %H:%M:%S %Z"),
        "horario_teste": teste_horario.strftime("%d/%m/%Y %H:%M:%S %Z"),
        "configuracao": hora_teste,
        "status": scheduler.get_status()
    }


# Inicialização
@app.on_event("startup")
async def startup_event():
    """Eventos de inicialização"""
    print("🚀 PNCP Extrator iniciado!")
    print(f"📊 Configurações: {settings.is_configured()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Eventos de finalização"""
    if scheduler.scheduler.running:
        scheduler.scheduler.shutdown()
    print("👋 PNCP Extrator finalizado!")