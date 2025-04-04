import streamlit as st
from backend.utils import render_footer
from backend.services import gerar_nuvem_palavras
import matplotlib.pyplot as plt


st.set_page_config(
    page_title="Início - Monitor de Notícias",
    page_icon="🏠",  # emoji de casa, por exemplo
    layout="wide"
)

# Mensagem inicial (opcional)
st.title("Monitor de Notícias sobre Inflação de Alimentos!")
# st.markdown("""
# Utilize o menu à esquerda para navegar entre as páginas:
# - **Histórico de Notícias:** Consulte o histórico filtrado das notícias sobre inflação de alimentos.
# - **Monitor de Notícias:** Busque e visualize notícias atualizadas em tempo real. 
# """)
st.markdown("""
Utilize o menu à esquerda para navegar entre as páginas:
""")



#### Nuvem de palavras
try:
    csv_path = "data/noticias/noticias.csv"
    stopwords_path = "data/keywords/stopwords.txt"  # Arquivo customizado de stopwords
    # mask_path pode ser definido se você tiver uma imagem personalizada, senão deixe como None
    mask_path = None  # ou "data/imagens/sua_mascara.png"
    
    # Gera a nuvem de palavras
    wordcloud = gerar_nuvem_palavras(csv_path, stopwords_path, mask_path)
    
    # Exibe a nuvem com Matplotlib
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)
except Exception as e:
    st.error("Erro ao gerar a nuvem de palavras: " + str(e))
#### Fim da nuvem de palavras

#### Sidebar
# Sidebar para descrição do projeto (caso queira manter)
st.sidebar.markdown(
    """
    ## Sobre o Projeto
    Este aplicativo monitora notícias sobre inflação de alimentos a partir de diversos feeds RSS.
    Utilizando um conjunto de palavras-chave, o sistema filtra as notícias. 
    Em seguida, um modelo de linguagem natura (LLM) classifica as notícias.
    Por fim, a aplicação exibe somente as notícias relevantes.
    """
)

### Fim da sidebar

# Exibe o rodapé chamando a função
render_footer()