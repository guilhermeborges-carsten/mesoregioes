# 🚀 Instruções Rápidas - Dashboard Logístico

## ⚡ Execução Rápida

### Windows
1. **Duplo clique** no arquivo `run.bat`
2. Aguarde a instalação das dependências
3. Acesse: `http://localhost:5000`

### Linux/macOS
1. **Terminal**: `./run.sh`
2. Aguarde a instalação das dependências
3. Acesse: `http://localhost:5000`

### Manual
```bash
# 1. Criar ambiente virtual
python -m venv venv

# 2. Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Executar aplicação
python app.py
```

## 📊 Primeiro Uso

1. **Acesse** o dashboard em `http://localhost:5000`
2. **Clique** em "Upload" no menu superior
3. **Selecione** "Carregar Excel"
4. **Faça upload** do arquivo `exemplo_dados.csv` para teste
5. **Explore** as funcionalidades!

## 🔧 Solução de Problemas

### Erro: "Porta já em uso"
- Altere a porta no `app.py`: `port=5001`
- Ou feche outros aplicativos usando a porta 5000

### Erro: "Módulo não encontrado"
- Reative o ambiente virtual
- Execute: `pip install -r requirements.txt`

### Performance lenta
- Use filtros mais específicos
- Reduza o número de registros por página

## 📁 Arquivos Importantes

- `app.py` - Aplicação principal
- `requirements.txt` - Dependências Python
- `exemplo_dados.csv` - Dados de teste
- `README.md` - Documentação completa

## 🆘 Suporte

- **Documentação**: `README.md`
- **Dados de Exemplo**: `exemplo_dados.csv`
- **Logs**: Console do terminal

---

**🎯 Aplicação pronta para uso!**
