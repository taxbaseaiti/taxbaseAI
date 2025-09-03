import streamlit as st
import bcrypt

st.set_page_config(page_title="Gerador de Hash", layout="centered")

st.title("🔑 Gerador de Hash de Senha")
st.write("Use esta ferramenta para criar as senhas criptografadas para o seu banco de dados.")

password = st.text_input("Digite a senha que deseja usar (ex: senha_admin):", type="password")

if password:
    try:
        # Codifica a senha para bytes, que é o formato que o bcrypt espera
        password_bytes = password.encode('utf-8')
        
        # Gera o "sal" e cria o hash
        salt = bcrypt.gensalt()
        hashed_password_bytes = bcrypt.hashpw(password_bytes, salt)
        
        # Descodifica o hash de volta para uma string para podermos copiar
        hashed_password_str = hashed_password_bytes.decode('utf-8')
        
        st.success("Hash gerado com sucesso!")
        st.code(hashed_password_str, language=None)
        st.info("⬆️ Copie o hash acima e cole no seu script 'migracao_db.py'")
        
    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar o hash: {e}")