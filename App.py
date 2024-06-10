import streamlit as st
import pandas as pd
import yfinance as yf
import sqlite3
from datetime import date
from PIL import Image
import json
import time
import requests

# Configurando a largura da página
st.set_page_config(layout="wide")

# Função para obter o cookie do Yahoo Finance
def get_yahoo_cookie():
    cookie_url = "https://fc.yahoo.com"
    response = requests.get(cookie_url)
    cookie = response.cookies.get_dict()
    return cookie

# Função para obter a migalha (crumb) do Yahoo Finance
def get_yahoo_crumb(cookie):
    crumb_url = "https://query2.finance.yahoo.com/v1/test/getcrumb"
    headers = {"cookie": "; ".join([f"{key}={value}" for key, value in cookie.items()])}
    response = requests.get(crumb_url, headers=headers)
    crumb = response.text
    return crumb

def get_yahoo_stock_info(symbol, crumb, cookie):
    fields = "'summaryProfile','summaryDetail','esgScores','price','incomeStatementHistory','incomeStatementHistoryQuarterly','balanceSheetHistory','balanceSheetHistoryQuarterly','cashflowStatementHistory','cashflowStatementHistoryQuarterly','defaultKeyStatistics','financialData','calendarEvents','secFilings','recommendationTrend','upgradeDowngradeHistory','institutionOwnership','fundOwnership','majorDirectHolders','majorHoldersBreakdown','insiderTransactions','insiderHolders','netSharePurchaseActivity','earnings','earningsHistory','earningsTrend','industryTrend','indexTrend','sectorTrend'"
    quote_url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={symbol}&fields={fields}&crumb={crumb}"
    headers = {"cookie": "; ".join([f"{key}={value}" for key, value in cookie.items()])}
    try:
        response = requests.get(quote_url, headers=headers)
        response.raise_for_status()  # Verificar se houve erro na solicitação
        data = response.json()
        return data
    except requests.exceptions.HTTPError as http_err:
        st.warning(f'HTTP error occurred: {http_err}')
    except requests.exceptions.RequestException as req_err:
        st.warning(f'Request error occurred: {req_err}')
    except Exception as err:
        st.warning(f'An error occurred: {err}')


# Função para obter os dados das ações
def pegar_dados_acoes():
    path = 'https://raw.githubusercontent.com/splocs/meu-repositorio/main/acoes.csv'
    return pd.read_csv(path, delimiter=';')

# Função para pegar informações das ações e armazenar no banco de dados
def pegar_info_acoes():
    df = pegar_dados_acoes()
    
    for index, row in df.iterrows():
        symbol = row['sigla_acao']
        symbol_yf = symbol + '.SA'
        cookie = get_yahoo_cookie()
        crumb = get_yahoo_crumb(cookie)
        stock_info = get_yahoo_stock_info(symbol_yf, crumb, cookie)

        try:
            if not stock_info:
                raise ValueError(f"Informações não encontradas para {symbol}")
        except Exception as e:
            st.warning(f"Erro ao buscar informações para {symbol}: {e}")
            continue

        # Tentar conectar e inserir/atualizar no banco de dados com retry
        retry_attempts = 5
        for attempt in range(retry_attempts):
            try:
                with sqlite3.connect('plotos.db', timeout=10) as conn:
                    c = conn.cursor()
                    c.execute('''
                    CREATE TABLE IF NOT EXISTS acoes_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT UNIQUE,
                        info TEXT
                    )
                    ''')

                    # Verificar se a informação já está no banco de dados
                    c.execute('SELECT * FROM acoes_info WHERE symbol = ?', (symbol,))
                    data = c.fetchone()

                    if data is None:
                        c.execute('INSERT INTO acoes_info (symbol, info) VALUES (?, ?)', (symbol, json.dumps(stock_info)))
                    else:
                        c.execute('UPDATE acoes_info SET info = ? WHERE symbol = ?', (json.dumps(stock_info), symbol))
                    
                    conn.commit()
                    break  # Se chegar até aqui, a operação foi bem-sucedida, então saímos do loop de retry
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    st.warning(f"Tentativa {attempt + 1} de {retry_attempts} falhou: {e}")
                    time.sleep(2)  # Esperar um pouco antes de tentar novamente
                else:
                    raise

# Função para testar a conexão com o banco de dados
def testar_conexao():
    try:
        with sqlite3.connect('plotos.db', timeout=10) as conn:
            pass
        return True
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return False

# Função para verificar as informações contidas no banco de dados
def verificar_informacoes():
    try:
        with sqlite3.connect('plotos.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM acoes_info')
            data = c.fetchall()
        return data
    except Exception as e:
        st.error(f"Erro ao acessar o banco de dados: {e}")
        return []

# Função para pegar valores online
def pegar_valores_online(sigla_acao):
    df = yf.download(sigla_acao, DATA_INICIO, DATA_FIM, progress=False)
    df.reset_index(inplace=True)
    return df

# Definindo data de início e fim
DATA_INICIO = '2017-01-01'
DATA_FIM = date.today().strftime('%Y-%m-%d')

# Logo
logo_path = "logo.png"
logo = Image.open(logo_path)

# Exibir o logo no aplicativo Streamlit
st.image(logo, width=250)

# Exibir o logo na sidebar
st.sidebar.image(logo, width=150)

# Criando a sidebar
st.sidebar.markdown('Escolha a ação')

# Pegando os dados das ações
df = pegar_dados_acoes()
acao = df['snome']

nome_acao_escolhida = st.sidebar.selectbox('Escolha uma ação:', acao)
df_acao = df[df['snome'] == nome_acao_escolhida]
sigla_acao_escolhida = df_acao.iloc[0]['sigla_acao']
sigla_acao_escolhida += '.SA'

# Botão para testar a conexão com o banco de dados
if st.sidebar.button('Testar Conexão com o Banco de Dados'):
    if testar_conexao():
        st.sidebar.success('Conexão com o banco de dados bem-sucedida!')
    else:
        st.sidebar.error('Falha na conexão com o banco de dados.')

# Botão para atualizar informações das ações e armazenar no banco de dados
if st.sidebar.button('Atualizar Informações das Ações'):
    pegar_info_acoes()
    st.sidebar.success('Informações atualizadas com sucesso!')

# Botão para verificar as informações contidas no banco de dados
if st.sidebar.button('Verificar Informações do Banco de Dados'):
    data = verificar_informacoes()
    if data:
        st.write(pd.DataFrame(data, columns=['ID', 'Symbol', 'Info']))
    else:
        st.write("Nenhuma informação disponível no banco de dados.")

# Exibir as informações da ação escolhida
try:
    with sqlite3.connect('plotos.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS acoes_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE,
            info TEXT
        )
        ''')
        c.execute('SELECT info FROM acoes_info WHERE symbol = ?', (df_acao.iloc[0]['sigla_acao'],))
        info = c.fetchone()

    if info:
        st.json(json.loads(info[0]))
    else:
        st.write("Nenhuma informação disponível para esta ação.")
except Exception as e:
    st.error(f"Erro ao acessar o banco de dados: {e}")













