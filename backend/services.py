"""Apresentação de veículos e nuvem de palavras do Streamlit."""

import os
import string
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from PIL import Image
from wordcloud import WordCloud

from .noticias import datas_publicacao


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


def carregar_stopwords(caminho: str) -> set:
    """
    Carrega as stopwords de um arquivo, onde cada linha contém uma palavra.
    """
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            stopwords_lista = [linha.strip() for linha in f if linha.strip()]
        return set(stopwords_lista)
    except Exception as e:
        raise ValueError("Erro ao carregar stopwords do arquivo: " + str(e))


def gerar_nuvem_palavras(
    csv_path: str,
    stopwords_path: str = None,
    mask_path: str = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> WordCloud:
    '''
    Le o CSV, filtra os artigos que abordam a inflacao, processa os textos
    e gera uma WordCloud estilizada.

    Parametros:
    - csv_path: caminho para o CSV de noticias.
    - stopwords_path: caminho para um arquivo de stopwords customizado (opcional).
    - mask_path: caminho para uma imagem que servira de mascara para a nuvem (opcional).
    - start_date: data inicial para filtrar as noticias (opcional).
    - end_date: data final para filtrar as noticias (opcional).

    Retorna:
    - Um objeto WordCloud.
    '''
    df = pd.read_csv(csv_path, dtype=str)

    if start_date or end_date:
        if "pub_date" not in df.columns:
            raise ValueError("Coluna 'pub_date' nao encontrada no CSV.")
        pub_dates = datas_publicacao(df["pub_date"]).dt.date
        mask_datas = pub_dates.notna()
        if start_date:
            mask_datas &= pub_dates >= start_date
        if end_date:
            mask_datas &= pub_dates <= end_date
        df = df[mask_datas]

    if df.empty:
        raise ValueError("Nenhuma noticia encontrada para o periodo selecionado.")

    coluna_inflacao = next(
        (col for col in df.columns if col.lower().startswith("1. o artigo aborda o tema da infl")),
        None
    )

    if not coluna_inflacao:
        raise ValueError("Coluna relacionada ao tema da inflacao nao encontrada no CSV.")

    df_filtrado = df[df[coluna_inflacao] == "Sim"]

    if df_filtrado.empty:
        raise ValueError("Nenhuma noticia relevante encontrada para o periodo selecionado.")

    textos = df_filtrado["title"].tolist()
    if "description" in df_filtrado.columns:
        textos += df_filtrado["description"].dropna().tolist()

    texto_completo = " ".join(textos).lower()
    texto_sem_pontuacao = texto_completo.translate(str.maketrans("", "", string.punctuation))

    if stopwords_path and os.path.exists(stopwords_path):
        stopwords_pt = carregar_stopwords(stopwords_path)
    else:
        stopwords_pt = set(stopwords.words('portuguese'))

    palavras_filtradas = [palavra for palavra in texto_sem_pontuacao.split() if palavra not in stopwords_pt]
    texto_final = " ".join(palavras_filtradas)

    mask = None
    if mask_path and os.path.exists(mask_path):
        mask = np.array(Image.open(mask_path))

    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color='white',
        colormap='Reds',
        mask=mask,
        contour_width=1,
        contour_color='steelblue',
        collocations=False
    ).generate(texto_final)

    return wordcloud
