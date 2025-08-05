"""
API Principal do PNCP Extrator
"""

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
        print("🤖 EXECUÇÃO AUTOMÁTICA INICIADA (INTELIGENTE)")
        await self.extrator.executar_extracao_inteligente(
            salvar_arquivos=False,  # Não salva arquivos automaticamente
            max_editais=25  # Limite otimizado para execução automática
        )
    
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
          description="Executa a extração inteligente do dia anterior imediatamente")
async def executar_agora():
    """2️⃣ Executa extração inteligente do dia anterior imediatamente"""
    try:
        # Executa em background com estratégia inteligente
        task = asyncio.create_task(
            extrator.executar_extracao_inteligente(
                salvar_arquivos=False,  # Não salva arquivos por padrão
                max_editais=30  # Limite otimizado
            )
        )
        
        return EditalResponse(
            success=True,
            message="Extração inteligente iniciada em background",
            data={
                "data_extracao": str((datetime.now() - timedelta(days=1)).date()),
                "configuracao": {
                    "max_editais": 30,
                    "salvar_arquivos": False,
                    "max_paginas": 3,
                    "limit_por_pagina": 25,
                    "estrategia": "inteligente"
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extrair-dia-anterior",
          response_model=EditalResponse,
          summary="📅 Extrair Dia Anterior",
          description="Extrai editais do dia anterior com estratégia inteligente")
async def extrair_dia_anterior(request: ExtrairDiaRequest):
    """3️⃣ Extrai editais do dia anterior com estratégia inteligente"""
    try:
        data_extracao = request.data
        if not data_extracao:
            data_extracao = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Configurações para extração inteligente
        salvar_arquivos = getattr(request, 'salvar_arquivos', False)
        max_editais = getattr(request, 'max_editais', 30)
        
        resultado = await extrator.executar_extracao_inteligente(
            data_extracao=data_extracao,
            salvar_arquivos=salvar_arquivos,
            max_editais=max_editais
        )
        
        return EditalResponse(
            success=resultado["success"],
            message=resultado["message"],
            data=resultado,
            tempo_execucao=resultado.get("tempo_execucao")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extrair-completo",
          response_model=EditalResponse,
          summary="📦 Extrair Completo",
          description="Extrai editais com arquivos usando estratégia inteligente")
async def extrair_completo(request: ExtrairDiaRequest):
    """4️⃣ Extrai editais com arquivos usando estratégia inteligente"""
    try:
        data_extracao = request.data
        if not data_extracao:
            data_extracao = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Configurações para extração completa inteligente
        salvar_arquivos = True  # Força salvar arquivos
        max_editais = min(getattr(request, 'max_editais', 10), 10)  # Máximo 10 para economizar
        
        resultado = await extrator.executar_extracao_inteligente(
            data_extracao=data_extracao,
            salvar_arquivos=salvar_arquivos,
            max_editais=max_editais
        )
        
        return EditalResponse(
            success=resultado["success"],
            message=f"Extração completa inteligente concluída - {resultado['message']}",
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


@app.get("/dashboard/resumo",
         summary="📈 Resumo Executivo",
         description="Retorna resumo executivo com principais métricas")
async def resumo_executivo():
    """Retorna resumo executivo"""
    try:
        # Busca dados da view de resumo executivo
        result = extrator.supabase.rpc("get_resumo_executivo").execute()
        
        if result.data:
            return EditalResponse(
                success=True,
                message="Resumo executivo",
                data=result.data[0] if result.data else {}
            )
        else:
            # Fallback se a view não existir
            total_result = extrator.supabase.table("editais_completos")\
                .select("id", count="exact")\
                .execute()
            
            return EditalResponse(
                success=True,
                message="Resumo executivo (fallback)",
                data={
                    "total_editais": total_result.count or 0,
                    "editais_ultimos_7_dias": 0,
                    "editais_ultimos_30_dias": 0,
                    "valor_total_editais": 0,
                    "valor_medio_editais": 0,
                    "total_orgaos": 0,
                    "total_modalidades": 0,
                    "total_locais": 0,
                    "ultima_atualizacao": datetime.now().isoformat(),
                    "editais_hoje": 0
                }
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/estatisticas-por-orgao",
         summary="🏢 Estatísticas por Órgão",
         description="Retorna estatísticas agrupadas por órgão")
async def estatisticas_por_orgao():
    """Retorna estatísticas por órgão"""
    try:
        result = extrator.supabase.table("editais_completos")\
            .select("orgao, total_editais, valor_total, valor_medio")\
            .not_.is_("orgao", "null")\
            .execute()
        
        # Agrupa por órgão
        orgaos = {}
        for row in result.data:
            orgao = row.get("orgao", "Sem órgão")
            if orgao not in orgaos:
                orgaos[orgao] = {
                    "orgao": orgao,
                    "total_editais": 0,
                    "valor_total": 0,
                    "valor_medio": 0
                }
            orgaos[orgao]["total_editais"] += 1
            orgaos[orgao]["valor_total"] += row.get("valor_total_numerico", 0)
        
        # Calcula médias
        for orgao in orgaos.values():
            if orgao["total_editais"] > 0:
                orgao["valor_medio"] = orgao["valor_total"] / orgao["total_editais"]
        
        return EditalResponse(
            success=True,
            message="Estatísticas por órgão",
            data=list(orgaos.values())
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/estatisticas-diarias",
         summary="📅 Estatísticas Diárias",
         description="Retorna estatísticas dos últimos 30 dias")
async def estatisticas_diarias():
    """Retorna estatísticas diárias"""
    try:
        data_limite = (datetime.now() - timedelta(days=30)).isoformat()
        
        result = extrator.supabase.table("editais_completos")\
            .select("created_at, valor_total_numerico, valor_sigiloso, anexos_processados, itens_processados")\
            .gte("created_at", data_limite)\
            .execute()
        
        # Agrupa por dia
        dias = {}
        for row in result.data:
            data = row.get("created_at", "")[:10]  # YYYY-MM-DD
            if data not in dias:
                dias[data] = {
                    "data": data,
                    "total_editais": 0,
                    "valor_total": 0,
                    "editais_sigilosos": 0,
                    "editais_com_anexos": 0,
                    "editais_com_itens": 0
                }
            
            dias[data]["total_editais"] += 1
            dias[data]["valor_total"] += row.get("valor_total_numerico", 0)
            if row.get("valor_sigiloso"):
                dias[data]["editais_sigilosos"] += 1
            if row.get("anexos_processados"):
                dias[data]["editais_com_anexos"] += 1
            if row.get("itens_processados"):
                dias[data]["editais_com_itens"] += 1
        
        return EditalResponse(
            success=True,
            message="Estatísticas diárias",
            data=list(dias.values())
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/alertas",
         summary="⚠️ Alertas e Problemas",
         description="Retorna alertas sobre problemas na base de dados")
async def alertas_problemas():
    """Retorna alertas e problemas"""
    try:
        # Editais sem anexos
        sem_anexos = extrator.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .eq("anexos_processados", False)\
            .execute()
        
        # Editais sem itens
        sem_itens = extrator.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .eq("itens_processados", False)\
            .execute()
        
        # Editais sem valor
        sem_valor = extrator.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .or_("valor_total_numerico.eq.0,valor_total_numerico.is.null")\
            .execute()
        
        alertas = [
            {
                "tipo": "editais_sem_anexos",
                "quantidade": sem_anexos.count or 0,
                "descricao": "Editais sem anexos processados",
                "severidade": "baixa"
            },
            {
                "tipo": "editais_sem_itens",
                "quantidade": sem_itens.count or 0,
                "descricao": "Editais sem itens processados",
                "severidade": "média"
            },
            {
                "tipo": "editais_sem_valor",
                "quantidade": sem_valor.count or 0,
                "descricao": "Editais sem valor informado",
                "severidade": "baixa"
            }
        ]
        
        return EditalResponse(
            success=True,
            message="Alertas e problemas",
            data=alertas
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/editais-recentes",
         summary="🆕 Editais Recentes",
         description="Retorna os editais mais recentes")
async def editais_recentes(limit: int = 20):
    """Retorna editais recentes"""
    try:
        data_limite = (datetime.now() - timedelta(days=7)).isoformat()
        
        result = extrator.supabase.table("editais_completos")\
            .select("id, id_pncp, edital, orgao, modalidade, valor, situacao, created_at")\
            .gte("created_at", data_limite)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return EditalResponse(
            success=True,
            message="Editais recentes",
            data=result.data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/editais-mais-valiosos",
         summary="💰 Editais Mais Valiosos",
         description="Retorna os editais com maior valor")
async def editais_mais_valiosos(limit: int = 20):
    """Retorna editais mais valiosos"""
    try:
        result = extrator.supabase.table("editais_completos")\
            .select("id, id_pncp, edital, orgao, modalidade, valor, valor_total_numerico, created_at")\
            .gt("valor_total_numerico", 0)\
            .order("valor_total_numerico", desc=True)\
            .limit(limit)\
            .execute()
        
        return EditalResponse(
            success=True,
            message="Editais mais valiosos",
            data=result.data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/performance",
         summary="⚡ Performance de Extração",
         description="Retorna métricas de performance da extração")
async def performance_extracao():
    """Retorna métricas de performance"""
    try:
        # Estatísticas gerais de processamento
        total = extrator.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .execute()
        
        anexos_processados = extrator.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .eq("anexos_processados", True)\
            .execute()
        
        itens_processados = extrator.supabase.table("editais_completos")\
            .select("id", count="exact")\
            .eq("itens_processados", True)\
            .execute()
        
        # Performance dos últimos 7 dias
        data_limite = (datetime.now() - timedelta(days=7)).isoformat()
        performance_recente = extrator.supabase.table("editais_completos")\
            .select("tempo_extracao, total_anexos, total_itens")\
            .gte("created_at", data_limite)\
            .execute()
        
        tempo_medio = 0
        media_anexos = 0
        media_itens = 0
        
        if performance_recente.data:
            tempos = [row.get("tempo_extracao", 0) for row in performance_recente.data if row.get("tempo_extracao")]
            anexos = [row.get("total_anexos", 0) for row in performance_recente.data]
            itens = [row.get("total_itens", 0) for row in performance_recente.data]
            
            if tempos:
                tempo_medio = sum(tempos) / len(tempos)
            if anexos:
                media_anexos = sum(anexos) / len(anexos)
            if itens:
                media_itens = sum(itens) / len(itens)
        
        return EditalResponse(
            success=True,
            message="Performance de extração",
            data={
                "total_editais": total.count or 0,
                "anexos_processados": anexos_processados.count or 0,
                "itens_processados": itens_processados.count or 0,
                "tempo_medio_extracao": round(tempo_medio, 2),
                "media_anexos_por_edital": round(media_anexos, 2),
                "media_itens_por_edital": round(media_itens, 2),
                "periodo_analise": "últimos 7 dias"
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