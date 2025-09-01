import streamlit as st
import os
import sqlite3
import pandas as pd
import streamlit_authenticator as stauth
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent

# --- Configuração da Página ---
st.set_page_config(page_title="taxbaseAI - Plataforma de BI com IA", layout="wide")
DB_PATH = "plataforma_financeira.db"

# --- CSS MÍNIMO (APENAS ESTÉTICA, SEM LAYOUT) ---
page_bg_css = """
<style>
/* Importa a fonte Poppins */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
/* Fundo Principal Escuro */
[data-testid="stAppViewContainer"] {
    background-color: #010714;
}
/* Deixa o Header e Toolbar transparentes */
[data-testid="stHeader"], [data-testid="stToolbar"] {
    background: none;
}
/* Aplica a nova fonte e cor a toda a aplicação */
html, body, [class*="st-"], [class*="css-"] {
    font-family: 'Poppins', sans-serif;
    color: #FAFAFA !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Poppins', sans-serif;
    color: #FAFAFA !important;
}
/* Estilos da Sidebar e do Chat */
[data-testid="stSidebar"] { background-color: #0E1117; }
[data-testid="stChatMessage"] {
    background-color: #1E293B;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
    border: 1px solid #334155;
}
/* Estilo para o formulário de login */
div[data-testid="stForm"] {
    border: 1px solid #334155;
    background-color: #0E1117;
    border-radius: 15px;
    padding: 2rem;
}
div[data-testid="stForm"] h1 { display: none; }
</style>
"""
st.markdown(page_bg_css, unsafe_allow_html=True)

# (O restante do seu código Python permanece o mesmo)
# --- Funções e Conexão com DB ---
def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)
if not os.path.exists(DB_PATH):
    st.error("Banco de dados não encontrado...")
    st.stop()

# --- AUTENTICAÇÃO ---
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('SELECT nome, email, senha, role FROM usuarios')
db_users = cursor.fetchall()
conn.close()
credentials = {'usernames': {}}
for row in db_users:
    nome, email, senha, role = row
    credentials['usernames'][email] = {'name': nome, 'password': senha, 'role': role}
authenticator = stauth.Authenticate(credentials, 'bi_cookie_final_v5', 'bi_key_final_v5', 30)

# --- LÓGICA DE RENDERIZAÇÃO ---
if not st.session_state.get("authentication_status"):
    # --- TELA DE LOGIN ---
    col1, col2, col3 = st.columns([1.5, 2, 1.5]) # Colunas laterais como espaçadores

    with col2: # Todo o conteúdo de login vai na coluna central
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            # ALTERAÇÃO: Corrigido o nome do parâmetro
            st.image(logo_path, use_container_width=True) 
        
        st.markdown("<h2 style='text-align: center;'>Sua Plataforma de Análise Financeira</h2>", unsafe_allow_html=True)
        
        fields_login = {'Form name': ' ', 'Username': 'Seu Email', 'Password': 'Sua Senha'}
        authenticator.login(fields=fields_login)
    
    if st.session_state.get("authentication_status") is False:
        st.error('Email ou senha incorretos.')
    elif st.session_state.get("authentication_status") is None:
        st.info('Por favor, insira suas credenciais para acessar.')

else:
    # --- INTERFACE PRINCIPAL APÓS O LOGIN ---
    st.session_state['role'] = credentials['usernames'][st.session_state['username']]['role']
    st.sidebar.image("assets/logo.png", width=150)
    st.sidebar.title(f"Bem-vindo, {st.session_state['name']}!")
    authenticator.logout('Logout', 'sidebar')

    app_mode = st.sidebar.radio("Navegação", ["Análise IA", "Painel Admin"] if st.session_state['role'] == 'admin' else ["Análise IA"])

    if app_mode == "Análise IA":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT e.id, e.nome FROM empresas e JOIN permissoes p ON e.id = p.id_empresa JOIN usuarios u ON p.id_usuario = u.id WHERE u.email = ?', (st.session_state['username'],))
        user_empresas = cursor.fetchall()
        conn.close()
        
        if not user_empresas:
            st.warning("Você não tem permissão para acessar nenhuma empresa.")
            st.stop()

        empresas_dict = {nome: id for id, nome in user_empresas}
        empresa_selecionada_nome = st.sidebar.selectbox("Selecione uma empresa:", options=empresas_dict.keys())
        empresa_selecionada_id = empresas_dict[empresa_selecionada_nome]
        
        st.header(f"Analisando: {empresa_selecionada_nome}")
        
        db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        llm = ChatOpenAI(temperature=0, model="gpt-4o", api_key=st.secrets["OPENAI_API_KEY"])
        CUSTOM_PROMPT_PREFIX = f"The company ID for all queries is: {empresa_selecionada_id}"
        agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True, prefix=CUSTOM_PROMPT_PREFIX)

        if "messages" not in st.session_state: st.session_state.messages = []
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