import streamlit as st
import os
import sqlite3
import pandas as pd # ALTERAÇÃO: Adicionada a importação que faltava
import streamlit_authenticator as stauth
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent

# --- Configuração da Página e Conexão com DB ---
st.set_page_config(page_title="Plataforma de BI com IA", layout="wide")
DB_PATH = "plataforma_financeira.db"

# Função para conectar ao DB
def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

if not os.path.exists(DB_PATH):
    st.error("Banco de dados não encontrado. Execute o script de migração.")
    st.stop()

# --- AUTENTICAÇÃO ---
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('SELECT nome, email, senha, role FROM usuarios') # Puxa também o 'role'
db_users = cursor.fetchall()
conn.close()

credentials = {'usernames': {}}
for row in db_users:
    nome, email, senha, role = row
    credentials['usernames'][email] = {'name': nome, 'password': senha, 'role': role}

authenticator = stauth.Authenticate(credentials, 'bi_cookie_v2', 'bi_key_v2', 30)

st.title("Plataforma de Análise Financeira com IA")
authenticator.login()

# --- LÓGICA PRINCIPAL DA APLICAÇÃO ---
if st.session_state.get("authentication_status"):
    # Adiciona o cargo do usuário à sessão
    st.session_state['role'] = credentials['usernames'][st.session_state['username']]['role']

    st.sidebar.title(f"Bem-vindo, {st.session_state['name']}!")
    authenticator.logout('Logout', 'sidebar')

    # --- NAVEGAÇÃO PRINCIPAL (CONDICIONAL AO CARGO) ---
    app_mode = st.sidebar.radio("Navegação", ["Análise IA", "Painel Admin"] if st.session_state['role'] == 'admin' else ["Análise IA"])

    # --- MODO: ANÁLISE IA (Para todos os usuários) ---
    if app_mode == "Análise IA":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id, e.nome FROM empresas e
            JOIN permissoes p ON e.id = p.id_empresa
            JOIN usuarios u ON p.id_usuario = u.id
            WHERE u.email = ?
        ''', (st.session_state['username'],))
        user_empresas = cursor.fetchall()
        conn.close()
        
        if not user_empresas:
            st.warning("Você não tem permissão para acessar nenhuma empresa.")
            st.stop()

        empresas_dict = {nome: id for id, nome in user_empresas}
        empresa_selecionada_nome = st.sidebar.selectbox("Selecione uma empresa:", options=empresas_dict.keys())
        empresa_selecionada_id = empresas_dict[empresa_selecionada_nome]

        # (O resto do código da IA permanece o mesmo...)
        st.header(f"Analisando: {empresa_selecionada_nome}")
        db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        llm = ChatOpenAI(temperature=0, model="gpt-4o", api_key=st.secrets["OPENAI_API_KEY"])
        CUSTOM_PROMPT_PREFIX = f"""
        You are a senior financial analyst AI...
        The company ID for all queries is: {empresa_selecionada_id}
        ...
        """
        agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True, prefix=CUSTOM_PROMPT_PREFIX)
        # (Interface de chat permanece a mesma...)
        if "messages" not in st.session_state: st.session_state.messages = []
        # ... (código do chat aqui) ...
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

    # --- MODO: PAINEL ADMIN (Apenas para admins) ---
    elif app_mode == "Painel Admin":
        st.header("🔑 Painel de Administração")
        st.subheader("Cadastrar Novo Usuário")

        with st.form("form_novo_usuario", clear_on_submit=True):
            novo_nome = st.text_input("Nome do Usuário")
            novo_email = st.text_input("Email")
            nova_senha = st.text_input("Senha Temporária", type="password")
            submitted = st.form_submit_button("Cadastrar Usuário")
            if submitted:
                if novo_nome and novo_email and nova_senha:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        hashed_password = stauth.Hasher(nova_senha).generate()
                        cursor.execute("INSERT INTO usuarios (nome, email, senha, role) VALUES (?, ?, ?, ?)",
                                       (novo_nome, novo_email, hashed_password[0], 'user'))
                        conn.commit()
                        conn.close()
                        st.success(f"Usuário '{novo_nome}' cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("Erro: Este email já existe.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")
                else:
                    st.warning("Por favor, preencha todos os campos.")

        st.divider()
        st.subheader("Gerenciar Permissões")

        with st.form("form_permissoes", clear_on_submit=True):
            conn = get_db_connection()
            # Pega listas de usuários e empresas do DB
            lista_usuarios = pd.read_sql('SELECT id, email FROM usuarios', conn)
            lista_empresas = pd.read_sql('SELECT id, nome FROM empresas', conn)
            conn.close()

            usuario_selecionado_id = st.selectbox("Selecione o Usuário:", options=lista_usuarios['id'], format_func=lambda x: lista_usuarios.loc[lista_usuarios['id'] == x, 'email'].iloc[0])
            empresa_selecionada_id_perm = st.selectbox("Selecione a Empresa:", options=lista_empresas['id'], format_func=lambda x: lista_empresas.loc[lista_empresas['id'] == x, 'nome'].iloc[0])
            
            submitted_perm = st.form_submit_button("Conceder Permissão")
            if submitted_perm:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (usuario_selecionado_id, empresa_selecionada_id_perm))
                    conn.commit()
                    conn.close()
                    st.success(f"Permissão concedida com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao conceder permissão: {e}")


# --- Lógica de Erro de Login ---
elif st.session_state.get("authentication_status") is False:
    st.error('Email ou senha incorretos.')
elif st.session_state.get("authentication_status") is None:
    st.info('Por favor, faça o login para continuar.')