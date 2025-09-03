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
    st.error("Banco de dados não encontrado. Por favor, execute o script 'migracao_db.py' primeiro.")
    st.stop()

def categorizar_conta(descricao):
    if not isinstance(descricao, str): return 'Outros'
    desc = descricao.upper()
    if 'CUSTO' in desc: return 'Custo'
    elif 'RECEITA' in desc: return 'Receita'
    elif 'DESPESA' in desc or 'IMPOSTOS' in desc or 'TAXAS' in desc or '(-) ' in descricao: return 'Despesa'
    elif 'LUCRO' in desc or 'RESULTADO' in desc or 'PREJUÍZO' in desc: return 'Resultado'
    else: return 'Outros'

# --- Ferramentas Especialistas da IA ---
def calcular_indice_liquidez(empresa_id: int) -> str:
    """Calcula o Índice de Liquidez Corrente e explica a fórmula e a fonte dos dados."""
    conn = get_db_connection()
    try:
        query = f"""
        SELECT
            (SELECT saldo_atual FROM balanco WHERE descrição = 'ATIVO CIRCULANTE' AND empresa_id = {empresa_id}) as ativo_c,
            (SELECT saldo_atual FROM balanco WHERE descrição = 'PASSIVO CIRCULANTE' AND empresa_id = {empresa_id}) as passivo_c
        """
        df = pd.read_sql_query(query, conn)

        if df.empty or df.isnull().values.any():
            return "Não foi possível calcular o Índice de Liquidez, pois 'Ativo Circulante' ou 'Passivo Circulante' não foram encontrados."

        ativo_c = df['ativo_c'].iloc[0]
        passivo_c = df['passivo_c'].iloc[0]
        liquidez = ativo_c / passivo_c if passivo_c != 0 else 0

        return f"""
        ### Análise de Liquidez Corrente
        - **Índice de Liquidez Corrente:** `{liquidez:.2f}`
        ---
        - **Fórmula:** `Ativo Circulante / Passivo Circulante`
        - **Ativo Circulante:** `R$ {ativo_c:,.2f}` *(Fonte: Balanço Patrimonial)*
        - **Passivo Circulante:** `R$ {passivo_c:,.2f}` *(Fonte: Balanço Patrimonial)*

        **Explicação:** Um índice de {liquidez:.2f} significa que a empresa possui R$ {liquidez:.2f} em ativos de curto prazo para cada R$ 1,00 de dívidas de curto prazo.
        """
    except Exception as e:
        return f"Ocorreu um erro ao calcular o Índice de Liquidez: {e}"
    finally:
        conn.close()

def calcular_ebitda(empresa_id: int) -> str:
    """Calcula o EBITDA e explica a fórmula e a fonte dos dados."""
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

        lucro_bruto = df['lucro_bruto'].iloc[0]
        despesas_op = df['despesas_op'].iloc[0]
        depr_amort = df['depr_amort'].iloc[0]
        lucro_operacional = lucro_bruto + despesas_op
        ebitda = lucro_operacional - depr_amort

        return f"""
        ### Análise de EBITDA
        - **EBITDA:** **R$ {ebitda:,.2f}**
        ---
        - **Fórmula:** `Lucro Operacional + Depreciação e Amortização`
        - **Lucro Operacional (EBIT):** `R$ {lucro_operacional:,.2f}` *(Fonte: DRE)*
        - **(+) Depreciação e Amortização:** `R$ {abs(depr_amort):,.2f}` *(Fonte: DRE)*
        """
    except Exception as e:
        return f"Ocorreu um erro ao calcular o EBITDA: {e}"
    finally:
        conn.close()

# --- FUNÇÃO DO DASHBOARD ---
def display_dashboard(empresa_id):
    st.subheader("Dashboard de Visão Geral")
    conn = get_db_connection()
    try:
        query = f"""
        WITH kpis AS (
            SELECT
                (SELECT valor FROM dre WHERE descrição = 'RECEITA LÍQUIDA' AND empresa_id = {empresa_id}) as receita_liquida,
                (SELECT valor FROM dre WHERE (descrição LIKE '%LUCRO LÍQUIDO%' OR descrição LIKE '%PREJUÍZO DO EXERCÍCIO%') AND empresa_id = {empresa_id}) as resultado_final
            )
        SELECT * FROM kpis
        """
        kpi_df = pd.read_sql_query(query, conn)

        if not kpi_df.empty and kpi_df.notna().all().all():
            receita_liquida = kpi_df['receita_liquida'].iloc[0] or 0
            resultado_final = kpi_df['resultado_final'].iloc[0] or 0
            rotulo_resultado = "Lucro Líquido" if resultado_final >= 0 else "Prejuízo do Exercício"
            margem_liquida = (resultado_final / receita_liquida * 100) if receita_liquida != 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Receita Líquida", f"R$ {receita_liquida:,.2f}")
            col2.metric(rotulo_resultado, f"R$ {resultado_final:,.2f}")
            col3.metric("Margem Líquida", f"{margem_liquida:.2f}%")
        else:
            st.warning("Não foi possível calcular os KPIs do dashboard.")

        st.markdown("---")
        st.subheader("Top 5 Maiores Despesas")
        despesas_df = pd.read_sql_query(f"SELECT descrição, valor FROM dre WHERE categoria = 'Despesa' AND empresa_id = {empresa_id} ORDER BY valor ASC LIMIT 5", conn)
        
        if not despesas_df.empty:
            despesas_df['valor_abs'] = despesas_df['valor'].abs()
            fig = px.bar(despesas_df, x='valor_abs', y='descrição', orientation='h', labels={'valor_abs': 'Valor (R$)', 'descrição': ''}, text='valor_abs', color_discrete_sequence=['#007bff'])
            fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#FAFAFA')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não foram encontradas despesas categorizadas para esta empresa.")
    except Exception as e:
        st.error(f"Erro ao gerar o dashboard: {e}")
    finally:
        conn.close()

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
        st.markdown("<h2 style='text-align: center;'>Sua Plataforma de Análise Financeira</h2>", unsafe_allow_html=True)
        fields_login = {'Form name': ' ', 'Username': 'Seu Email', 'Password': 'Sua Senha'}
        authenticator.login(fields=fields_login)
    
    if st.session_state.get("authentication_status") is False:
        st.error('Email ou senha incorretos.')
    elif st.session_state.get("authentication_status") is None:
        st.info('Por favor, insira suas credenciais para acessar.')
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
            st.warning("Você não tem permissão para acessar nenhuma empresa.")
            st.stop()

        empresas_dict = {nome: id for id, nome in user_empresas}
        empresa_selecionada_nome = st.sidebar.selectbox("Selecione uma empresa:", options=empresas_dict.keys())
        empresa_selecionada_id = empresas_dict[empresa_selecionada_nome]
        
        st.header(f"Analisando: {empresa_selecionada_nome}")
        display_dashboard(empresa_selecionada_id)
        st.divider()
        st.header("Converse com a IA")
        
        llm = ChatOpenAI(temperature=0, model="gpt-4o", api_key=st.secrets["OPENAI_API_KEY"])
        db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        custom_tools = [
            Tool.from_function(
                func=lambda _: calcular_ebitda(empresa_selecionada_id),
                name="ferramenta_calcular_ebitda",
                description="Use para QUALQUER pergunta sobre EBITDA. Ela calcula o valor e explica a fórmula."
            ),
            Tool.from_function(
                func=lambda _: calcular_indice_liquidez(empresa_selecionada_id),
                name="ferramenta_calcular_indice_liquidez",
                description="Use para QUALQUER pergunta sobre Índice de Liquidez. Ela calcula o valor e explica a fórmula."
            )
        ]
        
        agent_prompt_prefix = f"""
        Você é um assistente de IA para análise financeira. Responda em português do Brasil.
        O ID da empresa atual é {empresa_selecionada_id}.

        **REGRAS DE RACIOCÍNIO:**
        - **PRIORIDADE MÁXIMA:** Sempre verifique se uma das ferramentas especializadas (`ferramenta_calcular_ebitda`, `ferramenta_calcular_indice_liquidez`) pode responder à pergunta do usuário antes de tentar consultar o banco de dados.
        - **SEGUNDA OPÇÃO:** Se nenhuma ferramenta especializada se encaixar, use suas outras ferramentas para consultar o banco de dados e encontrar a resposta.
        - **SEGURANÇA:** Lembre-se que você só pode acessar dados da empresa com ID {empresa_selecionada_id}.
        - **FORMATAÇÃO SQL:** Quando você precisar escrever uma consulta SQL, sua resposta DEVE conter APENAS o código SQL, sem nenhuma formatação ou marcadores como ```sql.
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
                    with st.spinner("Analisando..."):
                        response = agent_executor.invoke({"input": prompt})
                        st.markdown(response["output"])
                        st.session_state.messages.append({"role": "assistant", "content": response["output"]})
                except Exception as e:
                    error_message = "Desculpe, encontrei um erro ao processar sua solicitação. Pode ser um problema com os dados ou uma consulta muito complexa. Por favor, tente uma pergunta mais simples."
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