"""
Schemas Pydantic para validação de dados
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ConfigScheduler(BaseModel):
    """Configuração do scheduler"""
    ativo: bool = True
    hora: str = "06:00"
    salvar_arquivos: bool = False


class ExtrairDiaRequest(BaseModel):
    """Request para extração de dia específico com configurações otimizadas"""
    data: Optional[str] = None  # YYYY-MM-DD, se None usa dia anterior
    salvar_arquivos: bool = False  # Por padrão não salva arquivos para economizar espaço
    max_editais: int = 1000  # Limite alto para processar TODOS
    max_paginas: int = 20  # Máximo de páginas para cobertura total
    limit_por_pagina: int = 100  # Editais por página para eficiência


class EditalResponse(BaseModel):
    """Response padrão para operações com editais"""
    success: bool
    message: str
    data: Optional[Dict[Any, Any]] = None
    tempo_execucao: Optional[float] = None


class StatusSchedulerResponse(BaseModel):
    """Response do status do scheduler"""
    ativo: bool
    proxima_execucao: Optional[str] = None
    ultima_execucao: Optional[str] = None
    configuracao: Dict[str, Any]
    estatisticas: Dict[str, Any]


class HealthResponse(BaseModel):
    """Response do health check"""
    status: str
    timestamp: str
    services: Dict[str, str]
    environment: Optional[Dict[str, Any]] = None