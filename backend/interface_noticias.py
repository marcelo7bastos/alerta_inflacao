"""Componentes de busca e leitura das notícias no Streamlit."""

import pandas as pd
import streamlit as st

from .noticias import ALIMENTOS, CAMPOS_CLASSIFICACAO, chave_url, texto_resumo
from .services import get_feed_name


def somente_alimentos():
    tema = st.radio("Recorte", ("Inflação de alimentos", "Inflação em geral"), horizontal=True)
    return tema == "Inflação de alimentos"


def mostrar_noticias(noticias):
    quantidade = len(noticias)
    st.caption("1 notícia" if quantidade == 1 else f"{quantidade} notícias")
    if noticias.empty:
        st.info("Nenhuma notícia encontrada com os filtros selecionados.")
    for _, noticia in noticias.iterrows():
        data = noticia.get("data_local")
        data = data.strftime("%d/%m/%Y") if pd.notna(data) else "Sem data informada"
        with st.expander(f"{noticia['title']} · {data}"):
            st.caption(get_feed_name(noticia["feed_url"]))
            resumo = texto_resumo(noticia.get("description"))
            if resumo:
                st.write(resumo[:600])
            if noticia.get(ALIMENTOS) == "Sim":
                st.caption("Classificada como inflação de alimentos")
            queda_geral = noticia.get(CAMPOS_CLASSIFICACAO["queda_geral"])
            queda_alimentos = noticia.get(CAMPOS_CLASSIFICACAO["queda_alimentos"])
            if queda_geral in ("Sim", "Não"):
                st.caption(f"Perspectiva de queda da inflação geral · {queda_geral}")
            if queda_alimentos in ("Sim", "Não"):
                st.caption(f"Perspectiva de queda da inflação de alimentos · {queda_alimentos}")
            if chave_url(noticia.get("link")):
                st.link_button("Abrir notícia na fonte", noticia["link"])
