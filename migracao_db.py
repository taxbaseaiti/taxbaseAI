import pandas as pd
import sqlite3
import os
# A biblioteca 'streamlit_authenticator' foi removida, pois não é mais necessária aqui.

# --- CONFIGURAÇÃO ---
ARQUIVO_DRE_CSV = 'DRE_CICLOMADE_2024.csv'
ARQUIVO_BALANCO_CSV = 'BALANCO_CICLOMADE_2024.csv'
ARQUIVO_DB = 'plataforma_financeira.db'

# --- APAGA O BANCO DE DADOS ANTIGO ---
if os.path.exists(ARQUIVO_DB):
    os.remove(ARQUIVO_DB)

# --- CRIA A CONEXÃO E AS TABELAS ---
conn = sqlite3.connect(ARQUIVO_DB)
cursor = conn.cursor()
print(f"Banco de dados '{ARQUIVO_DB}' criado.")

# Criar tabelas
cursor.execute('CREATE TABLE empresas (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE);')
cursor.execute('CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT);')
cursor.execute('CREATE TABLE permissoes (id INTEGER PRIMARY KEY, id_usuario INTEGER, id_empresa INTEGER);')
print("Tabelas de estrutura criadas.")

# --- DADOS DE EXEMPLO ---
try:
    # --- Empresa 1 e Usuário 1 ---
    cursor.execute("INSERT INTO empresas (nome) VALUES (?)", ('CICLOMADE - INDUSTRIA E COMERCIO DE ESPUMAS LTDA',))
    id_empresa_1 = cursor.lastrowid
    
    # ⭐️ COLE AQUI O HASH GERADO PARA 'senha_user_1' ⭐️
    senha_user_1_hash = "$2b$12$YTIIou.xbjKuuVMAe.mY/urNYTZEfXK7C8ZSbniYH73/Zep2D2G.O" 
    cursor.execute("INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)", ('Usuário Ciclomade', 'user1@email.com', senha_user_1_hash))
    id_user_1 = cursor.lastrowid
    
    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (id_user_1, id_empresa_1))
    print(f"Empresa 1 e Usuário 1 criados e associados.")

    # --- Empresa 2 e Usuário 2 ---
    cursor.execute("INSERT INTO empresas (nome) VALUES (?)", ('Empresa Fantasia XYZ',))
    id_empresa_2 = cursor.lastrowid

    # ⭐️ COLE AQUI O HASH GERADO PARA 'senha_user_2' ⭐️
    senha_user_2_hash = "$2b$12$E8zGbn4VPUMfxHgD2TKnb.L3z.JMe3ZiVCVanqOCLXwOXOtZUrGxO"
    cursor.execute("INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)", ('Usuário Fantasia', 'user2@email.com', senha_user_2_hash))
    id_user_2 = cursor.lastrowid
    
    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (id_user_2, id_empresa_2))
    print(f"Empresa 2 e Usuário 2 criados e associados.")

    # --- Carregar dados CSV para as empresas ---
    dre_df1 = pd.read_csv(ARQUIVO_DRE_CSV)
    dre_df1['empresa_id'] = id_empresa_1
    dre_df1.to_sql('dre', conn, index=False, if_exists='append')

    balanco_df1 = pd.read_csv(ARQUIVO_BALANCO_CSV)
    balanco_df1['empresa_id'] = id_empresa_1
    balanco_df1.to_sql('balanco', conn, index=False, if_exists='append')
    print(f"Dados carregados para a Empresa 1.")
    
    dre_df2 = dre_df1.copy()
    dre_df2['empresa_id'] = id_empresa_2
    dre_df2['valor'] = dre_df2['valor'] * 0.5
    dre_df2.to_sql('dre', conn, index=False, if_exists='append')
    
    balanco_df2 = balanco_df1.copy()
    balanco_df2['empresa_id'] = id_empresa_2
    balanco_df2['saldo_atual'] = balanco_df2['saldo_atual'] * 0.5
    balanco_df2.to_sql('balanco', conn, index=False, if_exists='append')
    print(f"Dados (fantasia) carregados para a Empresa 2.")

except Exception as e:
    print(f"Ocorreu um erro: {e}")

conn.commit()
conn.close()
print("Migração multiempresa concluída.")