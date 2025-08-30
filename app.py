# Importando as bibliotecas necessárias
import streamlit as st
import pandas as pd
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
import os

# --- Configuração da Página ---
st.set_page_config(page_title="Análise Financeira com IA", layout="wide", initial_sidebar_state="expanded")
st.title("🤖 Assistente de Análise Financeira v2.2")

# --- Funções Auxiliares ---
def get_language_instruction():
    return " IMPORTANT: Your final answer must be in Brazilian Portuguese. (IMPORTANTE: Sua resposta final deve ser em português do Brasil.)"

def calcular_kpis(agent):
    instruction = get_language_instruction()
    kpis_a_calcular = {
        "Margem Bruta": f"Calcule a Margem Bruta (Lucro Bruto / Receita Líquida). Exiba o resultado em percentual.{instruction}",
        "Margem Líquida": f"Calcule a Margem Líquida (Lucro Líquido / Receita Líquida). Exiba o resultado em percentual.{instruction}",
        "Liquidez Corrente": f"Calcule o índice de Liquidez Corrente (Ativo Circulante / Passivo Circulante). Exiba como um número (ex: 1.5x).{instruction}"
    }
    
    st.subheader("Dashboard de KPIs Essenciais")
    kpi_cols = st.columns(len(kpis_a_calcular))
    
    for i, (kpi_nome, kpi_pergunta) in enumerate(kpis_a_calcular.items()):
        with kpi_cols[i]:
            with st.spinner(f"Calculando {kpi_nome}..."):
                try:
                    # Modificado para passar a pergunta com a instrução de idioma
                    resposta_bruta = agent.run(kpi_pergunta)
                    # Tentativa de extrair apenas o valor para a métrica
                    st.metric(label=kpi_nome, value=resposta_bruta)
                except Exception as e:
                    st.error(f"Erro ao calcular {kpi_nome}")

# --- Barra Lateral (Sidebar) para Upload ---
with st.sidebar:
    st.header("Carregue seus Arquivos")
    st.write("Formatos aceitos: .xlsx ou .csv")
    dre_file = st.file_uploader("Upload do DRE", type=['xlsx', 'csv'])
    balanco_file = st.file_uploader("Upload do Balanço Patrimonial", type=['xlsx', 'csv'])

# --- Lógica Principal da Aplicação ---
if dre_file is not None and balanco_file is not None:
    try:
        # Carregando os dataframes
        if dre_file.name.endswith('.csv'):
            dre_df = pd.read_csv(dre_file)
        else:
            dre_df = pd.read_excel(dre_file, engine='openpyxl')

        if balanco_file.name.endswith('.csv'):
            balanco_df = pd.read_csv(balanco_file)
        else:
            balanco_df = pd.read_excel(balanco_file, engine='openpyxl')
            
        dre_df['descrição'] = dre_df['descrição'].str.strip()
        balanco_df['descrição'] = balanco_df['descrição'].str.strip()

        with st.expander("Visualizar DRE Completo (Dados Limpos)"):
            st.dataframe(dre_df)
        with st.expander("Visualizar Balanço Patrimonial Completo (Dados Limpos)"):
            st.dataframe(balanco_df)

        # Inicializando o agente de IA
        llm = ChatOpenAI(temperature=0, model="gpt-4o", api_key=st.secrets["OPENAI_API_KEY"])
        
        # ⭐️ ALTERAÇÃO: Removido 'agent_kwargs' e 'handle_parsing_errors' que não são mais suportados
        agent = create_pandas_dataframe_agent(
            llm,
            [dre_df, balanco_df],
            verbose=True,
            allow_dangerous_code=True
        )

        if st.button("Calcular KPIs Essenciais"):
            calcular_kpis(agent)
        st.divider()

        st.subheader("Converse com seus Dados")
        if "messages" not in st.session_state:
            st.session_state.messages = []
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if prompt := st.chat_input("Qual sua pergunta?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analisando..."):
                    # ⭐️ ALTERAÇÃO: Adicionando a instrução de idioma diretamente ao prompt do usuário
                    prompt_with_instruction = prompt + get_language_instruction()
                    response = agent.run(prompt_with_instruction)
                    st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os arquivos. Verifique o formato e o conteúdo. Detalhes: {e}")
else:
    st.info("Por favor, carregue os arquivos de DRE e Balanço na barra lateral para começar.")