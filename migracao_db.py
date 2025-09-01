import pandas as pd
import sqlite3
import os

# --- CONFIGURAÇÃO DOS NOMES DE ARQUIVOS ---
ARQUIVO_DRE_CICLOMADE_CSV = 'DRE_CICLOMADE_2024.csv'
ARQUIVO_BALANCO_CICLOMADE_CSV = 'BALANCO_CICLOMADE_2024.csv'
ARQUIVO_DRE_JJMAX_CSV = 'DRE_JJ_MAX_2024.csv'
ARQUIVO_BALANCO_JJMAX_CSV = 'BALANCO_JJ_MAX_2024.csv'
ARQUIVO_DB = 'plataforma_financeira.db'

# --- APAGA O BANCO DE DADOS ANTIGO PARA RECOMEÇAR ---
if os.path.exists(ARQUIVO_DB):
    os.remove(ARQUIVO_DB)

# --- CRIA A CONEXÃO E AS TABELAS ---
conn = sqlite3.connect(ARQUIVO_DB)
cursor = conn.cursor()
print(f"Banco de dados '{ARQUIVO_DB}' criado.")

cursor.execute('CREATE TABLE empresas (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE);')
cursor.execute('CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, role TEXT NOT NULL DEFAULT "user");')
cursor.execute('CREATE TABLE permissoes (id INTEGER PRIMARY KEY, id_usuario INTEGER, id_empresa INTEGER);')
print("Tabelas de estrutura criadas.")

# --- DADOS DE EXEMPLO ---
try:
    # --- Empresa 1 e Usuário 1 (ADMIN) ---
    cursor.execute("INSERT INTO empresas (nome) VALUES (?)", ('CICLOMADE - INDUSTRIA E COMERCIO DE ESPUMAS LTDA',))
    id_empresa_1 = cursor.lastrowid
    
    # Lembre-se de gerar os hashes com o gerar_hash.py e colar aqui
    senha_admin_hash = "$2b$12$JH868yRpoqP7x.k/vvcFo.tCKSVewKRDqVZ3G.4k5N9NtHYdzU0Gu" # Hash para 'senha_admin'
    cursor.execute("INSERT INTO usuarios (nome, email, senha, role) VALUES (?, ?, ?, ?)", ('Admin Principal', 'admin@email.com', senha_admin_hash, 'admin'))
    id_user_1 = cursor.lastrowid
    
    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (id_user_1, id_empresa_1))
    print(f"Empresa 1 e Usuário ADMIN ('admin@email.com') criados.")

    # --- Empresa 2 e Usuário 2 (USER) ---
    # ALTERAÇÃO: Usando o nome da nova empresa
    cursor.execute("INSERT INTO empresas (nome) VALUES (?)", ('JJ MAX INDUSTRIA E COMERCIO DE COMESTICOS LTDA',))
    id_empresa_2 = cursor.lastrowid

    # Lembre-se de gerar os hashes com o gerar_hash.py e colar aqui
    senha_user_2_hash = "$2b$12$41wl/3D9dj0kCj9Ar8kUSuRO2zMlskgjjWqMhoBvX5UMJUvfz1m7i" # Hash para 'senha_user_2'
    cursor.execute("INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)", ('Usuário JJ Max', 'user2@email.com', senha_user_2_hash))
    id_user_2 = cursor.lastrowid
    
    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (id_user_2, id_empresa_2))
    print(f"Empresa 2 (JJ MAX) e Usuário comum ('user2@email.com') criados.")
    
    # O admin também terá acesso à Empresa 2
    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (id_user_1, id_empresa_2))
    print(f"Permissão da Empresa 2 concedida também ao admin.")


    # --- Carregar dados CSV para as empresas ---
    # Carregando dados da Ciclomade (Empresa 1)
    dre_df1 = pd.read_csv(ARQUIVO_DRE_CICLOMADE_CSV)
    dre_df1['empresa_id'] = id_empresa_1
    dre_df1.to_sql('dre', conn, index=False, if_exists='append')
    balanco_df1 = pd.read_csv(ARQUIVO_BALANCO_CICLOMADE_CSV)
    balanco_df1['empresa_id'] = id_empresa_1
    balanco_df1.to_sql('balanco', conn, index=False, if_exists='append')
    print(f"Dados carregados para a Empresa 1 (CICLOMADE).")
    
    # ALTERAÇÃO: Carregando dados da JJ MAX (Empresa 2)
    dre_df2 = pd.read_csv(ARQUIVO_DRE_JJMAX_CSV)
    dre_df2['empresa_id'] = id_empresa_2
    dre_df2.to_sql('dre', conn, index=False, if_exists='append')
    
    balanco_df2 = pd.read_csv(ARQUIVO_BALANCO_JJMAX_CSV)
    balanco_df2['empresa_id'] = id_empresa_2
    balanco_df2.to_sql('balanco', conn, index=False, if_exists='append')
    print(f"Dados carregados para a Empresa 2 (JJ MAX).")

except Exception as e:
    print(f"Ocorreu um erro: {e}")

conn.commit()
conn.close()
print("Migração com dados da JJ MAX concluída.")