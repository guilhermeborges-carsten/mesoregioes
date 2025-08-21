#!/bin/bash

echo "========================================"
echo "   Dashboard Logístico - Mesorregioes"
echo "========================================"
echo ""
echo "Iniciando aplicação..."
echo ""

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "ERRO: Python3 não encontrado!"
    echo "Por favor, instale Python 3.8+ e tente novamente."
    exit 1
fi

# Verificar se o ambiente virtual existe
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERRO: Falha ao criar ambiente virtual!"
        exit 1
    fi
fi

# Ativar ambiente virtual
echo "Ativando ambiente virtual..."
source venv/bin/activate

# Instalar dependências
echo "Instalando dependências..."
pip install -r requirements.txt

# Executar aplicação
echo ""
echo "Iniciando servidor..."
echo "Acesse: http://localhost:5000"
echo ""
echo "Pressione Ctrl+C para parar o servidor"
echo ""
python app.py
