# app.py
import streamlit as st
import pandas as pd
from backend import load_keywords_from_csv, get_default_keywords, search_keywords_in_rss

# ======================
# 1) Função de nome de veículo
# ======================
def get_feed_name(feed_url: str) -> str:
    """
    Dado um feed_url, retorna um nome amigável do veículo de imprensa.
    Ajuste as condições conforme necessário.
    """
    feed_url_lower = feed_url.lower()
    if "g1.globo.com" in feed_url_lower:
        return "G1"
    elif "folha.uol.com.br" in feed_url_lower:
        return "Folha"
    elif "bbc.com" in feed_url_lower:
        return "BBC"
    elif "exame.com" in feed_url_lower:
        return "Exame"
    elif "cartacapital.com.br" in feed_url_lower:
        return "Carta Capital"
    elif "istoedinheiro" in feed_url_lower:
        return "IstoÉ Dinheiro"
    elif "infomoney" in feed_url_lower:
        return "InfoMoney"
    elif "jovempan.com.br" in feed_url_lower:
        return "Jovem Pan"
    elif "ig.com.br" in feed_url_lower:
        return "IG Economia"
    else:
        # Se não identificar, retorna a própria URL
        return feed_url

# ======================
# 2) Configuração e título
# ======================
st.set_page_config(page_title="Monitor de Notícias sobre Inflação de Alimentos", layout="wide")
st.title("📰 Monitor de Notícias - Inflação de Alimentos")

# ======================
# 3) Sidebar (Descrição do projeto)
# ======================
st.sidebar.markdown(
    """
    ## Sobre o Projeto

    Este aplicativo monitora notícias sobre inflação de alimentos a partir de diversos feeds RSS.
    Utilizando um conjunto de palavras-chave, o sistema filtra e exibe somente as notícias relevantes 
    para que você acompanhe as principais atualizações do setor.
    """
)

# ======================
# 4) Carregando as keywords
# ======================
csv_path = "data/keywords/ipca_alimentacao_bebidas.csv"
try:
    additional_keywords = load_keywords_from_csv(csv_path)
    #st.sidebar.info("Palavras-chave carregadas com sucesso!")
except Exception as e:
    #st.sidebar.error(f"Erro ao carregar palavras-chave: {e}")
    additional_keywords = []

default_keywords = get_default_keywords()
keywords = list(set(default_keywords + additional_keywords))
#st.sidebar.write("Palavras-chave utilizadas:", keywords)

# ======================
# 5) Lista de Feeds
# ======================
rss_feeds = [
    'https://g1.globo.com/rss/g1/',
    'https://feeds.folha.uol.com.br/emcimadahora/rss091.xml',
    'https://www.bbc.com/portuguese/index.xml',
    'https://exame.com/feed/',
    'https://www.cartacapital.com.br/feed/',
    'https://www.istoedinheiro.com.br/feed/',
    'https://www.infomoney.com.br/feed/',
    'https://www.jovempan.com.br/feed',
    'https://economia.ig.com.br/rss.xml',
]

# ======================
# 6) Botão para buscar notícias
# ======================

if st.button("🔍 Buscar Notícias"):
    # 1) Placeholder para mensagens
    message_placeholder = st.empty()

    # 2) Mensagem inicial
    message_placeholder.info("Buscando notícias, por favor aguarde...")

    # 3) Faz a busca
    resultados = search_keywords_in_rss(rss_feeds, keywords)

    # 4) Remove a mensagem de "Buscando..."
    message_placeholder.empty()

    # 5) Mostra os resultados

    if resultados:
        st.success(f"Foram encontradas {len(resultados)} notícia(s) relevantes.")

        # ======================
        # 6a) Agrupar por veículo
        # ======================
        grouped_results = {}
        for item in resultados:
            feed_name = get_feed_name(item['feed_url'])
            if feed_name not in grouped_results:
                grouped_results[feed_name] = []
            grouped_results[feed_name].append(item)

        # ======================
        # 6b) Exibir de forma organizada
        # ======================
        for feed_name, items in grouped_results.items():
            # Cria uma seção recolhível para cada veículo
            with st.expander(feed_name, expanded=False):
                # Dentro do expander, listamos cada notícia
                for i in items:
                    st.markdown(f"**Título:** {i['title']}")
                    st.write(f"Link: {i['link']}")
                    st.write(f"Fonte: {i['feed_url']}")
                    st.write(f"Data de publicação: {i['pub_date']}")
                    st.write(f"Palavra-chave: {i['matched_keyword']}")
                    st.write("---")  # Separador

    else:
        st.warning("Nenhuma notícia encontrada com as palavras-chave fornecidas.")


# ======================
# 8) Rodapé 
# ======================
footer_html = """
<style>
footer {
    visibility: hidden; /* Esconde o footer padrão do Streamlit */
}
.main .block-container {
    padding-bottom: 60px; /* Espaço extra para não sobrepor o conteúdo */
}
.custom-footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #f2f2f2;
    text-align: center;
    padding: 10px 0;
    font-size: 14px;
    color: #666;
}
</style>

<div class="custom-footer">
    Feito por <strong>Marcelo Cabreira Bastos</strong> | 
    Contato: <a href="mailto:marcelo.cabreira@mda.gov.br">marcelo.cabreira@mda.gov.br</a> | 
    <a href="https://www.linkedin.com/in/marcelo-cabreira-bastos/" target="_blank">LinkedIn</a>
</div>
"""

st.markdown(footer_html, unsafe_allow_html=True)






