import streamlit as st
from backend.services import (
    load_keywords_from_csv, 
    get_default_keywords, 
    search_keywords_in_rss, 
    classificar_artigo, 
    get_feed_name
)

from backend.utils import render_footer

# Configura a página se necessário (opcional, pois o Streamlit configura automaticamente)
st.set_page_config(page_title="Monitor de Notícias - Inflação de Alimentos", layout="wide")

st.title("📰 Monitor de Notícias - Inflação de Alimentos")

# Sidebar para descrição do projeto (caso queira manter)
# st.sidebar.markdown(
#     """
#     ## Sobre o Projeto
#     Este aplicativo monitora notícias sobre inflação de alimentos a partir de diversos feeds RSS.
#     Utilizando um conjunto de palavras-chave, o sistema filtra e exibe somente as notícias relevantes.
#     """
# )

# Carrega as keywords
csv_path = "data/keywords/ipca_alimentacao_bebidas.csv"
try:
    additional_keywords = load_keywords_from_csv(csv_path)
except Exception as e:
    additional_keywords = []

default_keywords = get_default_keywords()
keywords = list(set(default_keywords + additional_keywords))

# Lista de Feeds
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

if st.button("🔍 Buscar Notícias"):
    message_placeholder = st.empty()
    message_placeholder.info("Buscando notícias, por favor aguarde...")

    resultados = search_keywords_in_rss(rss_feeds, keywords)
    
    # Chamada da classificação para aprimorar os artigos
    for item in resultados:
        item = classificar_artigo(item)
    
    message_placeholder.empty()

    if resultados:
        total = len(resultados)
        filtered_count = sum(1 for artigo in resultados if artigo.get("1. O artigo aborda o tema da inflação?") == "Sim")
        st.success(
            f"Encontramos {total} notícias relevantes e nossa IA selecionou com precisão as {filtered_count} que realmente abordam a inflação de alimentos!"
        )
        # Agrupamento por veículo
        grouped_results = {}
        for item in resultados:
            feed_name = get_feed_name(item['feed_url'])
            if feed_name not in grouped_results:
                grouped_results[feed_name] = []
            grouped_results[feed_name].append(item)
        # Exibe os resultados de forma organizada
        for feed_name, items in grouped_results.items():
            with st.expander(feed_name, expanded=False):
                found = False
                for i in items:
                    if i.get("1. O artigo aborda o tema da inflação?") == "Sim":
                        found = True
                        st.markdown(f"**Título:** {i['title']}")
                        st.write(f"Link: {i['link']}")
                        st.write(f"Fonte: {i['feed_url']}")
                        st.write(f"Data de publicação: {i['pub_date']}")
                        st.write(f"Palavra-chave: {i['matched_keyword']}")
                        st.write(f"1. O artigo aborda o tema da inflação? {i['1. O artigo aborda o tema da inflação?']}")
                        st.write(f"2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral? {i['2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral?']}")
                        st.write(f"3. O artigo aborda especificamente a inflação de alimentos? {i['3. O artigo aborda especificamente a inflação de alimentos?']}")
                        st.write(f"4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor? {i['4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor?']}")
                        st.write("---")
                if not found:
                    st.warning("Nenhuma notícia sobre inflação de alimentos encontrada.")


# Exibe o rodapé chamando a função
render_footer()