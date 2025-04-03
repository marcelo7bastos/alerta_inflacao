import streamlit as st
from backend.utils import render_footer

st.set_page_config(
    page_title="Monitor de Notícias - Inflação de Alimentos",
    layout="wide"
)

# Mensagem inicial (opcional)
st.title("Bem-vindo ao Monitor de Notícias sobre Inflação de Alimentos!")
st.markdown("""
Utilize o menu à esquerda para navegar entre as páginas:
- **Histórico de Notícias:** Consulte o histórico filtrado das notícias sobre inflação de alimentos.
- **Monitor de Notícias:** Busque e visualize notícias atualizadas em tempo real. 
""")

# Exibe o rodapé chamando a função
render_footer()