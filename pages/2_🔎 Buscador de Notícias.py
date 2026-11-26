import os

import pandas as pd
import streamlit as st

from backend.atualiza_noticias import chave_noticia, coletar_noticias
from backend.interface_noticias import mostrar_noticias, somente_alimentos
from backend.noticias import (
    CAMPOS_CLASSIFICACAO,
    COLUNAS_NOTICIA,
    HISTORICO_CSV,
    ClassificacaoIndisponivel,
    buscar_texto,
    classificar_artigo,
    criar_cliente_openai,
    datas_publicacao,
    filtrar_historico,
    ler_historico,
    tem_classificacao,
)
from backend.utils import render_footer


@st.cache_data(ttl=600, show_spinner=False)
def consultar_feeds(versao_historico):
    historico = ler_historico()
    classificados = {
        chave_noticia(noticia): noticia
        for noticia in historico.to_dict("records")
        if tem_classificacao(noticia)
    }
    try:
        chave = st.secrets["openai"]["api_key"]
    except (KeyError, FileNotFoundError):
        chave = os.getenv("OPENAI_API_KEY")
    cliente = criar_cliente_openai(chave) if chave else None

    fontes = []
    candidatas = coletar_noticias(fontes)
    resultado = {}
    for noticia in candidatas:
        if not noticia["title"]:
            continue
        identificador = chave_noticia(noticia)
        if identificador in resultado:
            continue
        anterior = classificados.get(identificador)
        if anterior:
            noticia.update({coluna: anterior.get(coluna, "") for coluna in CAMPOS_CLASSIFICACAO.values()})
        elif cliente:
            try:
                noticia.update(classificar_artigo(noticia, cliente) or {})
            except ClassificacaoIndisponivel:
                cliente = None
        resultado[identificador] = noticia
    colunas = [*COLUNAS_NOTICIA, *CAMPOS_CLASSIFICACAO.values()]
    return pd.DataFrame(resultado.values(), columns=colunas).fillna(""), fontes


st.set_page_config(page_title="Buscador de Notícias", layout="wide")
st.title("Buscador de Notícias")

alimentos = somente_alimentos()
termo = st.text_input("Buscar no título ou no resumo", placeholder="Ex.: arroz, estiagem, supermercado")
historico_tab, feeds_tab = st.tabs(("Acervo publicado", "Feeds RSS"))

with historico_tab:
    mostrar_noticias(filtrar_historico(ler_historico(), alimentos, termo))

with feeds_tab:
    if st.button("Consultar feeds agora"):
        try:
            versao = HISTORICO_CSV.stat().st_mtime_ns
        except FileNotFoundError:
            versao = None
        with st.spinner("Consultando fontes e classificando os itens novos…"):
            st.session_state["consulta_rss"] = consultar_feeds(versao)

    if "consulta_rss" in st.session_state:
        resultados, fontes = st.session_state["consulta_rss"]
        indisponiveis = [fonte["feed"] for fonte in fontes if fonte["status"] != "ok"]
        if indisponiveis:
            st.warning("Fontes indisponíveis nesta consulta: " + ", ".join(indisponiveis))
        sem_rotulo = ~resultados.apply(tem_classificacao, axis=1).astype(bool)
        pendentes = buscar_texto(resultados[sem_rotulo], termo).copy()
        if not pendentes.empty:
            st.info(f"{len(pendentes)} candidatas aguardam classificação.")
        mostrar_noticias(filtrar_historico(resultados, alimentos, termo))
        if not pendentes.empty and st.toggle("Mostrar candidatas pendentes"):
            pendentes["data_local"] = datas_publicacao(pendentes["pub_date"])
            mostrar_noticias(pendentes.sort_values("data_local", ascending=False))

render_footer()
