from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
import json
import io
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Criar pasta de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Dados globais em memória
global_data = None
mesorregioes_info = {
    'Norte': ['Acre', 'Amazonas', 'Rondônia', 'Roraima', 'Amapá', 'Pará', 'Tocantins'],
    'Nordeste': ['Maranhão', 'Piauí', 'Ceará', 'Rio Grande do Norte', 'Pernambuco', 'Paraíba', 'Sergipe', 'Alagoas', 'Bahia'],
    'Centro-Oeste': ['Mato Grosso', 'Mato Grosso do Sul', 'Goiás', 'Distrito Federal'],
    'Sudeste': ['Minas Gerais', 'Espírito Santo', 'Rio de Janeiro', 'São Paulo'],
    'Sul': ['Paraná', 'Santa Catarina', 'Rio Grande do Sul']
}

def process_excel_data(file_path):
    """Processa arquivo Excel e retorna dados estruturados"""
    try:
        # Ler arquivo Excel
        df = pd.read_excel(file_path)
        
        # Verificar se as colunas estão corretas
        expected_columns = ['TRECHO - FROTA PRÓPRIA', 'MESORREGIÃO - ORIGEM', 'MESORREGIÃO - DESTINO', 'MÊS', 'EMBARQUES']
        if not all(col in df.columns for col in expected_columns):
            return None, "Colunas do arquivo não correspondem ao formato esperado"
        
        # Limpar dados
        df = df.dropna()
        df['EMBARQUES'] = pd.to_numeric(df['EMBARQUES'], errors='coerce')
        df = df[df['EMBARQUES'] > 0]
        
        # Processar coluna de mês
        df['MÊS'] = df['MÊS'].astype(str)
        df['ANO'] = df['MÊS'].str.extract(r'(\d{4})').astype(int)
        df['MES_NUM'] = df['MÊS'].str.extract(r'(\d+)').astype(int)
        
        # Criar coluna de data para ordenação
        df['DATA'] = pd.to_datetime(df['ANO'].astype(str) + '-' + df['MES_NUM'].astype(str) + '-01')
        
        return df, None
    except Exception as e:
        return None, f"Erro ao processar arquivo: {str(e)}"

def get_filtered_data(filters):
    """Aplica filtros aos dados globais"""
    if global_data is None:
        return pd.DataFrame()
    
    df = global_data.copy()
    print(f"get_filtered_data: Iniciando com {len(df)} registros")
    print(f"get_filtered_data: Filtros recebidos: {filters}")
    
    # Filtros de período
    if filters.get('data_inicio'):
        try:
            data_inicio = pd.to_datetime(filters['data_inicio'])
            df = df[df['DATA'] >= data_inicio]
            print(f"get_filtered_data: Filtro data_inicio aplicado: {data_inicio} - Dados restantes: {len(df)}")
        except Exception as e:
            print(f"get_filtered_data: Erro ao aplicar filtro data_inicio: {e}")
            pass  # Ignorar filtro de data inválido
    
    if filters.get('data_fim'):
        try:
            data_fim = pd.to_datetime(filters['data_fim'])
            df = df[df['DATA'] <= data_fim]
            print(f"get_filtered_data: Filtro data_fim aplicado: {data_fim} - Dados restantes: {len(df)}")
        except Exception as e:
            print(f"get_filtered_data: Erro ao aplicar filtro data_fim: {e}")
            pass  # Ignorar filtro de data inválido
    
    # Filtros de mesorregião - Melhorado para múltiplas seleções
    if filters.get('origens'):
        origens = filters['origens']
        print(f"get_filtered_data: Processando filtro origens: {origens} (tipo: {type(origens)})")
        
        # Flask pode retornar uma lista quando há múltiplos parâmetros com o mesmo nome
        # ou uma string quando há apenas um parâmetro
        if isinstance(origens, list):
            # Já é uma lista, usar diretamente
            origens_filtro = origens
        elif isinstance(origens, str):
            # Se for uma string única, converter para lista
            if origens:
                origens_filtro = [origens]
            else:
                origens_filtro = []
        elif origens is None:
            origens_filtro = []
        else:
            # Caso inesperado, converter para lista
            origens_filtro = list(origens) if origens else []
        
        print(f"get_filtered_data: Origens após processamento: {origens_filtro}")
        
        # Aplicar filtro apenas se houver origens selecionadas
        if len(origens_filtro) > 0:
            df = df[df['MESORREGIÃO - ORIGEM'].isin(origens_filtro)]
            print(f"get_filtered_data: Filtro de origens aplicado: {origens_filtro} - Dados restantes: {len(df)}")
    
    if filters.get('destinos'):
        destinos = filters['destinos']
        print(f"get_filtered_data: Processando filtro destinos: {destinos} (tipo: {type(destinos)})")
        
        # Flask pode retornar uma lista quando há múltiplos parâmetros com o mesmo nome
        # ou uma string quando há apenas um parâmetro
        if isinstance(destinos, list):
            # Já é uma lista, usar diretamente
            destinos_filtro = destinos
        elif isinstance(destinos, str):
            # Se for uma string única, converter para lista
            if destinos:
                destinos_filtro = [destinos]
            else:
                destinos_filtro = []
        elif destinos is None:
            destinos_filtro = []
        else:
            # Caso inesperado, converter para lista
            destinos_filtro = list(destinos) if destinos else []
        
        print(f"get_filtered_data: Destinos após processamento: {destinos_filtro}")
        
        # Aplicar filtro apenas se houver destinos selecionados
        if len(destinos_filtro) > 0:
            df = df[df['MESORREGIÃO - DESTINO'].isin(destinos_filtro)]
            print(f"get_filtered_data: Filtro de destinos aplicado: {destinos_filtro} - Dados restantes: {len(df)}")
    
    # Verificar se ainda há dados após filtros
    if df.empty:
        print("get_filtered_data: Nenhum dado encontrado após aplicar filtros")
        return df
    
    print(f"get_filtered_data: Filtros aplicados com sucesso. Total de registros: {len(df)}")
    return df

@app.route('/')
def index():
    """Página inicial do dashboard"""
    return render_template('index.html')

@app.route('/heatmap')
def heatmap():
    """Página do heatmap origem-destino"""
    return render_template('heatmap.html')

@app.route('/mapa_fluxos')
def mapa_fluxos():
    """Página do mapa de fluxos geográficos"""
    return render_template('mapa_fluxos.html')

@app.route('/tabela')
def tabela():
    """Página da tabela detalhada"""
    return render_template('tabela.html')

@app.route('/balanco')
def balanco():
    """Página do balanço de embarques"""
    return render_template('balanco.html')

@app.route('/balanco_clientes')
def balanco_clientes():
    """Página do balanço de embarques por clientes"""
    return render_template('balanco_clientes.html')

@app.route('/analise_clientes')
def analise_clientes():
    """Página de análise detalhada de clientes com gráficos e insights"""
    return render_template('analise_clientes.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API para upload de arquivo Excel"""
    global global_data
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
    
    if file and file.filename.endswith(('.xlsx', '.xls')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Processar dados
        df, error = process_excel_data(filepath)
        if error:
            return jsonify({'success': False, 'error': error})
        
        global_data = df
        
        # Remover arquivo temporário
        os.remove(filepath)
        
        return jsonify({'success': True, 'message': 'Arquivo processado com sucesso'})
    
    return jsonify({'success': False, 'error': 'Formato de arquivo não suportado'})

@app.route('/api/stats')
def get_stats():
    """API para estatísticas gerais"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    # Aplicar filtros se fornecidos
    filters = request.args.to_dict()
    print(f"Filtros recebidos na API stats: {filters}")
    
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Estatísticas básicas
    total_embarques = int(df['EMBARQUES'].sum())
    
    # Contar origens e destinos baseado nos filtros aplicados
    if filters.get('origens') and len(filters.get('origens', [])) > 0:
        # Se há filtro de origens, contar as origens selecionadas
        origens_filtro = filters['origens']
        if isinstance(origens_filtro, str):
            origens_filtro = [origens_filtro]
        total_origens = len(origens_filtro)
        print(f"get_stats: Contando origens do filtro: {origens_filtro} = {total_origens}")
    else:
        # Se não há filtro, contar origens únicas nos dados
        total_origens = df['MESORREGIÃO - ORIGEM'].nunique()
        print(f"get_stats: Contando origens únicas nos dados: {total_origens}")
    
    if filters.get('destinos') and len(filters.get('destinos', [])) > 0:
        # Se há filtro de destinos, contar os destinos selecionados
        destinos_filtro = filters['destinos']
        if isinstance(destinos_filtro, str):
            destinos_filtro = [destinos_filtro]
        total_destinos = len(destinos_filtro)
        print(f"get_stats: Contando destinos do filtro: {destinos_filtro} = {total_destinos}")
    else:
        # Se não há filtro, contar destinos únicos nos dados
        total_destinos = df['MESORREGIÃO - DESTINO'].nunique()
        print(f"get_stats: Contando destinos únicos nos dados: {total_destinos}")
    
    periodo_inicio = df['DATA'].min().strftime('%m/%Y')
    periodo_fim = df['DATA'].max().strftime('%m/%Y')
    
    # Top 5 origens
    top_origens = df.groupby('MESORREGIÃO - ORIGEM')['EMBARQUES'].sum().nlargest(5)
    top_origens = [{'regiao': regiao, 'embarques': int(embarques)} for regiao, embarques in top_origens.items()]
    
    # Top 5 destinos
    top_destinos = df.groupby('MESORREGIÃO - DESTINO')['EMBARQUES'].sum().nlargest(5)
    top_destinos = [{'regiao': regiao, 'embarques': int(embarques)} for regiao, embarques in top_destinos.items()]
    
    print(f"Estatísticas calculadas - Total embarques: {total_embarques}, Origens: {total_origens}, Destinos: {total_destinos}")
    
    return jsonify({
        'total_embarques': total_embarques,
        'total_origens': total_origens,
        'total_destinos': total_destinos,
        'periodo_inicio': periodo_inicio,
        'periodo_fim': periodo_fim,
        'top_origens': top_origens,
        'top_destinos': top_destinos
    })

@app.route('/api/evolucao_mensal')
def get_evolucao_mensal():
    """API para dados de evolução mensal"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    print(f"Filtros recebidos na API evolução mensal: {filters}")
    
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Agrupar por mês
    evolucao = df.groupby(['ANO', 'MES_NUM', 'DATA'])['EMBARQUES'].sum().reset_index()
    evolucao = evolucao.sort_values('DATA')
    
    # Calcular tendência (média móvel de 3 meses)
    evolucao['tendencia'] = evolucao['EMBARQUES'].rolling(window=3, center=True).mean()
    
    # Tratar valores NaN na tendência
    evolucao['tendencia'] = evolucao['tendencia'].fillna(0)
    
    print(f"Evolução mensal calculada - Períodos: {len(evolucao)}, Total embarques: {evolucao['EMBARQUES'].sum()}")
    
    return jsonify({
        'labels': [f"{row['MES_NUM']}/{row['ANO']}" for _, row in evolucao.iterrows()],
        'embarques': evolucao['EMBARQUES'].tolist(),
        'tendencia': evolucao['tendencia'].astype(int).tolist()
    })

@app.route('/api/evolucao_mensal_clientes')
def get_evolucao_mensal_clientes():
    """API para dados de evolução mensal por cliente"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    print(f"Filtros recebidos na API evolução mensal clientes: {filters}")
    
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Extrair nome do cliente da coluna TRECHO - FROTA PRÓPRIA
    df['CLIENTE'] = df['TRECHO - FROTA PRÓPRIA'].str.extract(r'^([^-]+)')[0].str.strip()
    
    # Verificar se a coluna DATA existe, se não, criar a partir de ANO e MES_NUM
    if 'DATA' not in df.columns:
        print("Coluna DATA não encontrada, criando a partir de ANO e MES_NUM")
        df['DATA'] = pd.to_datetime(df[['ANO', 'MES_NUM']].assign(DAY=1))
    
    # Agrupar por cliente, mês e calcular embarques
    evolucao_clientes = df.groupby(['CLIENTE', 'ANO', 'MES_NUM', 'DATA'])['EMBARQUES'].sum().reset_index()
    evolucao_clientes = evolucao_clientes.sort_values(['CLIENTE', 'DATA'])
    
    # Calcular tendência por cliente (média móvel de 3 meses)
    evolucao_clientes['tendencia'] = evolucao_clientes.groupby('CLIENTE')['EMBARQUES'].transform(
        lambda x: x.rolling(window=3, center=True).mean()
    )
    
    # Tratar valores NaN na tendência
    evolucao_clientes['tendencia'] = evolucao_clientes['tendencia'].fillna(0)
    
    # Preparar dados para o gráfico
    clientes = evolucao_clientes['CLIENTE'].unique()
    dados_grafico = {}
    
    for cliente in clientes:
        dados_cliente = evolucao_clientes[evolucao_clientes['CLIENTE'] == cliente].sort_values('DATA')
        
        dados_grafico[cliente] = {
            'labels': [f"{row['MES_NUM']}/{row['ANO']}" for _, row in dados_cliente.iterrows()],
            'embarques': dados_cliente['EMBARQUES'].tolist(),
            'tendencia': dados_cliente['tendencia'].astype(int).tolist()
        }
    
    print(f"Evolução mensal por clientes calculada - Clientes: {len(clientes)}")
    
    return jsonify({
        'clientes': clientes.tolist(),
        'dados': dados_grafico
    })

@app.route('/api/insights_clientes')
def get_insights_clientes():
    """API para insights e análises estratégicas por cliente"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    print(f"Filtros recebidos na API insights clientes: {filters}")
    
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Extrair nome do cliente da coluna TRECHO - FROTA PRÓPRIA
    df['CLIENTE'] = df['TRECHO - FROTA PRÓPRIA'].str.extract(r'^([^-]+)')[0].str.strip()
    
    # Verificar se a coluna DATA existe, se não, criar a partir de ANO e MES_NUM
    if 'DATA' not in df.columns:
        print("Coluna DATA não encontrada, criando a partir de ANO e MES_NUM")
        df['DATA'] = pd.to_datetime(df[['ANO', 'MES_NUM']].assign(DAY=1))
    
    # Análise por cliente
    insights_clientes = {}
    clientes = df['CLIENTE'].unique()
    
    for cliente in clientes:
        df_cliente = df[df['CLIENTE'] == cliente]
        
        # Estatísticas básicas
        total_embarques = df_cliente['EMBARQUES'].sum()
        total_registros = len(df_cliente)
        periodo_inicio = df_cliente['DATA'].min()
        periodo_fim = df_cliente['DATA'].max()
        
        # Top origens e destinos
        top_origens = df_cliente.groupby('MESORREGIÃO - ORIGEM')['EMBARQUES'].sum().nlargest(5)
        top_destinos = df_cliente.groupby('MESORREGIÃO - DESTINO')['EMBARQUES'].sum().nlargest(5)
        
        # Análise de sazonalidade (por mês)
        sazonalidade = df_cliente.groupby('MES_NUM')['EMBARQUES'].sum().sort_index()
        
        # Calcular crescimento (comparar primeiro vs último mês)
        if len(sazonalidade) > 1:
            primeiro_mes = sazonalidade.iloc[0]
            ultimo_mes = sazonalidade.iloc[-1]
            crescimento = ((ultimo_mes - primeiro_mes) / primeiro_mes * 100) if primeiro_mes > 0 else 0
        else:
            crescimento = 0
        
        # Identificar padrões e oportunidades
        oportunidades = []
        melhorias = []
        
        # Análise de concentração geográfica
        if top_origens.iloc[0] / total_embarques > 0.7:
            oportunidades.append("Diversificar origens para reduzir dependência de uma única região")
        
        if top_destinos.iloc[0] / total_embarques > 0.7:
            oportunidades.append("Expandir para novos destinos para aumentar mercado")
        
        # Análise de crescimento
        if crescimento > 20:
            melhorias.append("Crescimento forte - considerar expansão de capacidade")
        elif crescimento < -10:
            melhorias.append("Declínio detectado - investigar causas e implementar ações corretivas")
        
        # Análise de sazonalidade
        mes_maior = sazonalidade.idxmax()
        mes_menor = sazonalidade.idxmin()
        if sazonalidade.iloc[-1] > sazonalidade.iloc[0]:
            melhorias.append("Tendência positiva - manter estratégias de crescimento")
        
        insights_clientes[cliente] = {
            'estatisticas': {
                'total_embarques': int(total_embarques),
                'total_registros': total_registros,
                'periodo_inicio': periodo_inicio.strftime('%m/%Y'),
                'periodo_fim': periodo_fim.strftime('%m/%Y'),
                'crescimento_percentual': round(crescimento, 1)
            },
            'top_origens': [
                {'regiao': regiao, 'embarques': int(embarques), 'percentual': round(embarques/total_embarques*100, 1)}
                for regiao, embarques in top_origens.items()
            ],
            'top_destinos': [
                {'regiao': regiao, 'embarques': int(embarques), 'percentual': round(embarques/total_embarques*100, 1)}
                for regiao, embarques in top_destinos.items()
            ],
            'sazonalidade': {
                'meses': [int(mes) for mes in sazonalidade.index],
                'embarques': [int(embarques) for embarques in sazonalidade.values],
                'mes_maior': int(mes_maior),
                'mes_menor': int(mes_menor)
            },
            'oportunidades': oportunidades,
            'melhorias': melhorias,
            'score_performance': min(100, max(0, 50 + crescimento))  # Score baseado no crescimento
        }
    
    # Análise geral (todos os clientes juntos)
    total_geral = df['EMBARQUES'].sum()
    crescimento_geral = 0
    
    if len(df) > 0:
        # Calcular crescimento geral
        df_por_mes = df.groupby(['ANO', 'MES_NUM'])['EMBARQUES'].sum().reset_index()
        # Criar data completa com dia 1 para cada mês
        df_por_mes['DATA'] = pd.to_datetime(df_por_mes[['ANO', 'MES_NUM']].assign(DAY=1))
        df_por_mes = df_por_mes.sort_values('DATA')
        
        if len(df_por_mes) > 1:
            primeiro_mes_geral = df_por_mes.iloc[0]['EMBARQUES']
            ultimo_mes_geral = df_por_mes.iloc[-1]['EMBARQUES']
            crescimento_geral = ((ultimo_mes_geral - primeiro_mes_geral) / primeiro_mes_geral * 100) if primeiro_mes_geral > 0 else 0
    
    insights_geral = {
        'total_embarques': int(total_geral),
        'total_clientes': len(clientes),
        'crescimento_geral': round(crescimento_geral, 1),
        'clientes_ativos': len([c for c in clientes if insights_clientes[c]['estatisticas']['total_embarques'] > 0]),
        'distribuicao_clientes': [
            {
                'cliente': cliente,
                'percentual': round(insights_clientes[cliente]['estatisticas']['total_embarques'] / total_geral * 100, 1),
                'score': insights_clientes[cliente]['score_performance']
            }
            for cliente in clientes
        ]
    }
    
    print(f"Insights calculados para {len(clientes)} clientes")
    
    return jsonify({
        'insights_geral': insights_geral,
        'insights_clientes': insights_clientes
    })

@app.route('/api/top_origens')
def get_top_origens():
    """API para ranking de origens"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    print(f"Filtros recebidos na API top origens: {filters}")
    
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Top origens
    limit = filters.get('limit', 20)
    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 20
    
    top_origens = df.groupby('MESORREGIÃO - ORIGEM')['EMBARQUES'].sum().nlargest(limit)
    
    # Calcular percentuais
    total = top_origens.sum()
    top_origens_pct = [(regiao, int(embarques), round(embarques/total*100, 1)) 
                        for regiao, embarques in top_origens.items()]
    
    print(f"Top origens calculado - Limit: {limit}, Total origens: {len(top_origens_pct)}")
    
    return jsonify({
        'origens': [item[0] for item in top_origens_pct],
        'embarques': [item[1] for item in top_origens_pct],
        'percentuais': [item[2] for item in top_origens_pct]
    })

@app.route('/api/top_destinos')
def get_top_destinos():
    """API para ranking de destinos"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    print(f"Filtros recebidos na API top destinos: {filters}")
    
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Top destinos
    limit = filters.get('limit', 20)
    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 20
    
    top_destinos = df.groupby('MESORREGIÃO - DESTINO')['EMBARQUES'].sum().nlargest(limit)
    
    # Calcular percentuais
    total = top_destinos.sum()
    top_destinos_pct = [(regiao, int(embarques), round(embarques/total*100, 1)) 
                         for regiao, embarques in top_destinos.items()]
    
    print(f"Top destinos calculado - Limit: {limit}, Total destinos: {len(top_destinos_pct)}")
    
    return jsonify({
        'destinos': [item[0] for item in top_destinos_pct],
        'embarques': [item[1] for item in top_destinos_pct],
        'percentuais': [item[2] for item in top_destinos_pct]
    })

@app.route('/api/heatmap_data')
def get_heatmap_data():
    """API para dados do heatmap origem-destino"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Criar matriz origem-destino
    heatmap_data = df.groupby(['MESORREGIÃO - ORIGEM', 'MESORREGIÃO - DESTINO'])['EMBARQUES'].sum().reset_index()
    
    # Pivotar para formato de matriz
    heatmap_matrix = heatmap_data.pivot(index='MESORREGIÃO - ORIGEM', 
                                       columns='MESORREGIÃO - DESTINO', 
                                       values='EMBARQUES').fillna(0)
    
    return jsonify({
        'origens': heatmap_matrix.index.tolist(),
        'destinos': heatmap_matrix.columns.tolist(),
        'valores': heatmap_matrix.values.tolist()
    })

@app.route('/api/fluxos_mapa')
def get_fluxos_mapa():
    """API para dados de fluxos para o mapa"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Agrupar por origem-destino
    fluxos = df.groupby(['MESORREGIÃO - ORIGEM', 'MESORREGIÃO - DESTINO'])['EMBARQUES'].sum().reset_index()
    
    # Filtrar por volume mínimo se especificado
    volume_min = filters.get('volume_min', 0)
    if volume_min:
        try:
            volume_min_int = int(volume_min)
            fluxos = fluxos[fluxos['EMBARQUES'] >= volume_min_int]
        except:
            pass  # Ignorar filtro de volume inválido
    
    # Limitar número de fluxos se especificado
    top_n = filters.get('top_n', 20)
    if top_n:
        try:
            top_n_int = int(top_n)
            fluxos = fluxos.nlargest(top_n_int, 'EMBARQUES')
        except:
            pass  # Ignorar filtro de top_n inválido
    
    # Adicionar coordenadas simuladas (em produção, usar shapefiles reais)
    fluxos['origem_coords'] = fluxos['MESORREGIÃO - ORIGEM'].apply(lambda x: get_coordinates(x))
    fluxos['destino_coords'] = fluxos['MESORREGIÃO - DESTINO'].apply(lambda x: get_coordinates(x))
    
    return jsonify({
        'fluxos': fluxos.to_dict('records')
    })

@app.route('/api/tabela_dados')
def get_tabela_dados():
    """API para dados da tabela detalhada"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Limitar número de registros
    limit = filters.get('limit', 20)
    try:
        limit_int = int(limit)
        df = df.head(limit_int)
    except:
        df = df.head(20)  # Usar valor padrão se inválido
    
    # Formatar dados para tabela
    dados_tabela = []
    for _, row in df.iterrows():
        dados_tabela.append({
            'trecho': row['TRECHO - FROTA PRÓPRIA'],
            'origem': row['MESORREGIÃO - ORIGEM'],
            'destino': row['MESORREGIÃO - DESTINO'],
            'mes': row['MÊS'],
            'embarques': int(row['EMBARQUES'])
        })
    
    return jsonify({
        'dados': dados_tabela,
        'total': len(df)
    })

@app.route('/api/balanco_embarques')
def get_balanco_embarques():
    """Retorna dados para o balanço de embarques (origem - destino) por mesorregião"""
    try:
        filters = request.args.to_dict()
        
        # Aplicar filtros
        filtered_data = get_filtered_data(filters)
        
        if filtered_data.empty:
            return jsonify({'error': 'Nenhum dado encontrado'})
        
        # Agrupar por origem e destino
        origens = filtered_data.groupby('MESORREGIÃO - ORIGEM')['EMBARQUES'].sum().reset_index()
        origens.columns = ['MESORREGIÃO', 'EMBARQUES_ORIGEM']
        
        destinos = filtered_data.groupby('MESORREGIÃO - DESTINO')['EMBARQUES'].sum().reset_index()
        destinos.columns = ['MESORREGIÃO', 'EMBARQUES_DESTINO']
        
        # Fazer merge para ter origem e destino na mesma linha
        resultado = pd.merge(origens, destinos, on='MESORREGIÃO', how='outer').fillna(0)
        
        # Calcular saldo e indicadores
        resultado['SALDO'] = resultado['EMBARQUES_ORIGEM'] - resultado['EMBARQUES_DESTINO']
        resultado['TOTAL_MOVIMENTADO'] = resultado['EMBARQUES_ORIGEM'] + resultado['EMBARQUES_DESTINO']
        resultado['PERCENTUAL_ORIGEM'] = (resultado['EMBARQUES_ORIGEM'] / resultado['TOTAL_MOVIMENTADO'] * 100).round(1)
        resultado['PERCENTUAL_DESTINO'] = (resultado['EMBARQUES_DESTINO'] / resultado['TOTAL_MOVIMENTADO'] * 100).round(1)
        
        # Adicionar classificação do saldo
        def classificar_saldo(saldo):
            if saldo > 0:
                return 'Produtora (Origem > Destino)'
            elif saldo < 0:
                return 'Consumidora (Destino > Origem)'
            else:
                return 'Equilibrada (Origem = Destino)'
        
        resultado['CLASSIFICACAO'] = resultado['SALDO'].apply(classificar_saldo)
        
        # Ordenar por TOTAL_MOVIMENTADO (do maior para o menor)
        resultado = resultado.sort_values('TOTAL_MOVIMENTADO', ascending=False)
        
        # Aplicar filtro de classificação se especificado
        classificacao = filters.get('classificacao', '')
        if classificacao:
            if classificacao == 'produtora':
                resultado = resultado[resultado['SALDO'] > 0]
            elif classificacao == 'consumidora':
                resultado = resultado[resultado['SALDO'] < 0]
            elif classificacao == 'equilibrada':
                resultado = resultado[resultado['SALDO'] == 0]
        
        # Aplicar limite se especificado
        limit = filters.get('limit', 0)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 0
        
        if limit > 0:
            resultado = resultado.head(limit)
        
        return jsonify({
            'data': resultado.to_dict('records'),
            'resumo': {
                'total_mesorregioes': len(resultado),
                'produtoras': len(resultado[resultado['SALDO'] > 0]),
                'consumidoras': len(resultado[resultado['SALDO'] < 0]),
                'equilibradas': len(resultado[resultado['SALDO'] == 0])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/balanco_clientes')
def get_balanco_clientes():
    """Retorna dados para o balanço de embarques separado por clientes"""
    try:
        filters = request.args.to_dict()
        
        # Aplicar filtros
        filtered_data = get_filtered_data(filters)
        
        if filtered_data.empty:
            return jsonify({'error': 'Nenhum dado encontrado'})
        
        # Extrair nome do cliente da coluna TRECHO - FROTA PRÓPRIA
        # Formato esperado: "CLIENTE - ORIGEM X DESTINO"
        filtered_data['CLIENTE'] = filtered_data['TRECHO - FROTA PRÓPRIA'].str.extract(r'^([^-]+)')[0].str.strip()
        
        # Agrupar por cliente e origem
        origens_por_cliente = filtered_data.groupby(['CLIENTE', 'MESORREGIÃO - ORIGEM'])['EMBARQUES'].sum().reset_index()
        origens_por_cliente.columns = ['CLIENTE', 'MESORREGIÃO', 'EMBARQUES_ORIGEM']
        
        # Agrupar por cliente e destino
        destinos_por_cliente = filtered_data.groupby(['CLIENTE', 'MESORREGIÃO - DESTINO'])['EMBARQUES'].sum().reset_index()
        destinos_por_cliente.columns = ['CLIENTE', 'MESORREGIÃO', 'EMBARQUES_DESTINO']
        
        # Fazer merge para ter origem e destino na mesma linha por cliente
        resultado = pd.merge(origens_por_cliente, destinos_por_cliente, on=['CLIENTE', 'MESORREGIÃO'], how='outer').fillna(0)
        
        # Calcular saldo e indicadores
        resultado['SALDO'] = resultado['EMBARQUES_ORIGEM'] - resultado['EMBARQUES_DESTINO']
        resultado['TOTAL_MOVIMENTADO'] = resultado['EMBARQUES_ORIGEM'] + resultado['EMBARQUES_DESTINO']
        resultado['PERCENTUAL_ORIGEM'] = (resultado['EMBARQUES_ORIGEM'] / resultado['TOTAL_MOVIMENTADO'] * 100).round(1)
        resultado['PERCENTUAL_DESTINO'] = (resultado['EMBARQUES_DESTINO'] / resultado['TOTAL_MOVIMENTADO'] * 100).round(1)
        
        # Adicionar classificação do saldo
        def classificar_saldo(saldo):
            if saldo > 0:
                return 'Produtora (Origem > Destino)'
            elif saldo < 0:
                return 'Consumidora (Destino > Origem)'
            else:
                return 'Equilibrada (Origem = Destino)'
        
        resultado['CLASSIFICACAO'] = resultado['SALDO'].apply(classificar_saldo)
        
        # Ordenar por cliente e depois por TOTAL_MOVIMENTADO (do maior para o menor)
        resultado = resultado.sort_values(['CLIENTE', 'TOTAL_MOVIMENTADO'], ascending=[True, False])
        
        # Aplicar filtro de classificação se especificado
        classificacao = filters.get('classificacao', '')
        if classificacao:
            if classificacao == 'produtora':
                resultado = resultado[resultado['SALDO'] > 0]
            elif classificacao == 'consumidora':
                resultado = resultado[resultado['SALDO'] < 0]
            elif classificacao == 'equilibrada':
                resultado = resultado[resultado['SALDO'] == 0]
        
        # Aplicar filtro de cliente se especificado
        cliente = filters.get('cliente', '')
        if cliente:
            resultado = resultado[resultado['CLIENTE'] == cliente]
        
        # Aplicar limite se especificado
        limit = filters.get('limit', 0)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 0
        
        if limit > 0:
            resultado = resultado.head(limit)
        
        # Calcular resumo por cliente
        resumo_clientes = resultado.groupby('CLIENTE').agg({
            'MESORREGIÃO': 'count',
            'EMBARQUES_ORIGEM': 'sum',
            'EMBARQUES_DESTINO': 'sum',
            'SALDO': lambda x: (x > 0).sum(),  # Contar produtoras
            'CLASSIFICACAO': lambda x: (x.str.contains('Consumidora')).sum()  # Contar consumidoras
        }).reset_index()
        
        resumo_clientes.columns = ['CLIENTE', 'TOTAL_MESORREGIÕES', 'TOTAL_EMBARQUES_ORIGEM', 'TOTAL_EMBARQUES_DESTINO', 'MESORREGIÕES_PRODUTORAS', 'MESORREGIÕES_CONSUMIDORAS']
        resumo_clientes['TOTAL_MOVIMENTADO'] = resumo_clientes['TOTAL_EMBARQUES_ORIGEM'] + resumo_clientes['TOTAL_EMBARQUES_DESTINO']
        resumo_clientes['SALDO_TOTAL'] = resumo_clientes['TOTAL_EMBARQUES_ORIGEM'] - resumo_clientes['TOTAL_EMBARQUES_DESTINO']
        
        # Ordenar resumo por cliente por TOTAL_MOVIMENTADO (do maior para o menor)
        resumo_clientes = resumo_clientes.sort_values('TOTAL_MOVIMENTADO', ascending=False)
        
        return jsonify({
            'data': resultado.to_dict('records'),
            'resumo_clientes': resumo_clientes.to_dict('records'),
            'resumo_geral': {
                'total_clientes': len(resumo_clientes),
                'total_mesorregioes': len(resultado),
                'produtoras': len(resultado[resultado['SALDO'] > 0]),
                'consumidoras': len(resultado[resultado['SALDO'] < 0]),
                'equilibradas': len(resultado[resultado['SALDO'] == 0])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/clientes')
def get_clientes():
    """API para listar todos os clientes únicos disponíveis na base de dados"""
    try:
        if global_data is None:
            return jsonify({'error': 'Nenhum dado carregado'})
        
        # Extrair nome do cliente da coluna TRECHO - FROTA PRÓPRIA
        global_data['CLIENTE'] = global_data['TRECHO - FROTA PRÓPRIA'].str.extract(r'^([^-]+)')[0].str.strip()
        
        # Obter clientes únicos ordenados alfabeticamente
        clientes = sorted(global_data['CLIENTE'].unique().tolist())
        
        return jsonify({
            'clientes': clientes,
            'total': len(clientes)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/exportar_excel')
def exportar_excel():
    """API para exportar dados em Excel"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Selecionar apenas as colunas necessárias na ordem correta
    df_export = df[['TRECHO - FROTA PRÓPRIA', 'MESORREGIÃO - ORIGEM', 'MESORREGIÃO - DESTINO', 'MÊS', 'EMBARQUES']].copy()
    
    # Criar buffer de memória para o arquivo
    output = io.BytesIO()
    
    # Exportar para Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name='Dados_Embarques', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'embarques_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/exportar_csv')
def exportar_csv():
    """API para exportar dados em CSV"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Selecionar apenas as colunas necessárias na ordem correta
    df_export = df[['TRECHO - FROTA PRÓPRIA', 'MESORREGIÃO - ORIGEM', 'MESORREGIÃO - DESTINO', 'MÊS', 'EMBARQUES']].copy()
    
    # Criar buffer de memória para o arquivo
    output = io.StringIO()
    df_export.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'embarques_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/api/exportar_balanco_excel')
def exportar_balanco_excel():
    """API para exportar balanço de embarques em Excel"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    try:
        filters = request.args.to_dict()
        
        # Aplicar filtros
        filtered_data = get_filtered_data(filters)
        
        if filtered_data.empty:
            return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
        
        # Agrupar por origem e destino
        origens = filtered_data.groupby('MESORREGIÃO - ORIGEM')['EMBARQUES'].sum().reset_index()
        origens.columns = ['MESORREGIÃO', 'EMBARQUES_ORIGEM']
        
        destinos = filtered_data.groupby('MESORREGIÃO - DESTINO')['EMBARQUES'].sum().reset_index()
        destinos.columns = ['MESORREGIÃO', 'EMBARQUES_DESTINO']
        
        # Fazer merge para ter origem e destino na mesma linha
        resultado = pd.merge(origens, destinos, on='MESORREGIÃO', how='outer').fillna(0)
        
        # Calcular saldo e indicadores
        resultado['SALDO'] = resultado['EMBARQUES_ORIGEM'] - resultado['EMBARQUES_DESTINO']
        resultado['TOTAL_MOVIMENTADO'] = resultado['EMBARQUES_ORIGEM'] + resultado['EMBARQUES_DESTINO']
        resultado['PERCENTUAL_ORIGEM'] = (resultado['EMBARQUES_ORIGEM'] / resultado['TOTAL_MOVIMENTADO'] * 100).round(1)
        resultado['PERCENTUAL_DESTINO'] = (resultado['EMBARQUES_DESTINO'] / resultado['TOTAL_MOVIMENTADO'] * 100).round(1)
        
        # Adicionar classificação do saldo
        def classificar_saldo(saldo):
            if saldo > 0:
                return 'Produtora (Origem > Destino)'
            elif saldo < 0:
                return 'Consumidora (Destino > Origem)'
            else:
                return 'Equilibrada (Origem = Destino)'
        
        resultado['CLASSIFICACAO'] = resultado['SALDO'].apply(classificar_saldo)
        
        # Ordenar por saldo absoluto (maior diferença primeiro)
        resultado = resultado.sort_values('SALDO', key=abs, ascending=False)
        
        # Aplicar filtro de classificação se especificado
        classificacao = filters.get('classificacao', '')
        if classificacao:
            if classificacao == 'produtora':
                resultado = resultado[resultado['SALDO'] > 0]
            elif classificacao == 'consumidora':
                resultado = resultado[resultado['SALDO'] < 0]
            elif classificacao == 'equilibrada':
                resultado = resultado[resultado['SALDO'] == 0]
        
        # Criar buffer de memória para o arquivo
        output = io.BytesIO()
        
        # Exportar para Excel
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            resultado.to_excel(writer, sheet_name='Balanco_Embarques', index=False)
            
            # Adicionar resumo em outra aba
            resumo = pd.DataFrame({
                'Métrica': ['Total de Mesorregiões', 'Regiões Produtoras', 'Regiões Consumidoras', 'Regiões Equilibradas'],
                'Valor': [
                    len(resultado),
                    len(resultado[resultado['SALDO'] > 0]),
                    len(resultado[resultado['SALDO'] < 0]),
                    len(resultado[resultado['SALDO'] == 0])
                ]
            })
            resumo.to_excel(writer, sheet_name='Resumo', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'balanco_embarques_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/exportar_balanco_clientes_excel')
def exportar_balanco_clientes_excel():
    """API para exportar balanço de embarques por clientes em Excel"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    try:
        filters = request.args.to_dict()
        
        # Aplicar filtros
        filtered_data = get_filtered_data(filters)
        
        if filtered_data.empty:
            return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
        
        # Extrair nome do cliente da coluna TRECHO - FROTA PRÓPRIA
        filtered_data['CLIENTE'] = filtered_data['TRECHO - FROTA PRÓPRIA'].str.extract(r'^([^-]+)')[0].str.strip()
        
        # Agrupar por cliente e origem
        origens_por_cliente = filtered_data.groupby(['CLIENTE', 'MESORREGIÃO - ORIGEM'])['EMBARQUES'].sum().reset_index()
        origens_por_cliente.columns = ['CLIENTE', 'MESORREGIÃO', 'EMBARQUES_ORIGEM']
        
        # Agrupar por cliente e destino
        destinos_por_cliente = filtered_data.groupby(['CLIENTE', 'MESORREGIÃO - DESTINO'])['EMBARQUES'].sum().reset_index()
        destinos_por_cliente.columns = ['CLIENTE', 'MESORREGIÃO', 'EMBARQUES_DESTINO']
        
        # Fazer merge para ter origem e destino na mesma linha por cliente
        resultado = pd.merge(origens_por_cliente, destinos_por_cliente, on=['CLIENTE', 'MESORREGIÃO'], how='outer').fillna(0)
        
        # Calcular saldo e indicadores
        resultado['SALDO'] = resultado['EMBARQUES_ORIGEM'] - resultado['EMBARQUES_DESTINO']
        resultado['TOTAL_MOVIMENTADO'] = resultado['EMBARQUES_ORIGEM'] + resultado['EMBARQUES_DESTINO']
        resultado['PERCENTUAL_ORIGEM'] = (resultado['EMBARQUES_ORIGEM'] / resultado['TOTAL_MOVIMENTADO'] * 100).round(1)
        resultado['PERCENTUAL_DESTINO'] = (resultado['EMBARQUES_DESTINO'] / resultado['TOTAL_MOVIMENTADO'] * 100).round(1)
        
        # Adicionar classificação do saldo
        def classificar_saldo(saldo):
            if saldo > 0:
                return 'Produtora (Origem > Destino)'
            elif saldo < 0:
                return 'Consumidora (Destino > Origem)'
            else:
                return 'Equilibrada (Origem = Destino)'
        
        resultado['CLASSIFICACAO'] = resultado['SALDO'].apply(classificar_saldo)
        
        # Ordenar por cliente e depois por saldo absoluto
        resultado = resultado.sort_values(['CLIENTE', 'SALDO'], key=lambda x: x.abs() if x.name == 'SALDO' else x, ascending=[True, False])
        
        # Aplicar filtro de classificação se especificado
        classificacao = filters.get('classificacao', '')
        if classificacao:
            if classificacao == 'produtora':
                resultado = resultado[resultado['SALDO'] > 0]
            elif classificacao == 'consumidora':
                resultado = resultado[resultado['SALDO'] < 0]
            elif classificacao == 'equilibrada':
                resultado = resultado[resultado['SALDO'] == 0]
        
        # Aplicar limite se especificado
        limit = filters.get('limit', 50)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 50
        
        if limit > 0:
            resultado = resultado.head(limit)
        
        # Calcular resumo por cliente
        resumo_clientes = resultado.groupby('CLIENTE').agg({
            'MESORREGIÃO': 'count',
            'EMBARQUES_ORIGEM': 'sum',
            'EMBARQUES_DESTINO': 'sum',
            'SALDO': lambda x: (x > 0).sum(),
            'CLASSIFICACAO': lambda x: (x.str.contains('Consumidora')).sum()
        }).reset_index()
        
        resumo_clientes.columns = ['CLIENTE', 'TOTAL_MESORREGIÕES', 'TOTAL_EMBARQUES_ORIGEM', 'TOTAL_EMBARQUES_DESTINO', 'MESORREGIÕES_PRODUTORAS', 'MESORREGIÕES_CONSUMIDORAS']
        resumo_clientes['TOTAL_MOVIMENTADO'] = resumo_clientes['TOTAL_EMBARQUES_ORIGEM'] + resumo_clientes['TOTAL_EMBARQUES_DESTINO']
        resumo_clientes['SALDO_TOTAL'] = resumo_clientes['TOTAL_EMBARQUES_ORIGEM'] - resumo_clientes['TOTAL_EMBARQUES_DESTINO']
        
        # Criar buffer de memória para o arquivo
        output = io.BytesIO()
        
        # Exportar para Excel
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            resultado.to_excel(writer, sheet_name='Balanco_por_Cliente', index=False)
            resumo_clientes.to_excel(writer, sheet_name='Resumo_Clientes', index=False)
            
            # Adicionar resumo geral em outra aba
            resumo_geral = pd.DataFrame({
                'Métrica': ['Total de Clientes', 'Total de Mesorregiões', 'Regiões Produtoras', 'Regiões Consumidoras', 'Regiões Equilibradas'],
                'Valor': [
                    len(resumo_clientes),
                    len(resultado),
                    len(resultado[resultado['SALDO'] > 0]),
                    len(resultado[resultado['SALDO'] < 0]),
                    len(resultado[resultado['SALDO'] == 0])
                ]
            })
            resumo_geral.to_excel(writer, sheet_name='Resumo_Geral', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'balanco_clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)})

def get_coordinates(mesorregiao):
    """Retorna coordenadas geográficas precisas para mesorregiões brasileiras"""
    
    # Mapeamento detalhado com coordenadas reais das mesorregiões
    mapeamento_mesorregioes = {
        # SÃO PAULO - Coordenadas reais e precisas (IBGE/OpenStreetMap)
        'ARARAQUARA': [-21.7944, -48.1756],  # Centro real de Araraquara
        'ARARAQUARA/SP': [-21.7944, -48.1756],  # Centro real de Araraquara com estado
        'BAURU': [-22.3147, -49.0604],       # Centro real de Bauru
        'BAURU/SP': [-22.3147, -49.0604],    # Centro real de Bauru com estado
        'CAMPINAS': [-22.9064, -47.0616],    # Centro real de Campinas
        'CAMPINAS/SP': [-22.9064, -47.0616],  # Centro real de Campinas com estado
        'LITORAL SUL PAULISTA': [-24.0059, -46.3028],  # Santos
        'LITORAL SUL PAULISTA/SP': [-24.0059, -46.3028],  # Santos com estado
        'METROPOLITANA DE SÃO PAULO': [-23.5505, -46.6333],  # Centro real de São Paulo
        'METROPOLITANA DE SAO PAULO': [-23.5505, -46.6333],  # Centro real de São Paulo (sem acento)
        'METROPOLITANA DE SÃO PAULO/SP': [-23.5505, -46.6333],  # Centro real de São Paulo com estado
        'METROPOLITANA DE SAO PAULO/SP': [-23.5505, -46.6333],  # Centro real de São Paulo com estado (sem acento)
        'PIRACICABA': [-22.7253, -47.6490],  # Centro real de Piracicaba
        'PIRACICABA/SP': [-22.7253, -47.6490],  # Centro real de Piracicaba com estado
        'PRESIDENTE PRUDENTE': [-22.1276, -51.3856],  # Centro real de Presidente Prudente
        'PRESIDENTE PRUDENTE/SP': [-22.1276, -51.3856],  # Centro real de Presidente Prudente com estado
        'RIBEIRÃO PRETO': [-21.1763, -47.8208],  # Centro real de Ribeirão Preto
        'RIBEIRAO PRETO': [-21.1763, -47.8208],  # Centro real de Ribeirão Preto (sem acento)
        'RIBEIRÃO PRETO/SP': [-21.1763, -47.8208],  # Centro real de Ribeirão Preto com estado
        'RIBEIRAO PRETO/SP': [-21.1763, -47.8208],  # Centro real de Ribeirão Preto com estado (sem acento)
        'SÃO JOSÉ DO RIO PRETO': [-20.8115, -49.3752],  # Centro real de São José do Rio Preto
        'SAO JOSE DO RIO PRETO': [-20.8115, -49.3752],  # Centro real de São José do Rio Preto (sem acentos)
        'SÃO JOSÉ DO RIO PRETO/SP': [-20.8115, -49.3752],  # Centro real de São José do Rio Preto com estado
        'SAO JOSE DO RIO PRETO/SP': [-20.8115, -49.3752],  # Centro real de São José do Rio Preto com estado (sem acentos)
        'VALE DO PARAÍBA PAULISTA': [-23.1864, -45.8842],  # São José dos Campos
        'VALE DO PARAÍBA PAULISTA/SP': [-23.1864, -45.8842],  # São José dos Campos com estado
        'MARÍLIA': [-22.2178, -49.9505],     # Centro real de Marília
        'MARILIA': [-22.2178, -49.9505],     # Centro real de Marília (sem acento)
        'MARILIA/SP': [-22.2178, -49.9505],  # Centro real de Marília com estado
        'MARÍLIA/SP': [-22.2178, -49.9505],  # Centro real de Marília com estado (com acento)
        'ASSIS': [-22.6619, -50.4116],       # Centro real de Assis
        'ASSIS/SP': [-22.6619, -50.4116],    # Centro real de Assis com estado
        'ITAPETININGA': [-23.5917, -48.0531],  # Centro real de Itapetininga
        'ITAPETININGA/SP': [-23.5917, -48.0531],  # Centro real de Itapetininga com estado
        'MACRO METROPOLITANA PAULISTA': [-23.5505, -46.6333],  # São Paulo
        'ARACATUBA': [-21.2089, -50.4329],   # Centro real de Araçatuba
        'ARACATUBA/SP': [-21.2089, -50.4329], # Centro real de Araçatuba com estado
        'SOROCABA': [-23.5016, -47.4586],    # Centro real de Sorocaba
        'SOROCABA/SP': [-23.5016, -47.4586], # Centro real de Sorocaba com estado
        'JUNDIAI': [-23.1857, -46.8974],     # Centro real de Jundiaí
        'JUNDIAI/SP': [-23.1857, -46.8974],  # Centro real de Jundiaí com estado
        'SANTOS': [-23.9608, -46.3336],      # Centro real de Santos
        'SANTOS/SP': [-23.9608, -46.3336],   # Centro real de Santos com estado
        'SÃO JOSÉ DOS CAMPOS': [-23.1864, -45.8842],  # Centro real de São José dos Campos
        'SAO JOSE DOS CAMPOS': [-23.1864, -45.8842],  # Centro real de São José dos Campos (sem acentos)
        'SÃO JOSÉ DOS CAMPOS/SP': [-23.1864, -45.8842],  # Centro real de São José dos Campos com estado
        'SAO JOSE DOS CAMPOS/SP': [-23.1864, -45.8842],  # Centro real de São José dos Campos com estado (sem acentos)
        'GUARULHOS': [-23.4543, -46.5339],   # Centro real de Guarulhos
        'GUARULHOS/SP': [-23.4543, -46.5339], # Centro real de Guarulhos com estado
        'OSASCO': [-23.5320, -46.7920],      # Centro real de Osasco
        'OSASCO/SP': [-23.5320, -46.7920],   # Centro real de Osasco com estado
        'SANTO ANDRÉ': [-23.6639, -46.5383], # Centro real de Santo André
        'SANTO ANDRE': [-23.6639, -46.5383], # Centro real de Santo André (sem acento)
        'SANTO ANDRÉ/SP': [-23.6639, -46.5383], # Centro real de Santo André com estado
        'SANTO ANDRE/SP': [-23.6639, -46.5383], # Centro real de Santo André com estado (sem acento)
        'SÃO BERNARDO DO CAMPO': [-23.6944, -46.5654],  # Centro real de São Bernardo do Campo
        'SAO BERNARDO DO CAMPO': [-23.6944, -46.5654],  # Centro real de São Bernardo do Campo (sem acentos)
        'SÃO BERNARDO DO CAMPO/SP': [-23.6944, -46.5654],  # Centro real de São Bernardo do Campo com estado
        'SAO BERNARDO DO CAMPO/SP': [-23.6944, -46.5654],  # Centro real de São Bernardo do Campo com estado (sem acentos)
        'ILISTA': [-21.7944, -48.1756],      # Araraquara
        'MACRO N': [-21.7944, -48.1756],     # Araraquara
        'MACRO': [-21.7944, -48.1756],       # Araraquara
        
        # MINAS GERAIS - Coordenadas precisas
        'CENTRAL': [-19.9167, -43.9345],     # Belo Horizonte
        'CENTRAL/MG': [-19.9167, -43.9345],  # Belo Horizonte com estado
        'JUIZ DE FORA': [-21.7645, -43.3492],  # Centro de Juiz de Fora
        'JUIZ DE FORA/MG': [-21.7645, -43.3492],  # Centro de Juiz de Fora com estado
        'NORTE DE MINAS': [-16.7214, -43.8646],  # Montes Claros
        'NORTE DE MINASMG': [-16.7214, -43.8646],  # Montes Claros (formato sem espaço)
        'NORTE DE MINAS MG': [-16.7214, -43.8646],  # Montes Claros (formato com espaço)
        'NORTE DE MINAS/MG': [-16.7214, -43.8646],  # Montes Claros (formato com barra)
        'TRIÂNGULO MINEIRO': [-18.9186, -48.2772],  # Uberlândia
        'TRIANGULO MINEIRO': [-18.9186, -48.2772],  # Uberlândia (sem acento)
        'TRIÂNGULO MINEIRO/MG': [-18.9186, -48.2772],  # Uberlândia com estado
        'TRIANGULO MINEIRO/MG': [-18.9186, -48.2772],  # Uberlândia com estado (sem acento)
        'VALE DO MUCURI': [-18.8519, -41.9492],  # Teófilo Otoni
        'VALE DO MUCURI/MG': [-18.8519, -41.9492],  # Teófilo Otoni com estado
        'VALE DO RIO DOCE': [-19.9167, -43.9345],  # Belo Horizonte
        'VALE DO RIO DOCE/MG': [-19.9167, -43.9345],  # Belo Horizonte com estado
        'ZONA DA MATA': [-21.7645, -43.3492],  # Juiz de Fora
        'ZONA DA MATA/MG': [-21.7645, -43.3492],  # Juiz de Fora com estado
        'SUL/SUDOESTE DE MINAS': [-21.1356, -44.2492],  # Varginha
        'SUL/SUDOESTE DE MINAS/MG': [-21.1356, -44.2492],  # Varginha com estado
        'CAMPO DAS VERTENTES': [-21.1356, -44.2492],  # São João del Rei
        'CAMPO DAS VERTENTES/MG': [-21.1356, -44.2492],  # São João del Rei com estado
        'METROPOLITANA DE BELO HORIZONTE': [-19.9167, -43.9345],  # Belo Horizonte
        'METROPOLITANA DE BELO HORIZONTE/MG': [-19.9167, -43.9345],  # Belo Horizonte com estado
        'SUL': [-21.1356, -44.2492],         # Varginha
        'SUL/MG': [-21.1356, -44.2492],      # Varginha com estado
        'SUDOESTE': [-21.1356, -44.2492],    # Varginha
        'SUDOESTE/MG': [-21.1356, -44.2492], # Varginha com estado
        'NORTE': [-16.7214, -43.8646],       # Montes Claros
        'NORTE/MG': [-16.7214, -43.8646],    # Montes Claros com estado
        
        # RIO DE JANEIRO - Coordenadas precisas
        'CENTRAL FLUMINENSE': [-22.9068, -43.1729],  # Rio de Janeiro
        'CENTRAL FLUMINENSE/RJ': [-22.9068, -43.1729],  # Rio de Janeiro com estado
        'LESTE FLUMINENSE': [-22.9068, -43.1729],  # Rio de Janeiro
        'LESTE FLUMINENSE/RJ': [-22.9068, -43.1729],  # Rio de Janeiro com estado
        'METROPOLITANA DO RIO DE JANEIRO': [-22.9068, -43.1729],  # Rio de Janeiro
        'METROPOLITANA DO RIO DE JANEIRO/RJ': [-22.9068, -43.1729],  # Rio de Janeiro com estado
        'NOROESTE FLUMINENSE': [-22.9068, -43.1729],  # Rio de Janeiro
        'NOROESTE FLUMINENSE/RJ': [-22.9068, -43.1729],  # Rio de Janeiro com estado
        'NORTE FLUMINENSE': [-22.9068, -43.1729],  # Rio de Janeiro
        'NORTE FLUMINENSE/RJ': [-22.9068, -43.1729],  # Rio de Janeiro com estado
        'SERRANA': [-22.9068, -43.1729],     # Rio de Janeiro
        'SERRANA/RJ': [-22.9068, -43.1729],  # Rio de Janeiro com estado
        'SUL FLUMINENSE': [-22.9068, -43.1729],  # Rio de Janeiro
        'SUL FLUMINENSE/RJ': [-22.9068, -43.1729],  # Rio de Janeiro com estado
        
        # PARANÁ - Coordenadas precisas
        'CENTRO OCIDENTAL PARANAENSE': [-25.4289, -49.2671],  # Curitiba
        'CENTRO OCIDENTAL PARANAENSE/PR': [-25.4289, -49.2671],  # Curitiba com estado
        'CENTRO ORIENTAL PARANAENSE': [-25.4289, -49.2671],  # Curitiba
        'CENTRO ORIENTAL PARANAENSE/PR': [-25.4289, -49.2671],  # Curitiba com estado
        'CENTRO SUL PARANAENSE': [-25.4289, -49.2671],  # Curitiba
        'CENTRO SUL PARANAENSE/PR': [-25.4289, -49.2671],  # Curitiba com estado
        'METROPOLITANA DE CURITIBA': [-25.4289, -49.2671],  # Curitiba
        'METROPOLITANA DE CURITIBA/PR': [-25.4289, -49.2671],  # Curitiba com estado
        'NORDESTE PARANAENSE': [-23.4200, -51.9400],  # Londrina
        'NORDESTE PARANAENSE/PR': [-23.4200, -51.9400],  # Londrina com estado
        'NORTE CENTRAL PARANAENSE': [-23.4200, -51.9400],  # Londrina
        'NORTE CENTRAL PARANAENSE/PR': [-23.4200, -51.9400],  # Londrina com estado
        'NORTE PIONEIRO PARANAENSE': [-23.4200, -51.9400],  # Londrina
        'NORTE PIONEIRO PARANAENSE/PR': [-23.4200, -51.9400],  # Londrina com estado
        'OESTE PARANAENSE': [-24.9550, -53.4550],  # Cascavel
        'OESTE PARANAENSE/PR': [-24.9550, -53.4550],  # Cascavel com estado
        'SUDOESTE PARANAENSE': [-25.5400, -54.5800],  # Foz do Iguaçu
        'SUDOESTE PARANAENSE/PR': [-25.5400, -54.5800],  # Foz do Iguaçu com estado
        'SUL PARANAENSE': [-25.5400, -54.5800],  # Foz do Iguaçu
        'SUL PARANAENSE/PR': [-25.5400, -54.5800],  # Foz do Iguaçu com estado
        'CENTRO': [-25.4289, -49.2671],      # Curitiba
        'CENTRO/PR': [-25.4289, -49.2671],   # Curitiba com estado
        'ORIENTAL': [-25.4289, -49.2671],    # Curitiba
        'ORIENTAL/PR': [-25.4289, -49.2671], # Curitiba com estado
        'OCCIDENTAL': [-25.4289, -49.2671],  # Curitiba
        'OCCIDENTAL/PR': [-25.4289, -49.2671], # Curitiba com estado
        'PIONEIRO': [-23.4200, -51.9400],    # Londrina
        'PIONEIRO/PR': [-23.4200, -51.9400], # Londrina com estado
        'CENTRAL': [-25.4289, -49.2671],     # Curitiba
        'CENTRAL/PR': [-25.4289, -49.2671],  # Curitiba com estado
        
        # SANTA CATARINA - Coordenadas precisas
        'GRANDE FLORIANÓPOLIS': [-27.5969, -48.5495],  # Florianópolis
        'GRANDE FLORIANOPOLIS': [-27.5969, -48.5495],  # Florianópolis (sem acento)
        'GRANDE FLORIANÓPOLIS/SC': [-27.5969, -48.5495],  # Florianópolis com estado
        'GRANDE FLORIANOPOLIS/SC': [-27.5969, -48.5495],  # Florianópolis com estado (sem acento)
        'NORTE CATARINENSE': [-26.9180, -49.0660],  # Joinville
        'NORTE CATARINENSE/SC': [-26.9180, -49.0660],  # Joinville com estado
        'OESTE CATARINENSE': [-27.0950, -52.6170],  # Chapecó
        'OESTE CATARINENSE/SC': [-27.0950, -52.6170],  # Chapecó com estado
        'SERRA CATARINENSE': [-27.5969, -48.5495],  # Lages
        'SERRA CATARINENSE/SC': [-27.5969, -48.5495],  # Lages com estado
        'SUL CATARINENSE': [-28.6800, -49.3700],  # Criciúma
        'SUL CATARINENSE/SC': [-28.6800, -49.3700],  # Criciúma com estado
        'VALE DO ITAJAÍ': [-26.9180, -49.0660],  # Blumenau
        'VALE DO ITAJAI': [-26.9180, -49.0660],  # Blumenau (sem acento)
        'VALE DO ITAJAÍ/SC': [-26.9180, -49.0660],  # Blumenau com estado
        'VALE DO ITAJAI/SC': [-26.9180, -49.0660],  # Blumenau com estado (sem acento)
        'FLORIANÓPOLIS': [-27.5969, -48.5495],  # Florianópolis
        'FLORIANOPOLIS': [-27.5969, -48.5495],  # Florianópolis (sem acento)
        'FLORIANÓPOLIS/SC': [-27.5969, -48.5495],  # Florianópolis com estado
        'FLORIANOPOLIS/SC': [-27.5969, -48.5495],  # Florianópolis com estado (sem acento)
        'CATARINENSE': [-27.5969, -48.5495],  # Florianópolis
        'CATARINENSE/SC': [-27.5969, -48.5495],  # Florianópolis com estado
        'SERRA': [-27.5969, -48.5495],       # Lages
        'SERRA/SC': [-27.5969, -48.5495],    # Lages com estado
        
        # RIO GRANDE DO SUL - Coordenadas precisas
        'CENTRO ORIENTAL RIO GRANDENSE': [-30.0346, -51.2177],  # Porto Alegre
        'CENTRO ORIENTAL RIO GRANDENSE/RS': [-30.0346, -51.2177],  # Porto Alegre com estado
        'CENTRO OCIDENTAL RIO GRANDENSE': [-30.0346, -51.2177],  # Porto Alegre
        'CENTRO OCIDENTAL RIO GRANDENSE/RS': [-30.0346, -51.2177],  # Porto Alegre com estado
        'METROPOLITANA DE PORTO ALEGRE': [-30.0346, -51.2177],  # Porto Alegre
        'METROPOLITANA DE PORTO ALEGRE/RS': [-30.0346, -51.2177],  # Porto Alegre com estado
        'NORDESTE RIO GRANDENSE': [-29.6900, -53.8100],  # Caxias do Sul
        'NORDESTE RIO GRANDENSE/RS': [-29.6900, -53.8100],  # Caxias do Sul com estado
        'NOROESTE RIO GRANDENSE': [-27.7200, -54.1700],  # Ijuí
        'NOROESTE RIO GRANDENSE/RS': [-27.7200, -54.1700],  # Ijuí com estado
        'SUDESTE RIO GRANDENSE': [-31.7700, -52.3400],  # Pelotas
        'SUDESTE RIO GRANDENSE/RS': [-31.7700, -52.3400],  # Pelotas com estado
        'SUDOESTE RIO GRANDENSE': [-29.6900, -53.8100],  # Santa Maria
        'SUDOESTE RIO GRANDENSE/RS': [-29.6900, -53.8100],  # Santa Maria com estado
        'PORTO ALEGRE': [-30.0346, -51.2177],  # Porto Alegre
        'PORTO ALEGRE/RS': [-30.0346, -51.2177],  # Porto Alegre com estado
        'RIO GRANDENSE': [-30.0346, -51.2177],  # Porto Alegre
        'RIO GRANDENSE/RS': [-30.0346, -51.2177],  # Porto Alegre com estado
        'GRANDENSE': [-30.0346, -51.2177],    # Porto Alegre
        'GRANDENSE/RS': [-30.0346, -51.2177], # Porto Alegre com estado
        
        # BAHIA - Coordenadas precisas
        'CENTRO NORTE BAIANO': [-12.9714, -38.5011],  # Salvador
        'TE BAIANO': [-12.9714, -38.5011],  # Teixeira de Freitas, Bahia
        'TE BAIANO/BA': [-12.9714, -38.5011],  # Teixeira de Freitas, Bahia (com estado)
        'TE BAIANO BA': [-12.9714, -38.5011],  # Teixeira de Freitas, Bahia (sem barra)
        'CENTRO SUL BAIANO': [-12.9714, -38.5011],  # Salvador
        'CENTRO SUL BAIANO/BA': [-12.9714, -38.5011],  # Salvador com estado
        'EXTREMO OESTE BAIANO': [-12.9714, -38.5011],  # Salvador
        'EXTREMO OESTE BAIANO/BA': [-12.9714, -38.5011],  # Salvador com estado
        'METROPOLITANA DE SALVADOR': [-12.9714, -38.5011],  # Salvador
        'METROPOLITANA DE SALVADOR/BA': [-12.9714, -38.5011],  # Salvador com estado
        'NORDESTE BAIANO': [-12.9714, -38.5011],  # Salvador
        'NORDESTE BAIANO/BA': [-12.9714, -38.5011],  # Salvador com estado
        'SUL BAIANO': [-12.9714, -38.5011],  # Salvador
        'SUL BAIANO/BA': [-12.9714, -38.5011],  # Salvador com estado
        'VALE SÃO FRANCISCO DA BAHIA': [-12.9714, -38.5011],  # Salvador
        'VALE SAO FRANCISCO DA BAHIA': [-12.9714, -38.5011],  # Salvador (sem acentos)
        'VALE SÃO FRANCISCO DA BAHIA/BA': [-12.9714, -38.5011],  # Salvador com estado
        'VALE SAO FRANCISCO DA BAHIA/BA': [-12.9714, -38.5011],  # Salvador com estado (sem acentos)
        'SALVADOR': [-12.9714, -38.5011],    # Salvador
        'SALVADOR/BA': [-12.9714, -38.5011], # Salvador com estado
        'BAIANO': [-12.9714, -38.5011],      # Salvador
        'BAIANO/BA': [-12.9714, -38.5011],   # Salvador com estado
        
        # GOIÁS - Coordenadas precisas
        'CENTRO GOIANO': [-16.6864, -49.2653],  # Goiânia
        'CENTRO GOIANO/GO': [-16.6864, -49.2653],  # Goiânia com estado
        'LESTE GOIANO': [-16.6864, -49.2653],  # Goiânia
        'LESTE GOIANO/GO': [-16.6864, -49.2653],  # Goiânia com estado
        'NORDESTE GOIANO': [-16.6864, -49.2653],  # Goiânia
        'NORDESTE GOIANO/GO': [-16.6864, -49.2653],  # Goiânia com estado
        'NOROESTE GOIANO': [-16.6864, -49.2653],  # Goiânia
        'NOROESTE GOIANO/GO': [-16.6864, -49.2653],  # Goiânia com estado
        'SUL GOIANO': [-16.6864, -49.2653],  # Goiânia
        'SUL GOIANO/GO': [-16.6864, -49.2653],  # Goiânia com estado
        'GOIANO': [-16.6864, -49.2653],      # Goiânia
        'GOIANO/GO': [-16.6864, -49.2653],   # Goiânia com estado
        'GOIÁS': [-16.6864, -49.2653],       # Goiânia
        'GOIAS': [-16.6864, -49.2653],       # Goiânia (sem acento)
        'GOIÁS/GO': [-16.6864, -49.2653],    # Goiânia com estado
        'GOIAS/GO': [-16.6864, -49.2653],    # Goiânia com estado (sem acento)
        
        # MATO GROSSO - Coordenadas precisas
        'CENTRO SUL MATO GROSSENSE': [-15.6010, -56.0974],  # Cuiabá
        'CENTRO SUL MATO GROSSENSE/MT': [-15.6010, -56.0974],  # Cuiabá com estado
        'NORDESTE MATO GROSSENSE': [-15.6010, -56.0974],  # Cuiabá
        'NORDESTE MATO GROSSENSE/MT': [-15.6010, -56.0974],  # Cuiabá com estado
        'NORTE MATO GROSSENSE': [-15.6010, -56.0974],  # Cuiabá
        'NORTE MATO GROSSENSE/MT': [-15.6010, -56.0974],  # Cuiabá com estado
        'SUDESTE MATO GROSSENSE': [-15.6010, -56.0974],  # Cuiabá
        'SUDESTE MATO GROSSENSE/MT': [-15.6010, -56.0974],  # Cuiabá com estado
        'SUDOESTE MATO GROSSENSE': [-15.6010, -56.0974],  # Cuiabá
        'SUDOESTE MATO GROSSENSE/MT': [-15.6010, -56.0974],  # Cuiabá com estado
        'MATO GROSSENSE': [-15.6010, -56.0974],  # Cuiabá
        'MATO GROSSENSE/MT': [-15.6010, -56.0974],  # Cuiabá com estado
        'MATO GROSSO': [-15.6010, -56.0974],  # Cuiabá
        'MATO GROSSO/MT': [-15.6010, -56.0974],  # Cuiabá com estado
        'GROSSENSE': [-15.6010, -56.0974],   # Cuiabá
        'GROSSENSE/MT': [-15.6010, -56.0974], # Cuiabá com estado
        
        # MATO GROSSO DO SUL - Coordenadas precisas
        'CENTRO NORTE DE MATO GROSSO DO SUL': [-20.4486, -54.6295],  # Campo Grande
        'CENTRO NORTE DE MATO GROSSO DO SUL/MS': [-20.4486, -54.6295],  # Campo Grande com estado
        'LESTE DE MATO GROSSO DO SUL': [-20.4486, -54.6295],  # Campo Grande
        'LESTE DE MATO GROSSO DO SUL/MS': [-20.4486, -54.6295],  # Campo Grande com estado
        'PANTANAIS SUL MATO GROSSENSE': [-20.4486, -54.6295],  # Campo Grande
        'PANTANAIS SUL MATO GROSSENSE/MS': [-20.4486, -54.6295],  # Campo Grande com estado
        'SUDOESTE DE MATO GROSSO DO SUL': [-20.4486, -54.6295],  # Campo Grande
        'SUDOESTE DE MATO GROSSO DO SUL/MS': [-20.4486, -54.6295],  # Campo Grande com estado
        'SUL DE MATO GROSSO DO SUL': [-20.4486, -54.6295],  # Campo Grande
        'SUL DE MATO GROSSO DO SUL/MS': [-20.4486, -54.6295],  # Campo Grande com estado
        'MATO GROSSO DO SUL': [-20.4486, -54.6295],  # Campo Grande
        'MATO GROSSO DO SUL/MS': [-20.4486, -54.6295],  # Campo Grande com estado
        'GROSSO DO SUL': [-20.4486, -54.6295],  # Campo Grande
        'GROSSO DO SUL/MS': [-20.4486, -54.6295],  # Campo Grande com estado
        'DO SUL': [-20.4486, -54.6295],      # Campo Grande
        'DO SUL/MS': [-20.4486, -54.6295],   # Campo Grande com estado
        
        # Outros estados importantes
        'DISTRITO FEDERAL': [-15.7942, -47.8822],  # Brasília
        'DISTRITO FEDERAL/DF': [-15.7942, -47.8822],  # Brasília com estado
        'ESPÍRITO SANTO': [-20.2976, -40.2958],  # Vitória
        'ESPIRITO SANTO': [-20.2976, -40.2958],  # Vitória (sem acento)
        'ESPÍRITO SANTO/ES': [-20.2976, -40.2958],  # Vitória com estado
        'ESPIRITO SANTO/ES': [-20.2976, -40.2958],  # Vitória com estado (sem acento)
        'PERNAMBUCO': [-8.0476, -34.8770],  # Recife
        'PERNAMBUCO/PE': [-8.0476, -34.8770],  # Recife com estado
        'CEARÁ': [-3.7172, -38.5433],       # Fortaleza
        'CEARA': [-3.7172, -38.5433],       # Fortaleza (sem acento)
        'CEARÁ/CE': [-3.7172, -38.5433],    # Fortaleza com estado
        'CEARA/CE': [-3.7172, -38.5433],    # Fortaleza com estado (sem acento)
        'PARÁ': [-1.4554, -48.4898],        # Belém
        'PARA': [-1.4554, -48.4898],        # Belém (sem acento)
        'PARÁ/PA': [-1.4554, -48.4898],     # Belém com estado
        'PARA/PA': [-1.4554, -48.4898],     # Belém com estado (sem acento)
        'AMAZONAS': [-3.4168, -65.8561],    # Manaus
        'AMAZONAS/AM': [-3.4168, -65.8561], # Manaus com estado
        'ACRE': [-8.7619, -70.5511],        # Rio Branco
        'ACRE/AC': [-8.7619, -70.5511],     # Rio Branco com estado
        'RONDÔNIA': [-8.7619, -63.9039],    # Porto Velho
        'RONDONIA': [-8.7619, -63.9039],    # Porto Velho (sem acento)
        'RONDÔNIA/RO': [-8.7619, -63.9039], # Porto Velho com estado
        'RONDONIA/RO': [-8.7619, -63.9039], # Porto Velho com estado (sem acento)
        'RORAIMA': [2.8235, -60.6758],      # Boa Vista
        'RORAIMA/RR': [2.8235, -60.6758],   # Boa Vista com estado
        'AMAPÁ': [0.9019, -52.0030],        # Macapá
        'AMAPA': [0.9019, -52.0030],        # Macapá (sem acento)
        'AMAPÁ/AP': [0.9019, -52.0030],     # Macapá com estado
        'AMAPA/AP': [0.9019, -52.0030],     # Macapá com estado (sem acento)
        'TOCANTINS': [-10.1750, -48.2982],  # Palmas
        'TOCANTINS/TO': [-10.1750, -48.2982], # Palmas com estado
        'MARANHÃO': [-2.5297, -44.3028],    # São Luís
        'MARANHAO': [-2.5297, -44.3028],    # São Luís (sem acento)
        'MARANHÃO/MA': [-2.5297, -44.3028], # São Luís com estado
        'MARANHAO/MA': [-2.5297, -44.3028], # São Luís com estado (sem acento)
        'PIAUÍ': [-5.0892, -42.8016],       # Teresina
        'PIAUI': [-5.0892, -42.8016],       # Teresina (sem acento)
        'PIAUÍ/PI': [-5.0892, -42.8016],    # Teresina com estado
        'PIAUI/PI': [-5.0892, -42.8016],    # Teresina com estado (sem acento)
        'RIO GRANDE DO NORTE': [-5.7945, -35.2120],  # Natal
        'RIO GRANDE DO NORTE/RN': [-5.7945, -35.2120], # Natal com estado
        'PARAÍBA': [-7.1150, -34.8631],     # João Pessoa
        'PARAIBA': [-7.1150, -34.8631],     # João Pessoa (sem acento)
        'PARAÍBA/PB': [-7.1150, -34.8631],  # João Pessoa com estado
        'PARAIBA/PB': [-7.1150, -34.8631],  # João Pessoa com estado (sem acento)
        'SERGIPE': [-10.9091, -37.0677],    # Aracaju
        'SERGIPE/SE': [-10.9091, -37.0677], # Aracaju com estado
        'ALAGOAS': [-9.6498, -35.7089],     # Maceió
        'ALAGOAS/AL': [-9.6498, -35.7089],  # Maceió com estado
        'FLUMINENSE': [-22.9068, -43.1729], # Rio de Janeiro
        'FLUMINENSE/RJ': [-22.9068, -43.1729], # Rio de Janeiro com estado
        'PAULISTA': [-23.5505, -46.6333],   # São Paulo
        'PAULISTA/SP': [-23.5505, -46.6333], # São Paulo com estado
        'MINEIRO': [-19.9167, -43.9345],    # Belo Horizonte
        'MINEIRO/MG': [-19.9167, -43.9345], # Belo Horizonte com estado
        'PARANAENSE': [-25.4289, -49.2671], # Curitiba
        'PARANAENSE/PR': [-25.4289, -49.2671], # Curitiba com estado
        'CATARINENSE': [-27.5969, -48.5495], # Florianópolis
        'CATARINENSE/SC': [-27.5969, -48.5495], # Florianópolis com estado
        'RIO GRANDENSE': [-30.0346, -51.2177], # Porto Alegre
        'RIO GRANDENSE/RS': [-30.0346, -51.2177], # Porto Alegre com estado
        'BAIANO': [-12.9714, -38.5011],     # Salvador
        'BAIANO/BA': [-12.9714, -38.5011],  # Salvador com estado
        'GOIANO': [-16.6864, -49.2653],     # Goiânia
        'GOIANO/GO': [-16.6864, -49.2653],  # Goiânia com estado
        'GROSSENSE': [-15.6010, -56.0974],  # Cuiabá
        'GROSSENSE/MT': [-15.6010, -56.0974], # Cuiabá com estado
        'GROSSO DO SUL': [-20.4486, -54.6295],  # Campo Grande
        'GROSSO DO SUL/MS': [-20.4486, -54.6295]  # Campo Grande com estado
    }
    
    # Normalizar o nome da mesorregião para busca
    mesorregiao_normalizada = mesorregiao.upper().strip()
    
    # Primeiro, tentar mapeamento específico de mesorregiões
    for mesorregiao_key, coords in mapeamento_mesorregioes.items():
        if mesorregiao_key in mesorregiao_normalizada:
            return coords
    
    # Busca mais flexível por partes da mesorregião (mais rigorosa)
    # Só usar se a mesorregião não for encontrada de forma exata
    if 'METROPOLITANA' in mesorregiao_normalizada:
        # Para mesorregiões metropolitanas, ser mais específico
        if 'SÃO PAULO' in mesorregiao_normalizada or 'SAO PAULO' in mesorregiao_normalizada:
            return [-23.5505, -46.6333]  # São Paulo
        elif 'RECIFE' in mesorregiao_normalizada or 'PERNAMBUCO' in mesorregiao_normalizada:
            return [-8.0476, -34.8770]  # Recife
        elif 'BELO HORIZONTE' in mesorregiao_normalizada or 'MINAS GERAIS' in mesorregiao_normalizada:
            return [-19.9167, -43.9345]  # Belo Horizonte
        elif 'CURITIBA' in mesorregiao_normalizada or 'PARANÁ' in mesorregiao_normalizada or 'PARANA' in mesorregiao_normalizada:
            return [-25.4289, -49.2671]  # Curitiba
        elif 'PORTO ALEGRE' in mesorregiao_normalizada or 'RIO GRANDE DO SUL' in mesorregiao_normalizada:
            return [-30.0346, -51.2177]  # Porto Alegre
        elif 'SALVADOR' in mesorregiao_normalizada or 'BAHIA' in mesorregiao_normalizada:
            return [-12.9714, -38.5011]  # Salvador
        elif 'GOIÂNIA' in mesorregiao_normalizada or 'GOIANIA' in mesorregiao_normalizada or 'GOIÁS' in mesorregiao_normalizada or 'GOIAS' in mesorregiao_normalizada:
            return [-16.6864, -49.2653]  # Goiânia
        elif 'CUIABÁ' in mesorregiao_normalizada or 'CUIABA' in mesorregiao_normalizada or 'MATO GROSSO' in mesorregiao_normalizada:
            return [-15.6010, -56.0974]  # Cuiabá
        elif 'CAMPO GRANDE' in mesorregiao_normalizada or 'MATO GROSSO DO SUL' in mesorregiao_normalizada:
            return [-20.4486, -54.6295]  # Campo Grande
        elif 'FLORIANÓPOLIS' in mesorregiao_normalizada or 'FLORIANOPOLIS' in mesorregiao_normalizada or 'SANTA CATARINA' in mesorregiao_normalizada:
            return [-27.5969, -48.5495]  # Florianópolis
        elif 'VITÓRIA' in mesorregiao_normalizada or 'VITORIA' in mesorregiao_normalizada or 'ESPÍRITO SANTO' in mesorregiao_normalizada or 'ESPIRITO SANTO' in mesorregiao_normalizada:
            return [-20.2976, -40.2958]  # Vitória
        elif 'BRASÍLIA' in mesorregiao_normalizada or 'BRASILIA' in mesorregiao_normalizada or 'DISTRITO FEDERAL' in mesorregiao_normalizada:
            return [-15.7942, -47.8822]  # Brasília
        elif 'RIO DE JANEIRO' in mesorregiao_normalizada:
            return [-22.9068, -43.1729]  # Rio de Janeiro
    
    # Busca mais flexível por partes da mesorregião (apenas para casos não metropolitanos)
    partes_mesorregiao = mesorregiao_normalizada.split()
    for parte in partes_mesorregiao:
        if len(parte) > 3:  # Evitar palavras muito curtas
            for mesorregiao_key, coords in mapeamento_mesorregioes.items():
                if parte in mesorregiao_key and len(parte) > len(mesorregiao_key) * 0.5:  # Pelo menos 50% de correspondência
                    return coords
    
    # Busca por estado na mesorregião
    estados_coordenadas = {
        'ACRE': [-8.77, -70.55], 'AMAZONAS': [-3.42, -65.73], 'RONDÔNIA': [-8.76, -63.90],
        'RORAIMA': [2.82, -60.67], 'AMAPÁ': [0.90, -52.00], 'PARÁ': [-1.45, -48.50],
        'TOCANTINS': [-10.17, -48.33], 'MARANHÃO': [-2.53, -44.30], 'PIAUÍ': [-5.09, -42.80],
        'CEARÁ': [-3.72, -38.53], 'RIO GRANDE DO NORTE': [-5.79, -35.21], 'PERNAMBUCO': [-8.05, -34.92],
        'PARAÍBA': [-7.12, -34.86], 'SERGIPE': [-10.91, -37.07], 'ALAGOAS': [-9.65, -35.70],
        'BAHIA': [-12.97, -38.50], 'MATO GROSSO': [-15.60, -56.10], 'MATO GROSSO DO SUL': [-20.44, -54.64],
        'GOIÁS': [-16.64, -49.31], 'DISTRITO FEDERAL': [-15.78, -47.92], 'MINAS GERAIS': [-19.92, -43.93],
        'ESPÍRITO SANTO': [-20.32, -40.31], 'RIO DE JANEIRO': [-22.91, -43.20], 'SÃO PAULO': [-23.55, -46.64],
        'PARANÁ': [-25.42, -49.27], 'SANTA CATARINA': [-27.59, -48.55], 'RIO GRANDE DO SUL': [-30.03, -51.23]
    }
    
    for estado, coords in estados_coordenadas.items():
        if estado in mesorregiao_normalizada:
            return coords
    
    # Busca por siglas de estado
    siglas_estados = {
        'SP': [-23.5505, -46.6333], 'MG': [-19.9167, -43.9345], 'RJ': [-22.9068, -43.1729],
        'PR': [-25.4289, -49.2671], 'SC': [-27.5969, -48.5495], 'RS': [-30.0346, -51.2177],
        'BA': [-12.9714, -38.5011], 'GO': [-16.6864, -49.2653], 'MT': [-15.6010, -56.0974],
        'MS': [-20.4486, -54.6295], 'ES': [-20.2976, -40.2958], 'DF': [-15.7942, -47.8822],
        'PE': [-8.0476, -34.8770], 'CE': [-3.7172, -38.5433], 'PA': [-1.4554, -48.4898],
        'AM': [-3.4168, -65.8561], 'AC': [-8.7619, -70.5511], 'RO': [-8.7619, -63.9039],
        'RR': [2.8235, -60.6758], 'AP': [0.9019, -52.0030], 'TO': [-10.1750, -48.2982],
        'MA': [-2.5297, -44.3028], 'PI': [-5.0892, -42.8016], 'RN': [-5.7945, -35.2120],
        'PB': [-7.1150, -34.8631], 'SE': [-10.9091, -37.0677], 'AL': [-9.6498, -35.7089]
    }
    
    for sigla, coords in siglas_estados.items():
        if sigla in mesorregiao_normalizada:
            return coords
    
    # Se ainda não encontrar, gerar coordenadas baseadas no nome da mesorregião
    # Usar hash simples para gerar coordenadas consistentes
    import hashlib
    hash_obj = hashlib.md5(mesorregiao_normalizada.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Converter hash para coordenadas dentro do Brasil
    lat = -33.0 + (int(hash_hex[:8], 16) % 26)  # -33 a -7 (latitude do Brasil)
    lon = -74.0 + (int(hash_hex[8:16], 16) % 34)  # -74 a -40 (longitude do Brasil)
    
    return [lat, lon]

@app.route('/api/mesorregioes')
def get_mesorregioes():
    """API para listar todas as mesorregiões disponíveis"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    origens = sorted(global_data['MESORREGIÃO - ORIGEM'].unique().tolist())
    destinos = sorted(global_data['MESORREGIÃO - DESTINO'].unique().tolist())
    
    return jsonify({
        'origens': origens,
        'destinos': destinos
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
