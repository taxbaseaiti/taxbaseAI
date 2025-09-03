import pandas as pd
import sqlite3
import os
import bcrypt

# --- CONFIGURAÇÃO ---
ARQUIVO_DB = 'plataforma_financeira.db'

# --- APAGA O BANCO DE DADOS ANTIGO PARA UM COMEÇO LIMPO ---
if os.path.exists(ARQUIVO_DB):
    os.remove(ARQUIVO_DB)

# --- CRIA A CONEXÃO E AS TABELAS ---
conn = sqlite3.connect(ARQUIVO_DB)
cursor = conn.cursor()
print(f"Banco de dados '{ARQUIVO_DB}' criado.")

# Criar tabelas (dre agora tem a coluna 'categoria')
cursor.execute('CREATE TABLE empresas (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE);')
cursor.execute('CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, role TEXT NOT NULL DEFAULT "user");')
cursor.execute('CREATE TABLE permissoes (id INTEGER PRIMARY KEY, id_usuario INTEGER, id_empresa INTEGER);')
cursor.execute('CREATE TABLE dre (nome_empresa TEXT, descrição TEXT, valor REAL, empresa_id INTEGER, categoria TEXT);')
cursor.execute('CREATE TABLE balanco (nome_empresa TEXT, descrição TEXT, saldo_atual REAL, empresa_id INTEGER);')
print("Tabelas de estrutura criadas com a coluna 'categoria'.")

# --- FUNÇÃO DE CATEGORIZAÇÃO (ESSENCIAL) ---
def categorizar_conta(descricao):
    if not isinstance(descricao, str):
        return 'Outros'
    desc = descricao.upper()
    # Ordem de prioridade ajustada para maior precisão
    if 'CUSTO' in desc:
        return 'Custo'
    elif 'RECEITA' in desc:
        return 'Receita'
    elif 'DESPESA' in desc or 'IMPOSTOS' in desc or 'TAXAS' in desc or '(-) ' in descricao:
        return 'Despesa'
    elif 'LUCRO' in desc or 'RESULTADO' in desc or 'PREJUÍZO' in desc:
        return 'Resultado'
    else:
        return 'Outros'

# --- DADOS DE USUÁRIOS E EMPRESAS ---
# Use o gerar_hash.py para criar os hashes das senhas. SUBSTITUA PELOS SEUS VALORES GERADOS.
senha_admin_hash = "$2b$12$EHN2pyC5s5yL5s7V4f.M4.KzU2kL4kP2s7g/5vX6t/8s7o7h8f7Jk" # Hash para 'senha_admin'
senha_user_hash = "$2b$12$41wl/3D9dj0kCj9Ar8kUSuRO2zMlskgjjWqMhoBvX5UMJUvfz1m7i"  # Hash para 'senha_user'

usuarios_iniciais = [
    (1, 'Admin Principal', 'admin@email.com', senha_admin_hash, 'admin'),
    (2, 'Usuário Teste', 'user@email.com', senha_user_hash, 'user')
]
cursor.executemany("INSERT INTO usuarios (id, nome, email, senha, role) VALUES (?, ?, ?, ?, ?)", usuarios_iniciais)
print("Usuários iniciais criados.")

empresas_para_carregar = [
    { "id": 1, "nome": "CICLOMADE - INDUSTRIA E COMERCIO DE ESPUMAS LTDA", "dre_csv": "DRE_CICLOMADE_2024.csv", "balanco_csv": "BALANCO_CICLOMADE_2024.csv" },
    { "id": 2, "nome": "JJ MAX INDUSTRIA E COMERCIO DE COMESTICOS LTDA", "dre_csv": "DRE_JJ_MAX_2024.csv", "balanco_csv": "BALANCO_JJ_MAX_2024.csv" },
    { "id": 3, "nome": "SAUDE & FORMA-FARMACIA DE MANIPULACAO EHOMEOPATIA LTDA", "dre_csv": "DRE_SAUDE_FORMA_2024.csv", "balanco_csv": "BALANCO_SAUDE_FORMA_2024.csv" }
]

for empresa in empresas_para_carregar:
    try:
        cursor.execute("INSERT INTO empresas (id, nome) VALUES (?, ?)", (empresa['id'], empresa['nome']))
        
        dre_df = pd.read_csv(empresa['dre_csv'])
        dre_df['empresa_id'] = empresa['id']
        dre_df['categoria'] = dre_df['descrição'].apply(categorizar_conta)
        dre_df.to_sql('dre', conn, if_exists='append', index=False)

        balanco_df = pd.read_csv(empresa['balanco_csv'])
        balanco_df['empresa_id'] = empresa['id']
        balanco_df.to_sql('balanco', conn, if_exists='append', index=False)
        
        print(f"Dados carregados e categorizados para: {empresa['nome']}")
    except FileNotFoundError:
        print(f"AVISO: Arquivo CSV não encontrado para a empresa '{empresa['nome']}'. Pulando.")
    except Exception as e:
        print(f"Erro ao carregar dados para {empresa['nome']}: {e}")

# Conceder permissões
permissoes_iniciais = [
    (1, 1), (1, 2), (1, 3), # Admin acessa todas
    (2, 2)  # User 2 acessa SÓ a JJ MAX
]
cursor.executemany("INSERT INTO permissoes (id_usuario, id_empresa) VALUES (?, ?)", permissoes_iniciais)
print("Permissões iniciais concedidas.")

conn.commit()
conn.close()
print("Migração com categorização de contas concluída.")