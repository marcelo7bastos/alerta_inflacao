import streamlit as st
import pandas as pd
import os
from backend.utils import render_footer

st.set_page_config(page_title="Histórico de Inflação", layout="wide")
st.title("Histórico de Inflação")

csv_filepath = "data/noticias/noticias.csv"

if os.path.exists(csv_filepath):
    # Lê o CSV forçando todas as colunas como string
    df = pd.read_csv(csv_filepath, dtype=str)

    # Filtra apenas notícias onde "1. O artigo aborda o tema da inflação?" é "Sim"
    col_inflacao = "1. O artigo aborda o tema da inflação?"
    df = df[df[col_inflacao] == "Sim"]

    # Conversão de datas e ordenação decrescente
    df["pub_date"] = pd.to_datetime(df["pub_date"], errors="coerce", utc=True)
    df["pub_date"] = df["pub_date"].dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)
    df = df.sort_values(by="pub_date", ascending=False)

    # Filtros de data (início e fim)
    min_date = df["pub_date"].min()
    max_date = df["pub_date"].max()
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
        mask = (df["pub_date"].dt.date >= start_date) & (df["pub_date"].dt.date <= end_date)
        df = df[mask]

    st.write(f"Exibindo {len(df)} notícias filtradas:")

    if len(df) == 0:
        st.warning("Nenhuma notícia encontrada nesse intervalo de datas.")
    else:
        for idx, row in df.iterrows():
            with st.expander(f"{row['title']} ({row['pub_date']})", expanded=False):
                st.markdown(f"**Título:** {row['title']}")
                st.write(f"Data de publicação: {row['pub_date']}")
                st.write(f"Link: {row['link']}")
                st.write(f"Fonte: {row['feed_url']}")
                st.write(f"Palavra-chave: {row['matched_keyword']}")
                st.write(f"2. Perspectiva positiva (inflação geral)? {row.get('2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral?', '')}")
                st.write(f"3. Aborda especificamente inflação de alimentos? {row.get('3. O artigo aborda especificamente a inflação de alimentos?', '')}")
                st.write(f"4. Perspectiva positiva (inflação alimentos)? {row.get('4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor?', '')}")
else:
    st.error("Arquivo CSV de notícias não encontrado!")


# Exibe o rodapé chamando a função
render_footer()