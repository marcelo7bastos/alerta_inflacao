import streamlit as st

from backend.interface_noticias import mostrar_noticias, somente_alimentos
from backend.noticias import filtrar_historico, ler_historico
from backend.utils import render_footer


st.set_page_config(page_title="Histórico de Notícias", layout="wide")
st.title("Histórico de Notícias")
st.caption("A cobertura depende das fontes consultadas. O período filtra pela data de publicação.")

noticias = filtrar_historico(ler_historico(), somente_alimentos())
datas = noticias["data_local"].dt.date.dropna()
if not datas.empty:
    inicio, fim = datas.min(), datas.max()
    periodo = st.date_input("Período de publicação", (inicio, fim), min_value=inicio, max_value=fim)
    if len(periodo) == 2:
        inicio, fim = periodo
        noticias = noticias[noticias["data_local"].dt.date.between(inicio, fim)]
    else:
        st.info("Escolha a data final do período.")

mostrar_noticias(noticias)
render_footer()
