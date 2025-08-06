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
        
        if self.scheduler.get_job("extracao_diaria"):
            self.scheduler.remove_job("extracao_diaria")
        
        if ativo:
            h, m = hora.split(":")
            self.scheduler.add_job(
                self.executar_automatico,
                CronTrigger(hour=int(h), minute=int(m), timezone="America/Sao_Paulo"),
                id="extracao_diaria"
            )
            
            if not self.scheduler.running:
                self.scheduler.start()
    
    async def executar_automatico(self):
        print("🤖 EXECUÇÃO AUTOMÁTICA INICIADA")
        await self.extrator.executar_extracao_dia()
    
    def get_status(self):
        job = self.scheduler.get_job("extracao_diaria")
        proxima_execucao = job.next_run_time.isoformat() if job and job.next_run_time else None
        
        return {
            "ativo": self.config["ativo"],
            "proxima_execucao": proxima_execucao,
            "ultima_execucao": None,  # TODO: implementar tracking
            "configuracao": self.config,
            "estatisticas": {"total_extraidos": 0, "total_erros": 0}  # TODO: implementar
        }


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