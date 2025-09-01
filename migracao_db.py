import pandas as pd
import sqlite3
import os
# Lembre-se de ter o bcrypt instalado: pip install bcrypt

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
# ALTERAÇÃO: Adicionada a coluna 'role' com valor padrão 'user'
cursor.execute('CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, role TEXT NOT NULL DEFAULT "user");')
cursor.execute('CREATE TABLE permissoes (id INTEGER PRIMARY KEY, id_usuario INTEGER, id_empresa INTEGER);')
print("Tabelas de estrutura criadas com a coluna 'role'.")

# --- DADOS DE EXEMPLO ---
try:
    # --- Empresa 1 e Usuário 1 (ADMIN) ---
    cursor.execute("INSERT INTO empresas (nome) VALUES (?)", ('CICLOMADE - INDUSTRIA E COMERCIO DE ESPUMAS LTDA',))
    id_empresa_1 = cursor.lastrowid
    
    # Use o script gerar_hash.py para gerar os hashes das senhas 'senha_admin' e 'senha_user_2'
    senha_admin_hash = "$2b$12$OALEfubER1tXaIAVSiIbJ.PrShpkqJ1Qk1LeNvKT8R3Gki0fPAlkK" # SUBSTITUA PELO HASH DE 'senha_admin'
    # ALTERAÇÃO: Inserindo o cargo 'admin' para o primeiro usuário
    cursor.execute("INSERT INTO usuarios (nome, email, senha, role) VALUES (?, ?, ?, ?)", ('Admin Principal', 'admin@email.com', senha_admin_hash, 'admin'))
    id_user_1 = cursor.lastrowid
    
    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (id_user_1, id_empresa_1))
    print(f"Empresa 1 e Usuário ADMIN ('admin@email.com') criados e associados.")

    # --- Empresa 2 e Usuário 2 (USER) ---
    cursor.execute("INSERT INTO empresas (nome) VALUES (?)", ('Empresa Fantasia XYZ',))
    id_empresa_2 = cursor.lastrowid

    senha_user_2_hash = "$2b$12$q0tVUVhFRyLp8KEulb/t5u4iTK/JNrlxWswePuEODBcGVa7OGEVv2" # SUBSTITUA PELO HASH DE 'senha_user_2'
    cursor.execute("INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)", ('Usuário Fantasia', 'user2@email.com', senha_user_2_hash))
    id_user_2 = cursor.lastrowid
    
    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (id_user_2, id_empresa_2))
    print(f"Empresa 2 e Usuário comum ('user2@email.com') criados e associados.")

    # Adiciona a empresa 2 também para o admin
    cursor.execute("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", (id_user_1, id_empresa_2))
    print(f"Permissão da Empresa 2 concedida também ao admin.")

    # --- Carregar dados CSV para as empresas ---
    # (O código para carregar os dados do DRE e Balanço permanece o mesmo da versão anterior)
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
print("Migração com cargos de usuário concluída.")