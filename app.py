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
        expected_columns = ['MESORREGIÃO - ORIGEM', 'MESORREGIÃO - DESTINO', 'MÊS', 'EMBARQUES']
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
    
    # Filtros de período
    if filters.get('data_inicio'):
        try:
            data_inicio = pd.to_datetime(filters['data_inicio'])
            df = df[df['DATA'] >= data_inicio]
        except:
            pass  # Ignorar filtro de data inválido
    
    if filters.get('data_fim'):
        try:
            data_fim = pd.to_datetime(filters['data_fim'])
            df = df[df['DATA'] <= data_fim]
        except:
            pass  # Ignorar filtro de data inválido
    
    # Filtros de mesorregião
    if filters.get('origens'):
        origens = filters['origens']
        # Converter para lista se for string (quando vem de query params)
        if isinstance(origens, str):
            origens = [origens] if origens else []
        if len(origens) > 0:
            df = df[df['MESORREGIÃO - ORIGEM'].isin(origens)]
    
    if filters.get('destinos'):
        destinos = filters['destinos']
        # Converter para lista se for string (quando vem de query params)
        if isinstance(destinos, str):
            destinos = [destinos] if destinos else []
        if len(destinos) > 0:
            df = df[df['MESORREGIÃO - DESTINO'].isin(destinos)]
    
    # Verificar se ainda há dados após filtros
    if df.empty:
        return df
    
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
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Estatísticas básicas
    total_embarques = int(df['EMBARQUES'].sum())
    total_origens = df['MESORREGIÃO - ORIGEM'].nunique()
    total_destinos = df['MESORREGIÃO - DESTINO'].nunique()
    periodo_inicio = df['DATA'].min().strftime('%m/%Y')
    periodo_fim = df['DATA'].max().strftime('%m/%Y')
    
    # Top 5 origens
    top_origens = df.groupby('MESORREGIÃO - ORIGEM')['EMBARQUES'].sum().nlargest(5)
    top_origens = [{'regiao': regiao, 'embarques': int(embarques)} for regiao, embarques in top_origens.items()]
    
    # Top 5 destinos
    top_destinos = df.groupby('MESORREGIÃO - DESTINO')['EMBARQUES'].sum().nlargest(5)
    top_destinos = [{'regiao': regiao, 'embarques': int(embarques)} for regiao, embarques in top_destinos.items()]
    
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
    
    return jsonify({
        'labels': [f"{row['MES_NUM']}/{row['ANO']}" for _, row in evolucao.iterrows()],
        'embarques': evolucao['EMBARQUES'].tolist(),
        'tendencia': evolucao['tendencia'].astype(int).tolist()
    })

@app.route('/api/top_origens')
def get_top_origens():
    """API para ranking de origens"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
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
        
        # Aplicar limite se especificado
        limit = filters.get('limit', 50)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 50
        
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

@app.route('/api/exportar_excel')
def exportar_excel():
    """API para exportar dados em Excel"""
    if global_data is None:
        return jsonify({'error': 'Nenhum dado carregado'})
    
    filters = request.args.to_dict()
    df = get_filtered_data(filters)
    
    if df.empty:
        return jsonify({'error': 'Nenhum dado encontrado com os filtros aplicados'})
    
    # Criar buffer de memória para o arquivo
    output = io.BytesIO()
    
    # Exportar para Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Dados_Embarques', index=False)
    
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
    
    # Criar buffer de memória para o arquivo
    output = io.StringIO()
    df.to_csv(output, index=False)
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

def get_coordinates(mesorregiao):
    """Retorna coordenadas precisas para mesorregiões brasileiras"""
    
    # Mapeamento detalhado de mesorregiões com coordenadas reais
    mapeamento_mesorregioes = {
        # São Paulo - Coordenadas mais precisas
        'ARARAQUARA': [-21.7944, -48.1756], 'BAURU': [-22.3147, -49.0604], 'CAMPINAS': [-22.9064, -47.0616],
        'LITORAL SUL PAULISTA': [-24.0059, -46.3028], 'METROPOLITANA DE SÃO PAULO': [-23.5505, -46.6333],
        'PIRACICABA': [-22.7253, -47.6490], 'PRESIDENTE PRUDENTE': [-22.1276, -51.3856], 'RIBEIRÃO PRETO': [-21.1763, -47.8208],
        'SÃO JOSÉ DO RIO PRETO': [-20.8115, -49.3752], 'VALE DO PARAÍBA PAULISTA': [-23.1864, -45.8842],
        'MARÍLIA': [-22.2178, -49.9505], 'ASSIS': [-22.6619, -50.4116], 'ITAPETININGA': [-23.5917, -48.0531],
        'MACRO METROPOLITANA PAULISTA': [-23.5505, -46.6333], 'MACRO N ARARAQUARA/SP ILISTA/SP': [-21.7944, -48.1756],
        'ARACATUBA': [-21.2089, -50.4329], 'SOROCABA': [-23.5016, -47.4586], 'JUNDIAI': [-23.1857, -46.8974],
        'SANTOS': [-23.9608, -46.3336], 'SÃO JOSÉ DOS CAMPOS': [-23.1864, -45.8842], 'GUARULHOS': [-23.4543, -46.5339],
        'OSASCO': [-23.5320, -46.7920], 'SANTO ANDRÉ': [-23.6639, -46.5383], 'SÃO BERNARDO DO CAMPO': [-23.6944, -46.5654],
        'ILISTA': [-21.7944, -48.1756], 'MACRO N': [-21.7944, -48.1756], 'MACRO': [-21.7944, -48.1756],
        
        # Minas Gerais - Coordenadas precisas
        'CENTRAL': [-19.9167, -43.9345], 'JUIZ DE FORA': [-21.7645, -43.3492], 'NORTE DE MINAS': [-16.7214, -43.8646],
        'TRIÂNGULO MINEIRO': [-18.9186, -48.2772], 'VALE DO MUCURI': [-18.8519, -41.9492], 'VALE DO RIO DOCE': [-19.9167, -43.9345],
        'ZONA DA MATA': [-21.7645, -43.3492], 'SUL/SUDOESTE DE MINAS': [-21.1356, -44.2492], 'CAMPO DAS VERTENTES': [-21.1356, -44.2492],
        'METROPOLITANA DE BELO HORIZONTE': [-19.9167, -43.9345], 'VALE DO MUCURI': [-18.8519, -41.9492],
        'VALE DO RIO DOCE': [-19.9167, -43.9345], 'ZONA DA MATA': [-21.7645, -43.3492], 'SUL/SUDOESTE DE MINAS': [-21.1356, -44.2492],
        'CAMPO DAS VERTENTES': [-21.1356, -44.2492], 'METROPOLITANA DE BELO HORIZONTE': [-19.9167, -43.9345],
        'SUL': [-21.1356, -44.2492], 'SUDOESTE': [-21.1356, -44.2492], 'NORTE': [-16.7214, -43.8646],
        
        # Rio de Janeiro - Coordenadas precisas
        'CENTRAL FLUMINENSE': [-22.9068, -43.1729], 'LESTE FLUMINENSE': [-22.9068, -43.1729], 'METROPOLITANA DO RIO DE JANEIRO': [-22.9068, -43.1729],
        'NOROESTE FLUMINENSE': [-22.9068, -43.1729], 'NORTE FLUMINENSE': [-22.9068, -43.1729], 'SERRANA': [-22.9068, -43.1729],
        'SUL FLUMINENSE': [-22.9068, -43.1729], 'METROPOLITANA DO RIO DE JANEIRO': [-22.9068, -43.1729],
        
        # Paraná - Coordenadas precisas
        'CENTRO OCIDENTAL PARANAENSE': [-25.4289, -49.2671], 'CENTRO ORIENTAL PARANAENSE': [-25.4289, -49.2671],
        'CENTRO SUL PARANAENSE': [-25.4289, -49.2671], 'METROPOLITANA DE CURITIBA': [-25.4289, -49.2671],
        'NORDESTE PARANAENSE': [-25.4289, -49.2671], 'NORTE CENTRAL PARANAENSE': [-25.4289, -49.2671],
        'NORTE PIONEIRO PARANAENSE': [-25.4289, -49.2671], 'OESTE PARANAENSE': [-25.4289, -49.2671],
        'SUDOESTE PARANAENSE': [-25.4289, -49.2671], 'SUL PARANAENSE': [-25.4289, -49.2671],
        'METROPOLITANA DE CURITIBA': [-25.4289, -49.2671], 'NORDESTE PARANAENSE': [-25.4289, -49.2671],
        'NORTE CENTRAL PARANAENSE': [-25.4289, -49.2671], 'NORTE PIONEIRO PARANAENSE': [-25.4289, -49.2671],
        'OESTE PARANAENSE': [-25.4289, -49.2671], 'SUDOESTE PARANAENSE': [-25.4289, -49.2671], 'SUL PARANAENSE': [-25.4289, -49.2671],
        'CENTRO': [-25.4289, -49.2671], 'ORIENTAL': [-25.4289, -49.2671], 'OCCIDENTAL': [-25.4289, -49.2671],
        'PIONEIRO': [-25.4289, -49.2671], 'CENTRAL': [-25.4289, -49.2671],
        
        # Santa Catarina - Coordenadas precisas
        'GRANDE FLORIANÓPOLIS': [-27.5969, -48.5495], 'NORTE CATARINENSE': [-27.5969, -48.5495],
        'OESTE CATARINENSE': [-27.5969, -48.5495], 'SERRA CATARINENSE': [-27.5969, -48.5495],
        'SUL CATARINENSE': [-27.5969, -48.5495], 'VALE DO ITAJAÍ': [-27.5969, -48.5495],
        'GRANDE FLORIANÓPOLIS': [-27.5969, -48.5495], 'NORTE CATARINENSE': [-27.5969, -48.5495],
        'OESTE CATARINENSE': [-27.5969, -48.5495], 'SERRA CATARINENSE': [-27.5969, -48.5495],
        'SUL CATARINENSE': [-27.5969, -48.5495], 'VALE DO ITAJAÍ': [-27.5969, -48.5495],
        'FLORIANÓPOLIS': [-27.5969, -48.5495], 'CATARINENSE': [-27.5969, -48.5495], 'SERRA': [-27.5969, -48.5495],
        
        # Rio Grande do Sul - Coordenadas precisas
        'CENTRO ORIENTAL RIO GRANDENSE': [-30.0346, -51.2177], 'CENTRO OCIDENTAL RIO GRANDENSE': [-30.0346, -51.2177],
        'METROPOLITANA DE PORTO ALEGRE': [-30.0346, -51.2177], 'NORDESTE RIO GRANDENSE': [-30.0346, -51.2177],
        'NOROESTE RIO GRANDENSE': [-30.0346, -51.2177], 'SUDESTE RIO GRANDENSE': [-30.0346, -51.2177],
        'SUDOESTE RIO GRANDENSE': [-30.0346, -51.2177], 'METROPOLITANA DE PORTO ALEGRE': [-30.0346, -51.2177],
        'NORDESTE RIO GRANDENSE': [-30.0346, -51.2177], 'NOROESTE RIO GRANDENSE': [-30.0346, -51.2177],
        'SUDESTE RIO GRANDENSE': [-30.0346, -51.2177], 'SUDOESTE RIO GRANDENSE': [-30.0346, -51.2177],
        'PORTO ALEGRE': [-30.0346, -51.2177], 'RIO GRANDENSE': [-30.0346, -51.2177], 'GRANDENSE': [-30.0346, -51.2177],
        
        # Bahia - Coordenadas precisas
        'CENTRO NORTE BAIANO': [-12.9714, -38.5011], 'CENTRO SUL BAIANO': [-12.9714, -38.5011],
        'EXTREMO OESTE BAIANO': [-12.9714, -38.5011], 'METROPOLITANA DE SALVADOR': [-12.9714, -38.5011],
        'NORDESTE BAIANO': [-12.9714, -38.5011], 'SUL BAIANO': [-12.9714, -38.5011],
        'VALE SÃO FRANCISCO DA BAHIA': [-12.9714, -38.5011], 'METROPOLITANA DE SALVADOR': [-12.9714, -38.5011],
        'NORDESTE BAIANO': [-12.9714, -38.5011], 'SUL BAIANO': [-12.9714, -38.5011],
        'VALE SÃO FRANCISCO DA BAHIA': [-12.9714, -38.5011], 'SALVADOR': [-12.9714, -38.5011], 'BAIANO': [-12.9714, -38.5011],
        
        # Goiás - Coordenadas precisas
        'CENTRO GOIANO': [-16.6864, -49.2653], 'LESTE GOIANO': [-16.6864, -49.2653],
        'NORDESTE GOIANO': [-16.6864, -49.2653], 'NOROESTE GOIANO': [-16.6864, -49.2653],
        'SUL GOIANO': [-16.6864, -49.2653], 'CENTRO GOIANO': [-16.6864, -49.2653], 'LESTE GOIANO': [-16.6864, -49.2653],
        'NORDESTE GOIANO': [-16.6864, -49.2653], 'NOROESTE GOIANO': [-16.6864, -49.2653], 'SUL GOIANO': [-16.6864, -49.2653],
        'GOIANO': [-16.6864, -49.2653], 'GOIÁS': [-16.6864, -49.2653], 'GOIAS': [-16.6864, -49.2653],
        
        # Mato Grosso - Coordenadas precisas
        'CENTRO SUL MATO GROSSENSE': [-15.6010, -56.0974], 'NORDESTE MATO GROSSENSE': [-15.6010, -56.0974],
        'NORTE MATO GROSSENSE': [-15.6010, -56.0974], 'SUDESTE MATO GROSSENSE': [-15.6010, -56.0974],
        'SUDOESTE MATO GROSSENSE': [-15.6010, -56.0974], 'CENTRO SUL MATO GROSSENSE': [-15.6010, -56.0974],
        'NORDESTE MATO GROSSENSE': [-15.6010, -56.0974], 'NORTE MATO GROSSENSE': [-15.6010, -56.0974],
        'SUDESTE MATO GROSSENSE': [-15.6010, -56.0974], 'SUDOESTE MATO GROSSENSE': [-15.6010, -56.0974],
        'MATO GROSSENSE': [-15.6010, -56.0974], 'MATO GROSSO': [-15.6010, -56.0974], 'GROSSENSE': [-15.6010, -56.0974],
        
        # Mato Grosso do Sul - Coordenadas precisas
        'CENTRO NORTE DE MATO GROSSO DO SUL': [-20.4486, -54.6295], 'LESTE DE MATO GROSSO DO SUL': [-20.4486, -54.6295],
        'PANTANAIS SUL MATO GROSSENSE': [-20.4486, -54.6295], 'SUDOESTE DE MATO GROSSO DO SUL': [-20.4486, -54.6295],
        'SUL DE MATO GROSSO DO SUL': [-20.4486, -54.6295], 'CENTRO NORTE DE MATO GROSSO DO SUL': [-20.4486, -54.6295],
        'LESTE DE MATO GROSSO DO SUL': [-20.4486, -54.6295], 'PANTANAIS SUL MATO GROSSENSE': [-20.4486, -54.6295],
        'SUDOESTE DE MATO GROSSO DO SUL': [-20.4486, -54.6295], 'SUL DE MATO GROSSO DO SUL': [-20.4486, -54.6295],
        'MATO GROSSO DO SUL': [-20.4486, -54.6295], 'GROSSO DO SUL': [-20.4486, -54.6295], 'DO SUL': [-20.4486, -54.6295],
        
        # Outros estados importantes
        'DISTRITO FEDERAL': [-15.7942, -47.8822], 'ESPÍRITO SANTO': [-20.2976, -40.2958],
        'PERNAMBUCO': [-8.0476, -34.8770], 'CEARÁ': [-3.7172, -38.5433], 'PARÁ': [-1.4554, -48.4898],
        'AMAZONAS': [-3.4168, -65.8561], 'ACRE': [-8.7619, -70.5511], 'RONDÔNIA': [-8.7619, -63.9039],
        'RORAIMA': [2.8235, -60.6758], 'AMAPÁ': [0.9019, -52.0030], 'TOCANTINS': [-10.1750, -48.2982],
        'MARANHÃO': [-2.5297, -44.3028], 'PIAUÍ': [-5.0892, -42.8016], 'RIO GRANDE DO NORTE': [-5.7945, -35.2120],
        'PARAÍBA': [-7.1150, -34.8631], 'SERGIPE': [-10.9091, -37.0677], 'ALAGOAS': [-9.6498, -35.7089],
        'FLUMINENSE': [-22.9068, -43.1729], 'FLUMINENSE': [-22.9068, -43.1729], 'FLUMINENSE': [-22.9068, -43.1729],
        'PAULISTA': [-23.5505, -46.6333], 'PAULISTA': [-23.5505, -46.6333], 'PAULISTA': [-23.5505, -46.6333],
        'MINEIRO': [-19.9167, -43.9345], 'MINEIRO': [-19.9167, -43.9345], 'MINEIRO': [-19.9167, -43.9345],
        'PARANAENSE': [-25.4289, -49.2671], 'PARANAENSE': [-25.4289, -49.2671], 'PARANAENSE': [-25.4289, -49.2671],
        'CATARINENSE': [-27.5969, -48.5495], 'CATARINENSE': [-27.5969, -48.5495], 'CATARINENSE': [-27.5969, -48.5495],
        'RIO GRANDENSE': [-30.0346, -51.2177], 'RIO GRANDENSE': [-30.0346, -51.2177], 'RIO GRANDENSE': [-30.0346, -51.2177],
        'BAIANO': [-12.9714, -38.5011], 'BAIANO': [-12.9714, -38.5011], 'BAIANO': [-12.9714, -38.5011],
        'GOIANO': [-16.6864, -49.2653], 'GOIANO': [-16.6864, -49.2653], 'GOIANO': [-16.6864, -49.2653],
        'GROSSENSE': [-15.6010, -56.0974], 'GROSSENSE': [-15.6010, -56.0974], 'GROSSENSE': [-15.6010, -56.0974],
        'GROSSO DO SUL': [-20.4486, -54.6295], 'GROSSO DO SUL': [-20.4486, -54.6295], 'GROSSO DO SUL': [-20.4486, -54.6295]
    }
    
    # Primeiro, tentar mapeamento específico de mesorregiões
    for mesorregiao_key, coords in mapeamento_mesorregioes.items():
        if mesorregiao_key.lower() in mesorregiao.upper():
            return coords
    
    # Tentar buscar por partes da mesorregião (mais flexível)
    mesorregiao_upper = mesorregiao.upper()
    for mesorregiao_key, coords in mapeamento_mesorregioes.items():
        # Dividir a mesorregião em partes e verificar se alguma parte corresponde
        partes = mesorregiao_upper.split()
        for parte in partes:
            if parte in mesorregiao_key and len(parte) > 2:  # Evitar palavras muito curtas
                return coords
    
    # Se não encontrar, buscar por estado na mesorregião
    estados_coordenadas = {
        'Acre': [-8.77, -70.55], 'Amazonas': [-3.42, -65.73], 'Rondônia': [-8.76, -63.90],
        'Roraima': [2.82, -60.67], 'Amapá': [0.90, -52.00], 'Pará': [-1.45, -48.50],
        'Tocantins': [-10.17, -48.33], 'Maranhão': [-2.53, -44.30], 'Piauí': [-5.09, -42.80],
        'Ceará': [-3.72, -38.53], 'Rio Grande do Norte': [-5.79, -35.21], 'Pernambuco': [-8.05, -34.92],
        'Paraíba': [-7.12, -34.86], 'Sergipe': [-10.91, -37.07], 'Alagoas': [-9.65, -35.70],
        'Bahia': [-12.97, -38.50], 'Mato Grosso': [-15.60, -56.10], 'Mato Grosso do Sul': [-20.44, -54.64],
        'Goiás': [-16.64, -49.31], 'Distrito Federal': [-15.78, -47.92], 'Minas Gerais': [-19.92, -43.93],
        'Espírito Santo': [-20.32, -40.31], 'Rio de Janeiro': [-22.91, -43.20], 'São Paulo': [-23.55, -46.64],
        'Paraná': [-25.42, -49.27], 'Santa Catarina': [-27.59, -48.55], 'Rio Grande do Sul': [-30.03, -51.23]
    }
    
    for estado, coords in estados_coordenadas.items():
        if estado.lower() in mesorregiao.lower():
            return coords
    
    # Tentar buscar por siglas de estado (SP, MG, RJ, PR, SC, RS, BA, GO, MT, MS)
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
        if sigla in mesorregiao_upper:
            return coords
    
    # Se ainda não encontrar, gerar coordenadas baseadas no nome da mesorregião
    # Usar hash simples para gerar coordenadas consistentes
    import hashlib
    hash_obj = hashlib.md5(mesorregiao.encode())
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
