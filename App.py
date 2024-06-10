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
        id INTEGER PRIMARY KEY,
        symbol TEXT,
        info TEXT
    )
    ''')

    for index, row in df.iterrows():
        symbol = row['sigla_acao']
        symbol_yf = symbol + '.SA'
        acao = yf.Ticker(symbol_yf)
        info = acao.info

        # Verificar se a informação já está no banco de dados
        c.execute('SELECT * FROM acoes_info WHERE symbol = ?', (symbol,))
        data = c.fetchone()

        if data is None:
            c.execute('INSERT INTO acoes_info (symbol, info) VALUES (?, ?)', (symbol, json.dumps(info)))
        else:
            c.execute('UPDATE acoes_info SET info = ? WHERE symbol = ?', (json.dumps(info), symbol))

    conn.commit()
    conn.close()

# Função para formatar a data
def formatar_data(data):
    if data is not None:
        return pd.to_datetime(data, unit='s').strftime('%d-%m-%Y')
    return 'N/A'

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

# Atualizar informações das ações e armazenar no banco de dados
if st.sidebar.button('Atualizar informações das ações'):
    pegar_info_acoes()
    st.sidebar.success('Informações atualizadas com sucesso!')

# Exibir as informações da ação escolhida
conn = sqlite3.connect('plotos.db')
c = conn.cursor()
c.execute('SELECT info FROM acoes_info WHERE symbol = ?', (df_acao.iloc[0]['sigla_acao'],))
info = c.fetchone()

if info:
    st.json(json.loads(info[0]))
else:
    st.write("Nenhuma informação disponível para esta ação.")

conn.close()






