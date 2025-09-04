import pandas as pd
import sqlite3
import os
import bcrypt
from datetime import datetime, timedelta
import numpy as np

# --- Configuração ---
ARQUIVO_DB = 'plataforma_financeira.db'

# --- APAGA O BANCO DE DADOS ANTIGO ---
if os.path.exists(ARQUIVO_DB):
    os.remove(ARQUIVO_DB)

# --- CRIA A CONEXÃO E AS TABELAS ---
conn = sqlite3.connect(ARQUIVO_DB)
cursor = conn.cursor()
print(f"Banco de dados '{ARQUIVO_DB}' criado.")

# ⭐️ ALTERAÇÃO: Adicionada a coluna 'periodo' para dados históricos ⭐️
cursor.execute('CREATE TABLE empresas (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE);')
cursor.execute('CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, role TEXT NOT NULL DEFAULT "user");')
cursor.execute('CREATE TABLE permissoes (id INTEGER PRIMARY KEY, id_usuario INTEGER, id_empresa INTEGER);')
cursor.execute('CREATE TABLE dre (nome_empresa TEXT, "descrição" TEXT, valor REAL, empresa_id INTEGER, categoria TEXT, periodo TEXT);')
cursor.execute('CREATE TABLE balanco (nome_empresa TEXT, "descrição" TEXT, saldo_atual REAL, empresa_id INTEGER, periodo TEXT);')
cursor.execute('CREATE TABLE knowledge_base (id INTEGER PRIMARY KEY, termo TEXT NOT NULL, definicao TEXT NOT NULL, ferramenta_associada TEXT);')
print("Tabelas de estrutura criadas com a coluna 'periodo'.")


# --- FUNÇÃO DE CATEGORIZAÇÃO (permanece a mesma) ---
def categorizar_conta(descricao):
    if not isinstance(descricao, str): return 'Outros'
    desc = descricao.upper()
    if 'CUSTO' in desc: return 'Custo'
    elif 'RECEITA' in desc: return 'Receita'
    elif 'DESPESA' in desc or 'IMPOSTOS' in desc or 'TAXAS' in desc or '(-) ' in descricao: return 'Despesa'
    elif 'LUCRO' in desc or 'RESULTADO' in desc or 'PREJUÍZO' in desc: return 'Resultado'
    else: return 'Outros'

# --- DICIONÁRIO CONTABILÍSTICO (Base de Conhecimento da Fase 2 + 3) ---
dicionario_contabil = [
    ('EBITDA', 'O EBITDA (Lucro Antes de Juros, Impostos, Depreciação e Amortização) mede a capacidade de geração de caixa operacional...', 'ferramenta_calcular_ebitda'),
    ('Índice de Liquidez Corrente', 'Mede a capacidade da empresa de pagar as suas dívidas de curto prazo...', 'ferramenta_calcular_indice_liquidez'),
    ('Análise de Lucratividade (Margens)', 'Mostra a eficiência da empresa em transformar receita em lucro...', 'ferramenta_analise_lucratividade'),
    ('Retorno sobre o Património Líquido (ROE)', 'Mede a capacidade de uma empresa de gerar lucro a partir do dinheiro dos acionistas...', 'ferramenta_calcular_roe'),
    ('Análise de Tendência de Receita', 'Utiliza dados históricos para projetar a performance futura da receita. Esta análise ajuda a prever o crescimento e a planear estrategicamente.', 'ferramenta_analisar_tendencia_receita'),
    ('Deteção de Anomalias em Despesas', 'Compara o valor de uma despesa no último período com a sua média histórica para identificar aumentos inesperados que possam indicar problemas de controlo de custos ou oportunidades de otimização.', 'ferramenta_detectar_anomalia_despesa')
]
cursor.executemany("INSERT INTO knowledge_base (termo, definicao, ferramenta_associada) VALUES (?, ?, ?)", dicionario_contabil)
print("Base de Conhecimento populada.")

# --- DADOS DE USUÁRIOS E EMPRESAS ---
# IMPORTANTE: Use o script 'gerar_hash.py' para criar os hashes das suas senhas.
admin123 = "$2b$12$YeOk1GaVfS9D0KBYCfjC6eNw0A5A0TwDjAcE6.rnsorGqn8hE7h1W"
user123 = "$2b$12$zEZCaUK65FZWGA0k0yVRK..2NX4PYa1zLx6q/4snR9eq1x94Lv4LS"

if "COLOQUE_SEU_HASH" in admin123 or "COLOQUE_SEU_HASH" in user123:
    print("\n!!! ATENÇÃO: HASHES DE SENHA NÃO FORAM ATUALIZADOS !!!")
    conn.close()
    exit()

usuarios_iniciais = [(1, 'Admin Principal', 'admin@email.com', admin123, 'admin'), (2, 'Utilizador Teste', 'user@email.com', user123, 'user')]
cursor.executemany("INSERT INTO usuarios (id, nome, email, senha, role) VALUES (?, ?, ?, ?, ?)", usuarios_iniciais)
print("Utilizadores iniciais criados.")

empresas_para_carregar = [
    { "id": 1, "nome": "CICLOMADE - INDUSTRIA E COMERCIO DE ESPUMAS LTDA", "dre_csv": "DRE_CICLOMADE_2024.csv", "balanco_csv": "BALANCO_CICLOMADE_2024.csv" },
    { "id": 2, "nome": "JJ MAX INDUSTRIA E COMERCIO DE COMESTICOS LTDA", "dre_csv": "DRE_JJ_MAX_2024.csv", "balanco_csv": "BALANCO_JJ_MAX_2024.csv" },
    { "id": 3, "nome": "SAUDE & FORMA-FARMACIA DE MANIPULACAO EHOMEOPATIA LTDA", "dre_csv": "DRE_SAUDE_FORMA_2024.csv", "balanco_csv": "BALANCO_SAUDE_FORMA_2024.csv" }
]

# --- ⭐️ LÓGICA DE SIMULAÇÃO DE DADOS HISTÓRICOS ⭐️ ---
for empresa in empresas_para_carregar:
    try:
        cursor.execute("INSERT INTO empresas (id, nome) VALUES (?, ?)", (empresa['id'], empresa['nome']))
        
        # Simula os últimos 6 meses de dados
        for i in range(6):
            periodo_atual = (datetime.now() - timedelta(days=30*i)).strftime('%Y-%m')
            fator_variacao = 1 - (i * 0.05) # Simula um pequeno crescimento linear

            # Carrega DRE com variação e período
            dre_df = pd.read_csv(empresa['dre_csv'])
            dre_df['empresa_id'] = empresa['id']
            dre_df['categoria'] = dre_df['descrição'].apply(categorizar_conta)
            dre_df['periodo'] = periodo_atual
            dre_df['valor'] = dre_df['valor'] * fator_variacao * (1 + (0.05 - 0.1 * np.random.rand(len(dre_df)))) # Adiciona ruído
            dre_df.to_sql('dre', conn, if_exists='append', index=False)

            # Carrega Balanço com variação e período
            balanco_df = pd.read_csv(empresa['balanco_csv'])
            balanco_df['empresa_id'] = empresa['id']
            balanco_df['periodo'] = periodo_atual
            balanco_df['saldo_atual'] = balanco_df['saldo_atual'] * fator_variacao * (1 + (0.05 - 0.1 * np.random.rand(len(balanco_df))))
            balanco_df.to_sql('balanco', conn, if_exists='append', index=False)
        
        print(f"Dados históricos simulados e categorizados para: {empresa['nome']}")
    except FileNotFoundError:
        print(f"AVISO: Arquivo CSV não encontrado para a empresa '{empresa['nome']}'. Pulando.")
    except Exception as e:
        print(f"Erro ao carregar dados para {empresa['nome']}: {e}")

# Conceder permissões (permanece o mesmo)
permissoes_iniciais = [(1, 1), (1, 2), (1, 3), (2, 2)]
cursor.executemany("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", permissoes_iniciais)
print("Permissões iniciais concedidas.")

conn.commit()
conn.close()
print("Migração com dados históricos e base de conhecimento concluída.")