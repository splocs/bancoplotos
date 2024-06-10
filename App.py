# Importações necessárias
import streamlit as st
import pandas as pd
import sqlite3
import json
import requests
import time

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

# Função para obter as informações de uma ação do Yahoo Finance
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

# Função para armazenar as informações de uma ação no banco de dados SQLite
def store_stock_info(symbol, info):
    try:
        with sqlite3.connect('plotos.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('''
            CREATE TABLE IF NOT EXISTS acoes_info (
                symbol TEXT PRIMARY KEY,
                info TEXT
            )
            ''')

            # Verificar se a informação já está no banco de dados
            c.execute('SELECT * FROM acoes_info WHERE symbol = ?', (symbol,))
            data = c.fetchone()

            if data is None:
                c.execute('INSERT INTO acoes_info (symbol, info) VALUES (?, ?)', (symbol, json.dumps(info)))
            else:
                c.execute('UPDATE acoes_info SET info = ? WHERE symbol = ?', (json.dumps(info), symbol))
            
            conn.commit()
    except sqlite3.OperationalError as e:
        st.warning(f'SQLite operational error occurred: {e}')
    except Exception as err:
        st.warning(f'An error occurred while storing data: {err}')

# Função para verificar se as informações de uma ação já estão armazenadas no banco de dados
def is_stock_info_stored(symbol):
    try:
        with sqlite3.connect('plotos.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM acoes_info WHERE symbol = ?', (symbol,))
            data = c.fetchone()
        return data is not None
    except sqlite3.OperationalError as e:
        st.warning(f'SQLite operational error occurred: {e}')
        return False
    except Exception as err:
        st.warning(f'An error occurred: {err}')
        return False

# Função para buscar informações de uma ação
def fetch_stock_info(symbol):
    cookie = get_yahoo_cookie()
    crumb = get_yahoo_crumb(cookie)
    stock_info = get_yahoo_stock_info(symbol, crumb, cookie)
    return stock_info

# Função principal para atualizar as informações das ações
def update_stock_info():
    df = pegar_dados_acoes()
    
    for index, row in df.iterrows():
        symbol = row['sigla_acao']
        if not is_stock_info_stored(symbol):
            stock_info = fetch_stock_info(symbol)
            if stock_info:
                store_stock_info(symbol, stock_info)
            else:
                st.warning(f"No information found for {symbol}")
        else:
            st.warning(f"Information for {symbol} is already stored")

# Função para pegar os dados das ações
def pegar_dados_acoes():
    path = 'https://raw.githubusercontent.com/splocs/meu-repositorio/main/acoes.csv'
    return pd.read_csv(path, delimiter=';')

# Função para exibir as informações de uma ação
def show_stock_info(symbol):
    try:
        with sqlite3.connect('plotos.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('SELECT info FROM acoes_info WHERE symbol = ?', (symbol,))
            info = c.fetchone()

        if info:
            st.json(json.loads(info[0]))
        else:
            st.warning("No information available for this stock.")
    except sqlite3.OperationalError as e:
        st.warning(f'SQLite operational error occurred: {e}')
    except Exception as err:
        st.warning(f'An error occurred: {err}')

# Definição de layout e funcionalidades do aplicativo Streamlit
st.set_page_config(layout="wide")

# Barra lateral para interação
st.sidebar.title("Opções de Ações")

# Botão para atualizar as informações das ações
if st.sidebar.button('Atualizar Informações das Ações'):
    update_stock_info()
    st.sidebar.success('Informações atualizadas com sucesso!')

# Dropdown para selecionar uma ação
selected_stock = st.sidebar.selectbox('Selecione uma ação:', pegar_dados_acoes()['sigla_acao'])

# Exibir informações da ação selecionada
st.title(f"Informações da Ação: {selected_stock}")
show_stock_info(selected_stock)













