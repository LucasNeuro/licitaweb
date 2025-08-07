#!/usr/bin/env python3
"""
Teste de compatibilidade com Render
"""

import os
import sys
from dotenv import load_dotenv

def test_render_compatibility():
    """Testa se o sistema é compatível com Render"""
    print("🧪 TESTE DE COMPATIBILIDADE COM RENDER")
    print("=" * 50)
    
    # Teste 1: Variáveis de ambiente
    print("1️⃣ Testando variáveis de ambiente...")
    load_dotenv()
    
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variáveis faltando: {missing_vars}")
        print("💡 Configure no Render Dashboard > Environment Variables")
    else:
        print("✅ Variáveis de ambiente configuradas")
    
    # Teste 2: Imports
    print("\n2️⃣ Testando imports...")
    try:
        from fastapi import FastAPI
        print("✅ FastAPI OK")
    except ImportError as e:
        print(f"❌ FastAPI: {e}")
    
    try:
        from supabase import create_client
        print("✅ Supabase OK")
    except ImportError as e:
        print(f"❌ Supabase: {e}")
    
    try:
        from selenium import webdriver
        print("✅ Selenium OK")
    except ImportError as e:
        print(f"❌ Selenium: {e}")
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        print("✅ WebDriver Manager OK")
    except ImportError as e:
        print(f"❌ WebDriver Manager: {e}")
    
    # Teste 3: Configurações
    print("\n3️⃣ Testando configurações...")
    try:
        from app.core.config import settings
        print("✅ Configurações carregadas")
        print(f"   📊 Supabase configurado: {settings.is_configured()}")
        print(f"   🌐 Host: {settings.HOST}")
        print(f"   🔢 Porta: {settings.PORT}")
        print(f"   🤖 Selenium headless: {settings.SELENIUM_HEADLESS}")
    except Exception as e:
        print(f"❌ Erro nas configurações: {e}")
    
    # Teste 4: Estrutura de arquivos
    print("\n4️⃣ Testando estrutura de arquivos...")
    required_files = [
        "app/main.py",
        "app/core/config.py", 
        "app/core/extractor.py",
        "requirements.txt",
        "Procfile"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Arquivos faltando: {missing_files}")
    else:
        print("✅ Todos os arquivos necessários existem")
    
    print("\n" + "=" * 50)
    print("📋 RESUMO:")
    if not missing_vars and not missing_files:
        print("✅ SISTEMA PRONTO PARA RENDER!")
        print("🚀 Pode fazer o deploy com segurança")
    else:
        print("⚠️ Alguns problemas detectados")
        print("🔧 Corrija antes do deploy")
    print("=" * 50)

if __name__ == "__main__":
    test_render_compatibility()
