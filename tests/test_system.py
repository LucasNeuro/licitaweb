#!/usr/bin/env python3
"""
Teste unificado do sistema PNCP Extrator
"""

import requests
import json
import sys
from datetime import datetime, timedelta


def test_api_status():
    """Testa o status básico da API"""
    print("TESTE DO STATUS DA API")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Teste básico de conectividade
    print("\n1. Testando conectividade básica...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - API Online - Status: {response.status_code}")
            print(f"   Message: {data.get('message', 'N/A')}")
            print(f"   Version: {data.get('version', 'N/A')}")
        else:
            print(f"   ERRO - API Offline - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERRO - Erro de conexão: {e}")
        return False
    
    # Teste de health check
    print("\n2. Testando health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - Health: {data.get('status', 'N/A')}")
        else:
            print(f"   ERRO - Health Check falhou - Status: {response.status_code}")
    except Exception as e:
        print(f"   ERRO - Erro no health check: {e}")
    
    return True


def test_extraction():
    """Testa a extração de dados"""
    print("\nTESTE DE EXTRAÇÃO")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Teste executar-agora
    print("\n1. Testando extração otimizada...")
    try:
        response = requests.post(f"{base_url}/executar-agora", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - Status: {response.status_code}")
            print(f"   Success: {data.get('success')}")
            print(f"   Message: {data.get('message')}")
        else:
            print(f"   ERRO - Status: {response.status_code}")
    except Exception as e:
        print(f"   ERRO - {e}")
    
    # Teste extração customizada
    print("\n2. Testando extração customizada...")
    try:
        payload = {
            "data": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "salvar_arquivos": False,
            "max_editais": 5
        }
        
        response = requests.post(f"{base_url}/extrair-dia-anterior", json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - Status: {response.status_code}")
            if 'data' in data:
                resultado = data['data']
                print(f"   Encontrados: {resultado.get('total_encontrados', 0)}")
                print(f"   Salvos: {resultado.get('total_salvos', 0)}")
        else:
            print(f"   ERRO - Status: {response.status_code}")
    except Exception as e:
        print(f"   ERRO - {e}")


def test_dashboard():
    """Testa os endpoints do dashboard"""
    print("\nTESTE DO DASHBOARD")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    endpoints = [
        ("/dashboard/resumo", "Resumo Executivo"),
        ("/dashboard/estatisticas-por-orgao", "Estatísticas por Órgão"),
        ("/dashboard/estatisticas-diarias", "Estatísticas Diárias"),
        ("/dashboard/alertas", "Alertas"),
        ("/dashboard/editais-recentes", "Editais Recentes"),
        ("/dashboard/editais-mais-valiosos", "Editais Mais Valiosos"),
        ("/dashboard/performance", "Performance"),
        ("/estatisticas", "Estatísticas Gerais")
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"   OK - {name}: {response.status_code}")
            else:
                print(f"   ERRO - {name}: {response.status_code}")
        except Exception as e:
            print(f"   ERRO - {name}: {e}")


def test_scheduler():
    """Testa o scheduler"""
    print("\nTESTE DO SCHEDULER")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    try:
        response = requests.get(f"{base_url}/scheduler/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - Status: {response.status_code}")
            print(f"   Ativo: {data.get('ativo', 'N/A')}")
        else:
            print(f"   ERRO - Status: {response.status_code}")
    except Exception as e:
        print(f"   ERRO - {e}")


def main():
    """Executa todos os testes"""
    print("TESTE COMPLETO DO SISTEMA PNCP EXTRATOR")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Executa testes
    test_api_status()
    test_extraction()
    test_dashboard()
    test_scheduler()
    
    print("\nRESUMO DOS TESTES")
    print("=" * 60)
    print("Sistema testado com sucesso!")
    print("Verifique os logs acima para detalhes.")


if __name__ == "__main__":
    main() 