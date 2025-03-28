# app.py
import streamlit as st
import pandas as pd
from backend import load_keywords_from_csv, get_default_keywords, search_keywords_in_rss, classificar_artigo

######## Preparação para uso da OpenAI
import openai
# Acesse a chave usando st.secrets
openai.api_key = st.secrets["openai"]["api_key"]
# Se preferir, você pode definir um alias:
client = openai
########



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
# Lista de feeds RSS para monitorar (adicionar/remover conforme necessário)]
rss_feeds = [
    # Feeds funcionando corretamente:
    'https://g1.globo.com/rss/g1/',  # Portal de notícias da Globo, ampla cobertura nacional, política, economia e cotidiano.
    'https://feeds.folha.uol.com.br/emcimadahora/rss091.xml',  # Folha de S.Paulo, jornal com ampla cobertura em política, economia e sociedade.
    'https://www.bbc.com/portuguese/index.xml',  # Versão em português da BBC, com ampla cobertura internacional e local.
    'https://exame.com/feed/',  # Revista Exame, especializada em economia, negócios e investimentos.
    'https://www.cartacapital.com.br/feed/',  # Carta Capital, revista focada em política, economia e sociedade.
    'https://www.istoedinheiro.com.br/feed/',  # Revista especializada em economia e negócios.
    'https://www.infomoney.com.br/feed/',  # Site especializado em economia, mercado financeiro e investimentos.
    'https://www.jovempan.com.br/feed',  # Portal da Rádio Jovem Pan, com cobertura em tempo real sobre política, economia e cotidiano.
    'https://economia.ig.com.br/rss.xml',  # Portal iG, notícias gerais com foco em economia e negócios.

    # # Feeds sem itens (provável sitemap ou estrutura não compatível):
    # 'https://www.cnnbrasil.com.br/sitemap-news.xml',  # CNN Brasil, notícias rápidas e cobertura internacional.
    # 'https://oglobo.globo.com/rss.xml',  # Jornal O Globo, notícias nacionais, internacionais, política e economia.

    # # Feeds com erro de parsing (XML inválido):
    # 'https://rss.uol.com.br/feed/noticias.xml',  # Portal UOL, um dos maiores portais com notícias gerais e economia.
    # 'https://www.terra.com.br/rss/Controller?channelid=3d5d59942b25e410VgnVCM10000098cceb0aRCRD&ctName=atomo-noticia',  # Portal Terra, notícias gerais, economia e cotidiano.

    # # Feeds com status HTTP 404 (não encontrados):
    # 'https://www.estadao.com.br/rss/ultimas.xml',  # O Estado de S. Paulo, tradicional jornal brasileiro focado em política e economia.
    # 'https://noticias.r7.com/feed.xml',  # Portal da Record com notícias gerais, economia e política.
    # 'https://brasil.elpais.com/rss/brasil/portada.xml',  # Versão brasileira do jornal espanhol El País, com foco em análise política.
    # 'https://veja.abril.com.br/rss.xml',  # Revista Veja, foco em política, economia e atualidades.
    # 'https://epocanegocios.globo.com/rss/ultimas/feed.xml',  # Época Negócios, revista de negócios e economia.
    # 'https://www.correiobraziliense.com.br/rss/noticia-brasil.xml',  # Correio Braziliense, jornal tradicional de Brasília com foco político e econômico.

    # # Feeds com falha de conexão:
    # 'https://www.valor.globo.com/rss',  # Valor Econômico, especializado em economia, mercados financeiros e negócios.
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
    #teste: cortar para 5 resultados
    #resultados = resultados[:5]
    #st.write("Estrutura dos artigos:", resultados)

    #3.1) Aprimorares os resultados com a OpenAI
    for item in resultados:
        item = classificar_artigo(item)
    #st.write("Artigos aprimorados:", resultados)
            


    # 4) Remove a mensagem de "Buscando..."
    message_placeholder.empty()

    # 5) Mostra os resultados
    if resultados:
        total = len(resultados)
        filtered_count = sum(1 for artigo in resultados if artigo.get("1. O artigo aborda o tema da inflação?") == "Sim")
        st.success(
            f"Encontramos {total} notícias relevantes e nossa IA selecionou com precisão as {filtered_count} que realmente abordam a inflação de alimentos!\n"
             "Confira nossa curadoria inteligente e fique por dentro das principais tendências."
        )

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
        with st.expander(feed_name, expanded=False):
            found = False  # Flag para verificar se pelo menos um item foi exibido
            for i in items:
                # Apenas exibe se a resposta à pergunta 1 for "Sim"
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
                    st.write("---")  # Separador visual
            if not found:
                st.warning("Nenhuma notícia sobre inflação de alimentos encontrada.")


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
.icon {
    width: 20px;
    height: 20px;
    vertical-align: middle;
    margin-right: 5px;
    border-radius: 4px; /* Borda levemente arredondada */
}
</style>

<div class="custom-footer">
    Feito por <strong>Marcelo Cabreira Bastos</strong> | 
    Contato: <a href="mailto:marcelo.cabreira@mda.gov.br">marcelo.cabreira@mda.gov.br</a> | 
    <a href="https://www.linkedin.com/in/marcelo-cabreira-bastos/" target="_blank">
        <img src="https://cdn-icons-png.flaticon.com/512/174/174857.png" alt="LinkedIn" class="icon">
        LinkedIn
    </a> |
    <a href="https://api.whatsapp.com/send?phone=5561981983931" target="_blank">
        <img src="https://cdn-icons-png.flaticon.com/512/124/124034.png" alt="WhatsApp" class="icon">
        WhatsApp
    </a>
</div>
"""

import streamlit as st
st.markdown(footer_html, unsafe_allow_html=True)








