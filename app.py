import streamlit as st
import os
import sqlite3
import pandas as pd
import streamlit_authenticator as stauth
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.agents import AgentExecutor, create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.tools import Tool
import bcrypt
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="taxbaseAI - Plataforma de BI com IA", layout="wide")
DB_PATH = "plataforma_financeira.db"

# --- CSS EMBUTIDO ---
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
/* Aplica a nova fonte como padrão */
body, .stApp {
    font-family: 'Poppins', sans-serif;
}
/* Garante a cor correta do texto, respeitando os ícones */
html, body, [class*="st-"], [class*="css-"] {
    color: #FAFAFA !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Poppins', sans-serif; /* Garante que títulos usem Poppins */
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

# --- Funções e Conexão com DB ---
def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

if not os.path.exists(DB_PATH):
    st.error("Base de dados não encontrada. Por favor, execute o script 'migracao_db.py' primeiro.")
    st.stop()

def categorizar_conta(descricao):
    if not isinstance(descricao, str): return 'Outros'
    desc = descricao.upper()
    if 'CUSTO' in desc: return 'Custo'
    elif 'RECEITA' in desc: return 'Receita'
    elif 'DESPESA' in desc or 'IMPOSTOS' in desc or 'TAXAS' in desc or '(-) ' in descricao: return 'Despesa'
    elif 'LUCRO' in desc or 'RESULTADO' in desc or 'PREJUÍZO' in desc: return 'Resultado'
    else: return 'Outros'

# --- ⭐️ FERRAMENTAS ESPECIALISTAS DA IA ⭐️ ---
def analisar_lucratividade_completa(empresa_id: int) -> str:
    """Ferramenta especialista para realizar uma análise de lucratividade completa, calculando as margens Bruta, Operacional e Líquida."""
    conn = get_db_connection()
    try:
        query = f"""
        SELECT
            (SELECT valor FROM dre WHERE descrição = 'RECEITA LÍQUIDA' AND empresa_id = {empresa_id}) as rl,
            (SELECT valor FROM dre WHERE descrição = 'LUCRO BRUTO' AND empresa_id = {empresa_id}) as lb,
            (SELECT valor FROM dre WHERE descrição LIKE '%RESULTADO OPERACIONAL%' AND empresa_id = {empresa_id}) as ro,
            (SELECT valor FROM dre WHERE (descrição LIKE '%LUCRO LÍQUIDO%' OR descrição LIKE '%PREJUÍZO%') AND empresa_id = {empresa_id}) as rf
        """
        df = pd.read_sql_query(query, conn)

        if df.empty or df.isnull().values.any():
            return "Não foi possível realizar a análise de lucratividade, pois um dos componentes chave (Receita, Lucro Bruto, etc.) não foi encontrado."

        rl, lb, ro, rf = df.iloc[0]
        mb = (lb / rl * 100) if rl != 0 else 0
        mo = (ro / rl * 100) if rl != 0 else 0
        ml = (rf / rl * 100) if rl != 0 else 0

        return f"""
        ### Análise Completa de Lucratividade
        - **Receita Líquida:** `R$ {rl:,.2f}`
        - **Margem Bruta:** `{mb:.2f}%` (calculada a partir de um Lucro Bruto de R$ {lb:,.2f})
        - **Margem Operacional:** `{mo:.2f}%` (calculada a partir de um Resultado Operacional de R$ {ro:,.2f})
        - **Margem Líquida:** `{ml:.2f}%` (calculada a partir de um Resultado Final de R$ {rf:,.2f})
        """
    except Exception as e:
        return f"Ocorreu um erro ao analisar a lucratividade: {e}"
    finally:
        conn.close()

def calcular_ebitda(empresa_id: int) -> str:
    """Ferramenta especialista para calcular o EBITDA e explicar a fórmula."""
    conn = get_db_connection()
    try:
        query = f"""
        SELECT
            (SELECT valor FROM dre WHERE descrição LIKE '%LUCRO BRUTO%' AND empresa_id = {empresa_id}) as lucro_bruto,
            (SELECT valor FROM dre WHERE descrição LIKE '%DESPESAS OPERACIONAIS%' AND empresa_id = {empresa_id}) as despesas_op,
            (SELECT valor FROM dre WHERE descrição LIKE '%DEPRECIAÇÕES, AMORTIZAÇÕES%' AND empresa_id = {empresa_id}) as depr_amort
        """
        df = pd.read_sql_query(query, conn)

        if df.empty or df.isnull().values.any():
            return "Não foi possível calcular o EBITDA, pois um dos componentes (Lucro Bruto, Despesas Operacionais ou Depreciação) não foi encontrado."

        lucro_bruto, despesas_op, depr_amort = df.iloc[0]
        lucro_operacional = lucro_bruto + despesas_op
        ebitda = lucro_operacional - depr_amort

        return f"""
        ### Análise de EBITDA
        - **EBITDA:** **R$ {ebitda:,.2f}**
        - **Fórmula:** `Lucro Operacional + Depreciação e Amortização`
        """
    except Exception as e:
        return f"Ocorreu um erro ao calcular o EBITDA: {e}"
    finally:
        conn.close()

# --- FUNÇÃO DO DASHBOARD (permanece a mesma) ---
def display_dashboard(empresa_id):
    pass # Cole a sua função de dashboard completa aqui

# --- AUTENTICAÇÃO ---
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('SELECT nome, email, senha, role FROM usuarios')
db_users = cursor.fetchall()
conn.close()
config = {'credentials': {'usernames': {}}}
for row in db_users:
    nome, email, senha, role = row
    config['credentials']['usernames'][email] = {'name': nome, 'password': senha, 'role': role}
authenticator = stauth.Authenticate(config['credentials'], 'TaxbaseAppCookie', 'TaxbaseAppKey_s#cr&t', 30)

# --- LÓGICA DE RENDERIZAÇÃO ---
if not st.session_state.get("authentication_status"):
    # --- TELA DE LOGIN ---
    col1, col2, col3 = st.columns([1.5, 2, 1.5]) 
    with col2: 
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>A sua Plataforma de Análise Financeira</h2>", unsafe_allow_html=True)
        fields_login = {'Form name': ' ', 'Username': 'O seu Email', 'Password': 'A sua Senha'}
        authenticator.login(fields=fields_login)
    
    if st.session_state.get("authentication_status") is False:
        st.error('Email ou senha incorretos.')
    elif st.session_state.get("authentication_status") is None:
        st.info('Por favor, insira as suas credenciais para aceder.')
else:
    # --- INTERFACE PRINCIPAL APÓS O LOGIN ---
    st.session_state['role'] = config['credentials']['usernames'][st.session_state['username']]['role']
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
            st.warning("Não tem permissão para aceder a nenhuma empresa.")
            st.stop()

        empresas_dict = {nome: id for id, nome in user_empresas}
        empresa_selecionada_nome = st.sidebar.selectbox("Selecione uma empresa:", options=empresas_dict.keys())
        empresa_selecionada_id = empresas_dict[empresa_selecionada_nome]
        
        st.header(f"A analisar: {empresa_selecionada_nome}")
        # display_dashboard(empresa_selecionada_id)
        st.divider()
        st.header("Converse com a IA")
        
        # --- ARQUITETURA FINAL HÍBRIDA E ROBUSTA ---
        llm = ChatOpenAI(temperature=0, model="gpt-4o", api_key=st.secrets["OPENAI_API_KEY"])
        db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        custom_tools = [
            Tool.from_function(
                func=lambda _: analisar_lucratividade_completa(empresa_selecionada_id),
                name="ferramenta_analise_lucratividade",
                description="Use para QUALQUER pergunta sobre análise de lucratividade, margem bruta, margem operacional ou margem líquida."
            ),
            Tool.from_function(
                func=lambda _: calcular_ebitda(empresa_selecionada_id),
                name="ferramenta_calcular_ebitda",
                description="Use para QUALQUER pergunta sobre EBITDA. Ela calcula o valor e explica a fórmula."
            )
        ]
        
        agent_prompt_prefix = f"""
        Você é um assistente de IA para análise financeira. Responda em português do Brasil.
        O ID da empresa atual é {empresa_selecionada_id}.

        **REGRAS DE RACIOCÍNIO:**
        - **PRIORIDADE MÁXIMA:** Sempre verifique se uma das ferramentas especializadas pode responder à pergunta do utilizador antes de tentar consultar a base de dados.
        - **SEGUNDA OPÇÃO:** Se nenhuma ferramenta especializada se encaixar, use as suas outras ferramentas para consultar a base de dados e encontrar a resposta.
        - **SEGURANÇA:** Lembre-se que só pode aceder a dados da empresa com ID {empresa_selecionada_id}.
        - **FORMATAÇÃO SQL:** Quando precisar de escrever uma consulta SQL, a sua resposta DEVE conter APENAS o código SQL, sem nenhuma formatação ou marcadores como ```sql.
        """
        
        agent_executor = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            extra_tools=custom_tools,
            verbose=True,
            prefix=agent_prompt_prefix,
            handle_parsing_errors=True
        )

        if "messages" not in st.session_state: st.session_state.messages = []
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if prompt := st.chat_input(f"Pergunte algo sobre {empresa_selecionada_nome}..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    with st.spinner("A analisar..."):
                        response = agent_executor.invoke({"input": prompt})
                        st.markdown(response["output"])
                        st.session_state.messages.append({"role": "assistant", "content": response["output"]})
                except Exception as e:
                    error_message = "Desculpe, encontrei um erro ao processar a sua solicitação. Pode ser um problema com os dados ou uma consulta muito complexa. Por favor, tente uma pergunta mais simples."
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
    
    elif app_mode == "Painel Admin":
        st.header("🔑 Painel de Administração")
        st.subheader("Cadastrar Nova Empresa")
        with st.form("form_nova_empresa", clear_on_submit=True):
            nome_nova_empresa = st.text_input("Nome da Nova Empresa")
            arquivo_dre = st.file_uploader("Arquivo DRE (CSV)", type=['csv'])
            arquivo_balanco = st.file_uploader("Arquivo Balanço (CSV)", type=['csv'])
            submitted_empresa = st.form_submit_button("Cadastrar Empresa e Dados")
            if submitted_empresa:
                if nome_nova_empresa and arquivo_dre and arquivo_balanco:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO empresas (nome) VALUES (?)", (nome_nova_empresa,))
                        id_nova_empresa = cursor.lastrowid
                        conn.commit()
                        dre_df = pd.read_csv(arquivo_dre)
                        dre_df['empresa_id'] = id_nova_empresa
                        dre_df['categoria'] = dre_df['descrição'].apply(categorizar_conta)
                        dre_df.to_sql('dre', conn, if_exists='append', index=False)
                        balanco_df = pd.read_csv(arquivo_balanco)
                        balanco_df['empresa_id'] = id_nova_empresa
                        balanco_df.to_sql('balanco', conn, if_exists='append', index=False)
                        conn.close()
                        st.success(f"Empresa '{nome_nova_empresa}' e seus dados foram cadastrados com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: Uma empresa com o nome '{nome_nova_empresa}' já existe.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro inesperado: {e}")
                else:
                    st.warning("Por favor, preencha todos os campos e anexe os dois arquivos.")
        
        st.divider()
        
        st.subheader("Cadastrar Novo Usuário")
        with st.form("form_novo_usuario", clear_on_submit=True):
            novo_nome = st.text_input("Nome do Usuário")
            novo_email = st.text_input("Email")
            nova_senha = st.text_input("Senha Temporária", type="password")
            novo_cargo = st.selectbox("Cargo (Role)", options=['user', 'admin'])
            submitted = st.form_submit_button("Cadastrar Usuário")
            if submitted:
                if novo_nome and novo_email and nova_senha and novo_cargo:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        password_bytes = nova_senha.encode('utf-8')
                        salt = bcrypt.gensalt()
                        hashed_password_bytes = bcrypt.hashpw(password_bytes, salt)
                        hashed_password_str = hashed_password_bytes.decode('utf-8')
                        cursor.execute("INSERT INTO usuarios (nome, email, senha, role) VALUES (?, ?, ?, ?)",
                                       (novo_nome, novo_email, hashed_password_str, novo_cargo))
                        conn.commit()
                        conn.close()
                        st.success(f"Usuário '{novo_nome}' ({novo_cargo}) cadastrado com sucesso!")
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

            # ⭐️ ALTERAÇÃO: Corrigindo o nome da variável ⭐️
            usuario_selecionado_id = st.selectbox("Selecione o Usuário:", options=lista_usuarios['id'], format_func=lambda x: lista_usuarios.loc[lista_usuarios['id'] == x, 'email'].iloc[0])
            empresa_selecionada_id_perm = st.selectbox("Selecione a Empresa:", options=lista_empresas['id'], format_func=lambda x: lista_empresas.loc[lista_empresas['id'] == x, 'nome'].iloc[0])
            
            submitted_perm = st.form_submit_button("Conceder Permissão")
            if submitted_perm:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    # ⭐️ ALTERAÇÃO: Usando o nome da variável correta ⭐️
                    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (usuario_selecionado_id, empresa_selecionada_id_perm))
                    conn.commit()
                    conn.close()
                    st.success(f"Permissão concedida com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao conceder permissão: {e}")
        
        st.divider()
        
        st.subheader("Apagar Usuário")
        st.warning("Atenção: Esta ação é permanente e não pode ser desfeita.")
        with st.form("form_apagar_usuario", clear_on_submit=True):
            conn = get_db_connection()
            lista_usuarios_deletar = pd.read_sql('SELECT id, email FROM usuarios WHERE email != ?', conn, params=(st.session_state['username'],))
            conn.close()
            if not lista_usuarios_deletar.empty:
                usuario_a_deletar_id = st.selectbox("Selecione o Usuário a ser Apagado:", 
                                                    options=lista_usuarios_deletar['id'], 
                                                    format_func=lambda x: lista_usuarios_deletar.loc[lista_usuarios_deletar['id'] == x, 'email'].iloc[0])
                confirmacao = st.checkbox(f"Eu confirmo que desejo apagar permanentemente o usuário selecionado.")
                submitted_delete = st.form_submit_button("Apagar Usuário")
                if submitted_delete:
                    if confirmacao:
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_a_deletar_id,))
                            cursor.execute("DELETE FROM permissoes WHERE id_usuario = ?", (usuario_a_deletar_id,))
                            conn.commit()
                            conn.close()
                            st.success("Usuário apagado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ocorreu um erro ao apagar o usuário: {e}")
                    else:
                        st.warning("Você precisa marcar a caixa de confirmação para apagar um usuário.")
            else:
                st.info("Não há outros usuários para apagar.")