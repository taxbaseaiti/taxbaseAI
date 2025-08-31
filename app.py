import streamlit as st
import os
import sqlite3
import pandas as pd
import streamlit_authenticator as stauth
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent

# --- Configuração da Página ---
st.set_page_config(page_title="Plataforma de BI com IA", layout="wide")

# --- Conexão com o Banco de Dados ---
DB_PATH = "plataforma_financeira.db"
if not os.path.exists(DB_PATH):
    st.error("Banco de dados não encontrado. Execute o script de migração primeiro.")
    st.stop()
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# --- AUTENTICAÇÃO ---
# Puxa os dados dos usuários do banco de dados
cursor.execute('SELECT nome, email, senha FROM usuarios')
db_users = cursor.fetchall()
credentials = {'usernames': {}}
for row in db_users:
    nome, email, senha = row
    credentials['usernames'][email] = {'name': nome, 'password': senha}

authenticator = stauth.Authenticate(credentials, 'bi_cookie', 'bi_key', cookie_expiry_days=30)

# --- TELA DE LOGIN E CADASTRO ---
st.title("Plataforma de Análise Financeira com IA")

# Cria abas para Login e Cadastro
login_tab, register_tab = st.tabs(["Login", "Cadastre-se"])

with login_tab:
    # ALTERAÇÃO AQUI: A função login() apenas renderiza o formulário.
    # A verificação do status é feita depois, via st.session_state.
    authenticator.login()

with register_tab:
    try:
        if authenticator.register_user(pre_authorization=False):
            st.success('Usuário cadastrado com sucesso! Por favor, faça o login na aba "Login".')
            # Atualiza as credenciais após o cadastro
            cursor.execute('SELECT nome, email, senha FROM usuarios')
            db_users_updated = cursor.fetchall()
            credentials['usernames'] = {email: {'name': nome, 'password': senha} for nome, email, senha in db_users_updated}
            authenticator.credentials = credentials
    except Exception as e:
        st.error(e)

# --- LÓGICA PRINCIPAL DA APLICAÇÃO (SÓ EXECUTA APÓS LOGIN) ---
if st.session_state.get("authentication_status"):
    st.sidebar.title(f"Bem-vindo, {st.session_state['name']}!")
    authenticator.logout('Logout', 'sidebar')

    # --- SELEÇÃO DE EMPRESA ---
    cursor.execute('''
        SELECT e.id, e.nome FROM empresas e
        JOIN permissoes p ON e.id = p.id_empresa
        JOIN usuarios u ON p.id_usuario = u.id
        WHERE u.email = ?
    ''', (st.session_state['username'],))
    user_empresas = cursor.fetchall()
    
    if not user_empresas:
        st.warning("Você não tem permissão para acessar nenhuma empresa. Contate o administrador.")
        st.stop()
    
    empresas_dict = {nome: id for id, nome in user_empresas}
    empresa_selecionada_nome = st.sidebar.selectbox("Selecione uma empresa:", options=empresas_dict.keys())
    empresa_selecionada_id = empresas_dict[empresa_selecionada_nome]

    if "current_company_id" not in st.session_state or st.session_state.current_company_id != empresa_selecionada_id:
        st.session_state.messages = []
        st.session_state.current_company_id = empresa_selecionada_id

    # --- INICIALIZAÇÃO DA IA ---
    st.header(f"Analisando: {empresa_selecionada_nome}")
    db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
    llm = ChatOpenAI(temperature=0, model="gpt-4o", api_key=st.secrets["OPENAI_API_KEY"])

    CUSTOM_PROMPT_PREFIX = f"""
    You are a senior financial analyst AI. 
    *** CRITICAL SECURITY RULE ***
    ALL SQL queries you generate MUST include a WHERE clause to filter by the company ID.
    The company ID for all queries is: {empresa_selecionada_id}
    NEVER query data without this WHERE clause.
    """
    
    agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True, prefix=CUSTOM_PROMPT_PREFIX)

    # --- Funcionalidade de Chat ---
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if prompt := st.chat_input(f"Pergunte algo sobre {empresa_selecionada_nome}..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                response = agent_executor.invoke({"input": prompt})
                st.markdown(response["output"])
        st.session_state.messages.append({"role": "assistant", "content": response["output"]})

elif st.session_state.get("authentication_status") is False:
    with login_tab:
        st.error('Email ou senha incorretos.')
elif st.session_state.get("authentication_status") is None:
    with login_tab:
        st.info('Por favor, faça o login para continuar.')

conn.close()