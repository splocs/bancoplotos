import streamlit as st
import pandas as pd
import yfinance as yf
import sqlite3
from datetime import date
from PIL import Image
import json

# Configurando a largura da página
st.set_page_config(layout="wide")

# Função para pegar os dados das ações
def pegar_dados_acoes():
    path = 'https://raw.githubusercontent.com/splocs/meu-repositorio/main/acoes.csv'
    return pd.read_csv(path, delimiter=';')

# Função para pegar informações das ações e armazenar no banco de dados
def pegar_info_acoes():
    df = pegar_dados_acoes()
    conn = sqlite3.connect('plotos.db')
    c = conn.cursor()

    # Criar tabela se não existir
    c.execute('''
    CREATE TABLE IF NOT EXISTS acoes_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT UNIQUE,
        info TEXT
    )
    ''')

    for index, row in df.iterrows():
        symbol = row['sigla_acao']
        symbol_yf = symbol + '.SA'
        acao = yf.Ticker(symbol_yf)

        try:
            info = acao.info
            if not info:
                raise ValueError(f"Informações não encontradas para {symbol}")
        except Exception as e:
            st.warning(f"Erro ao buscar informações para {symbol}: {e}")
            continue

        # Verificar se a informação já está no banco de dados
        c.execute('SELECT * FROM acoes_info WHERE symbol = ?', (symbol,))
        data = c.fetchone()

        if data is None:
            c.execute('INSERT INTO acoes_info (symbol, info) VALUES (?, ?)', (symbol, json.dumps(info)))
        else:
            c.execute('UPDATE acoes_info SET info = ? WHERE symbol = ?', (json.dumps(info), symbol))

    conn.commit()
    conn.close()

# Função para testar a conexão com o banco de dados
def testar_conexao():
    try:
        conn = sqlite3.connect('plotos.db')
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return False

# Função para verificar as informações contidas no banco de dados
def verificar_informacoes():
    try:
        conn = sqlite3.connect('plotos.db')
        c = conn.cursor()
        c.execute('SELECT * FROM acoes_info')
        data = c.fetchall()
        conn.close()
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
conn = sqlite3.connect('plotos.db')
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

conn.close()










