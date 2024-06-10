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

# Função para pegar os dados das ações
def pegar_dados_acoes():
    path = 'https://raw.githubusercontent.com/splocs/meu-repositorio/main/acoes.csv'
    return pd.read_csv(path, delimiter=';')

# Função para obter o cookie do Yahoo
def get_yahoo_cookie():
    cookie = None

    user_agent_key = "User-Agent"
    user_agent_value = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"

    headers = {user_agent_key: user_agent_value}
    response = requests.get(
        "https://fc.yahoo.com", headers=headers, allow_redirects=True
    )

    if not response.cookies:
        raise Exception("Failed to obtain Yahoo auth cookie.")

    cookie = list(response.cookies)[0]

    return cookie

# Função para obter o crumb do Yahoo
def get_yahoo_crumb(cookie):
    crumb = None

    user_agent_key = "User-Agent"
    user_agent_value = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"

    headers = {user_agent_key: user_agent_value}

    crumb_response = requests.get(
        "https://query1.finance.yahoo.com/v1/test/getcrumb",
        headers=headers,
        cookies={cookie.name: cookie.value},
        allow_redirects=True,
    )
    crumb = crumb_response.text

    if crumb is None:
        raise Exception("Failed to retrieve Yahoo crumb.")

    return crumb

# Função para pegar cookies e crumb
def obter_cookies_e_crumb():
    cookie = get_yahoo_cookie()
    crumb = get_yahoo_crumb(cookie)
    return cookie, crumb

# Função para pegar informações das ações e armazenar no banco de dados
def pegar_info_acoes():
    df = pegar_dados_acoes()
    cookie, crumb = obter_cookies_e_crumb()
    
    for index, row in df.iterrows():
        symbol = row['sigla_acao']
        symbol_yf = symbol + '.SA'

        retry_attempts = 5
        success = False
        wait_time = 1  # Tempo inicial de espera em segundos

        for attempt in range(retry_attempts):
            try:
                url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol_yf}?modules=summaryProfile,financialData,quoteType,defaultKeyStatistics,assetProfile,summaryDetail&crumb={crumb}"
                response = requests.get(url, cookies={cookie.name: cookie.value})
                if response.status_code == 429:
                    raise ValueError(f"Erro ao buscar informações para {symbol_yf}: {response.status_code}")
                elif response.status_code != 200:
                    raise ValueError(f"Erro ao buscar informações para {symbol_yf}: {response.status_code}")
                
                data = response.json()
                if 'quoteSummary' not in data or 'result' not in data['quoteSummary']:
                    raise ValueError(f"Informações não encontradas para {symbol}")
                
                info = data['quoteSummary']['result'][0]
                acao = yf.Ticker(symbol_yf)
                recommendations_summary = acao.recommendations_summary
                dividends = acao.dividends
                splits = acao.splits
                balance_sheet = acao.balance_sheet

                success = True
                break
            except ValueError as ve:
                st.warning(f"Erro ao buscar informações para {symbol}: {ve}. Tentando novamente...")
                time.sleep(wait_time)
                wait_time *= 2  # Aumenta o tempo de espera exponencialmente
            except Exception as e:
                st.error(f"Erro ao buscar informações para {symbol}: {e}. Tentando novamente...")
                time.sleep(wait_time)
                wait_time *= 2  # Aumenta o tempo de espera exponencialmente
        
        if not success:
            st.error(f"Erro ao buscar informações para {symbol} após várias tentativas.")
            continue

        # Tentar conectar e inserir/atualizar no banco de dados com retry
        for attempt in range(retry_attempts):
            try:
                with sqlite3.connect('plotos.db', timeout=10) as conn:
                    c = conn.cursor()
                    c.execute('''
                    CREATE TABLE IF NOT EXISTS acoes_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT UNIQUE,
                        info TEXT,
                        recommendations_summary TEXT,
                        dividends TEXT,
                        splits TEXT,
                        balance_sheet TEXT
                    )
                    ''')

                    # Verificar se a informação já está no banco de dados
                    c.execute('SELECT * FROM acoes_info WHERE symbol = ?', (symbol,))
                    data = c.fetchone()

                    if data is None:
                        c.execute('''
                            INSERT INTO acoes_info (
                                symbol, info, recommendations_summary, dividends, splits, balance_sheet
                            ) VALUES (?, ?, ?, ?, ?, ?)''', 
                            (symbol, json.dumps(info), recommendations_summary.to_json(), dividends.to_json(), splits.to_json(), balance_sheet.to_json()))
                    else:
                        c.execute('''
                            UPDATE acoes_info 
                            SET info = ?, recommendations_summary = ?, dividends = ?, splits = ?, balance_sheet = ? 
                            WHERE symbol = ?''', 
                            (json.dumps(info), recommendations_summary.to_json(), dividends.to_json(), splits.to_json(), balance_sheet.to_json(), symbol))
                    
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

# Função para exportar o banco de dados
def exportar_banco():
    with open('plotos.db', 'rb') as f:
        st.download_button(label='Baixar Banco de Dados', data=f, file_name='plotos.db')

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
        st.write(pd.DataFrame(data, columns=['ID', 'Symbol', 'Info', 'Recommendations Summary', 'Dividends', 'Splits', 'Balance Sheet']))
    else:
        st.write("Nenhuma informação disponível no banco de dados.")

# Botão para exportar o banco de dados
exportar_banco()

# Exibir as informações da ação escolhida
try:
    with sqlite3.connect('plotos.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS acoes_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE,
            info TEXT,
            recommendations_summary TEXT,
            dividends TEXT,
            splits TEXT,
            balance_sheet TEXT
        )
        ''')
except sqlite3.OperationalError as e:
    st.error(f"Erro ao criar a tabela no banco de dados: {e}")
















