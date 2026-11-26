import streamlit as st
from backend.utils import render_footer
from backend.services import gerar_nuvem_palavras
from backend.noticias import datas_publicacao
import matplotlib.pyplot as plt
import pandas as pd


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


def carregar_intervalo_datas(caminho_csv: str):
    try:
        df = pd.read_csv(caminho_csv, usecols=["pub_date"], dtype=str)
    except (FileNotFoundError, ValueError):
        return None, None
    datas = datas_publicacao(df["pub_date"]).dropna()
    if datas.empty:
        return None, None
    return datas.min().date(), datas.max().date()



#### Nuvem de palavras
csv_path = "data/noticias/noticias.csv"
stopwords_path = "data/keywords/stopwords.txt"  # Arquivo customizado de stopwords
mask_path = None  # ou "data/imagens/sua_mascara.png"

data_inicial, data_final = carregar_intervalo_datas(csv_path)

if not data_inicial or not data_final:
    st.info("Nenhuma noticia encontrada para definir o periodo da nuvem.")
else:
    col_inicio, col_fim = st.columns(2)
    with col_inicio:
        data_inicio = st.date_input(
            "Data inicial",
            value=data_inicial,
            min_value=data_inicial,
            max_value=data_final,
            key="nuvem_data_inicio"
        )
    with col_fim:
        default_fim = data_final if data_inicio <= data_final else data_inicio
        data_fim = st.date_input(
            "Data final",
            value=default_fim,
            min_value=data_inicio,
            max_value=data_final,
            key="nuvem_data_final"
        )

    if data_inicio > data_fim:
        st.error("A data inicial nao pode ser posterior a data final.")
    else:
        try:
            wordcloud = gerar_nuvem_palavras(
                csv_path,
                stopwords_path,
                mask_path,
                start_date=data_inicio,
                end_date=data_fim
            )

            fig, ax = plt.subplots(figsize=(8.5, 4.25))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            col_esquerda, col_centro, col_direita = st.columns([0.075, 0.85, 0.075])
            with col_centro:
                st.pyplot(fig, use_container_width=True)
        except ValueError as e:
            st.warning(str(e))
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
