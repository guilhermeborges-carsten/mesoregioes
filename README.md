# 🚛 Dashboard Logístico - Análise de Embarques entre Mesorregiões

Dashboard web interativo para análise de dados logísticos de embarques entre mesorregiões brasileiras, desenvolvido com Flask, Bootstrap 5, Chart.js e Leaflet.js.

## ✨ Funcionalidades

- **📊 Dashboard Principal**: Estatísticas rápidas, evolução mensal, top rankings
- **🔥 Heatmap Origem-Destino**: Matriz de intensidade de fluxos com filtros
- **🗺️ Mapa de Fluxos**: Visualização geográfica interativa dos fluxos
- **📋 Tabela Detalhada**: Dados completos com paginação e filtros
- **🧮 Balanço de Embarques**: Análise de saldo (origem - destino) por mesorregião
- **📤 Upload de Dados**: Carregamento de arquivos Excel (.xlsx/.xls)
- **📥 Exportação**: Excel, CSV e imagens PNG dos gráficos

## 🛠️ Tecnologias Utilizadas

### Backend
- **Flask 2.3.3**: Framework web Python
- **Pandas 2.1.1**: Manipulação e análise de dados
- **GeoPandas 0.14.0**: Processamento de dados geográficos
- **OpenPyXL 3.1.2**: Manipulação de arquivos Excel
- **NumPy 1.24.3**: Computação numérica
- **Gunicorn 21.2.0**: Servidor WSGI para produção

### Frontend
- **Bootstrap 5**: Framework CSS responsivo
- **Chart.js**: Gráficos interativos
- **Leaflet.js**: Mapas interativos
- **Select2**: Dropdowns avançados
- **jQuery**: Manipulação do DOM

## 🚀 Deploy no Render

### Pré-requisitos
- Conta no [Render](https://render.com)
- Repositório Git (GitHub, GitLab, etc.)

### Passos para Deploy

1. **Fork/Clone este repositório**
   ```bash
   git clone <seu-repositorio>
   cd dashboard-logistico
   ```

2. **Conectar ao Render**
   - Acesse [render.com](https://render.com)
   - Faça login ou crie uma conta
   - Clique em "New +" → "Web Service"

3. **Configurar o Serviço**
   - **Name**: `dashboard-logistico` (ou nome de sua preferência)
   - **Environment**: `Python 3`
   - **Region**: Escolha a região mais próxima
   - **Branch**: `main` (ou sua branch principal)
   - **Root Directory**: Deixe em branco (raiz do projeto)

4. **Configurações de Build**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

5. **Deploy Automático**
   - Clique em "Create Web Service"
   - O Render fará o deploy automaticamente
   - Aguarde a mensagem "Deploy successful"

### Configurações Importantes

- **Plan**: Free (para começar)
- **Auto-Deploy**: Habilitado (deploy automático a cada push)
- **Health Check Path**: `/` (página inicial)

## 📁 Estrutura do Projeto

```
dashboard-logistico/
├── app.py                 # Aplicação Flask principal
├── requirements.txt       # Dependências Python
├── render.yaml           # Configuração do Render
├── Procfile              # Comando de inicialização
├── runtime.txt           # Versão do Python
├── static/               # Arquivos estáticos
│   ├── css/
│   ├── js/
│   └── img/
├── templates/            # Templates HTML
│   ├── base.html
│   ├── index.html
│   ├── heatmap.html
│   ├── mapa_fluxos.html
│   ├── tabela.html
│   └── balanco.html
└── README.md
```

## 🔧 Desenvolvimento Local

### Instalação
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### Execução
```bash
# Desenvolvimento
python app.py

# Produção
gunicorn app:app
```

## 📊 Formato dos Dados

O sistema aceita arquivos Excel (.xlsx/.xls) com as seguintes colunas:

| Coluna | Descrição | Exemplo |
|--------|-----------|---------|
| `MESORREGIÃO - ORIGEM` | Mesorregião de origem | "MARILIA/SP" |
| `MESORREGIÃO - DESTINO` | Mesorregião de destino | "SÃO PAULO/SP" |
| `MÊS` | Período do embarque | "8 - 2023" |
| `EMBARQUES` | Quantidade de embarques | 99 |

## 🌐 URLs da Aplicação

- **Home**: `/` - Dashboard principal
- **Heatmap**: `/heatmap` - Matriz origem-destino
- **Mapa**: `/mapa_fluxos` - Visualização geográfica
- **Tabela**: `/tabela` - Dados detalhados
- **Balanço**: `/balanco` - Análise de saldo

## 🔒 Considerações de Segurança

- **Upload de arquivos**: Validação de extensão (.xlsx/.xls)
- **Processamento**: Dados processados em memória (não persistidos)
- **Exportação**: Apenas dados filtrados são exportados

## 📱 Responsividade

O dashboard é totalmente responsivo e funciona em:
- ✅ Desktop (1920x1080+)
- ✅ Tablet (768px+)
- ✅ Mobile (320px+)

## 🆘 Suporte

Para dúvidas ou problemas:
1. Verifique os logs no Render Dashboard
2. Teste localmente primeiro
3. Verifique se todas as dependências estão instaladas

## 📈 Próximas Funcionalidades

- [ ] Persistência de dados em banco
- [ ] Autenticação de usuários
- [ ] Mais tipos de gráficos
- [ ] API REST completa
- [ ] Cache de dados
- [ ] Relatórios agendados

---

**Desenvolvido com ❤️ para análise logística brasileira**
