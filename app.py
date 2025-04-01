import streamlit as st
import pandas as pd
import os
from backend import load_keywords_from_csv, get_default_keywords, search_keywords_in_rss, classificar_artigo

######## Preparação para uso da OpenAI
import openai
openai.api_key = st.secrets["openai"]["api_key"]
client = openai
########

# ======================
# 1) Função de nome de veículo
# ======================
def get_feed_name(feed_url: str) -> str:
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
        return feed_url

# ======================
# 2) Configuração e título do app
# ======================
st.set_page_config(page_title="Monitor de Notícias sobre Inflação de Alimentos", layout="wide")
st.title("📰 Monitor de Notícias - Inflação de Alimentos")

# ======================
# 3) Sidebar: Descrição do projeto e escolha de tela
# ======================
st.sidebar.markdown(
    """
    ## Sobre o Projeto
    Este aplicativo monitora notícias sobre inflação de alimentos a partir de diversos feeds RSS.
    Utilizando um conjunto de palavras-chave, o sistema filtra e exibe somente as notícias relevantes 
    para que você acompanhe as principais atualizações do setor.
    """
)

# Seletor de tela
pagina = st.sidebar.radio("Selecione a tela", ["Monitor de Notícias", "Histórico de Inflação"])

# ======================
# 4) Carregando as keywords
# ======================
csv_path = "data/keywords/ipca_alimentacao_bebidas.csv"
try:
    additional_keywords = load_keywords_from_csv(csv_path)
except Exception as e:
    additional_keywords = []

default_keywords = get_default_keywords()
keywords = list(set(default_keywords + additional_keywords))

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
# Tela: Monitor de Notícias
# ======================
if pagina == "Monitor de Notícias":
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

# ======================
# Tela: Histórico de Inflação
# ======================
elif pagina == "Histórico de Inflação":
    st.title("Histórico de Inflação")
    csv_filepath = "data/noticias/noticias.csv"
    
    if os.path.exists(csv_filepath):
        # Lê o CSV forçando todas as colunas como string
        df = pd.read_csv(csv_filepath, dtype=str)

        # ===========================
        # 1) Filtrar apenas notícias onde a coluna 
        #    "1. O artigo aborda o tema da inflação?" é "Sim"
        # ===========================
        col_inflacao = "1. O artigo aborda o tema da inflação?"
        df = df[df[col_inflacao] == "Sim"]

        # ===========================
        # 2) Conversão de datas e ordenação decrescente
        # ===========================
        # Tenta converter a coluna pub_date para datetime
        # Se houver datas em formato inconsistente, elas ficarão como NaT
        # Converte a coluna pub_date para datetime, forçando UTC
        df["pub_date"] = pd.to_datetime(df["pub_date"], errors="coerce", utc=True)

        # # Converte de UTC para o fuso horário de São Paulo (UTC-3)
        df["pub_date"] = df["pub_date"].dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)


        # Ordena por pub_date (mais recentes primeiro)
        df = df.sort_values(by="pub_date", ascending=False)

        # ===========================
        # 3) Filtros de data (início e fim)
        # ===========================
        # Sugere-se definir valores padrão adequados ao seu cenário
        min_date = df["pub_date"].min()
        max_date = df["pub_date"].max()

        # Se min_date ou max_date forem NaT (caso não haja datas válidas), defina manualmente
        if pd.isna(min_date):
            min_date = pd.to_datetime("2023-01-01")
        if pd.isna(max_date):
            max_date = pd.to_datetime("today")

        st.write("### Filtrar por data de publicação")
        start_date = st.date_input("Data de Início", value=min_date.date())
        end_date = st.date_input("Data de Fim", value=max_date.date())

        if start_date > end_date:
            st.warning("A data de início não pode ser maior que a data de fim.")
        else:
            # Aplica o filtro de datas
            mask = (df["pub_date"].dt.date >= start_date) & (df["pub_date"].dt.date <= end_date)
            df = df[mask]

        # ===========================
        # 4) Exibição em lista
        # ===========================
        st.write(f"Exibindo {len(df)} notícias filtradas:")

        if len(df) == 0:
            st.warning("Nenhuma notícia encontrada nesse intervalo de datas.")
        else:
            # Itera sobre o DataFrame e exibe cada notícia
            for idx, row in df.iterrows():
                with st.expander(f"{row['title']} ({row['pub_date']})", expanded=False):
                    st.markdown(f"**Título:** {row['title']}")
                    st.write(f"Data de publicação: {row['pub_date']}")
                    st.write(f"Link: {row['link']}")
                    st.write(f"Fonte: {row['feed_url']}")
                    st.write(f"Palavra-chave: {row['matched_keyword']}")
                    
                    # Se quiser exibir também as outras respostas de classificação:
                    st.write(f"2. Perspectiva positiva (inflação geral)? {row.get('2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral?', '')}")
                    st.write(f"3. Aborda especificamente inflação de alimentos? {row.get('3. O artigo aborda especificamente a inflação de alimentos?', '')}")
                    st.write(f"4. Perspectiva positiva (inflação alimentos)? {row.get('4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor?', '')}")

    else:
        st.error("Arquivo CSV de notícias não encontrado!")


# ======================
# 6) Rodapé
# ======================
footer_html = """
<style>
footer { visibility: hidden; }
.main .block-container { padding-bottom: 60px; }
.custom-footer {
    position: fixed; left: 0; bottom: 0; width: 100%;
    background-color: #f2f2f2; text-align: center;
    padding: 10px 0; font-size: 14px; color: #666;
}
.icon { width: 20px; height: 20px; vertical-align: middle; margin-right: 5px; border-radius: 4px; }
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
st.markdown(footer_html, unsafe_allow_html=True)
