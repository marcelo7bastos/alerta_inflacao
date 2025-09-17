# backend.py
import re
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import date
from typing import List, Dict, Any, Optional
import streamlit as st

### Funcionamento da API da OpenAI
import openai
# Atribui a chave de API dos secrets do Streamlit
openai.api_key = st.secrets["openai"]["api_key"]
client = openai
###


def load_keywords_from_csv(csv_filepath: str) -> List[str]:
    """
    Lê o arquivo CSV com as colunas de palavras-chave e retorna uma lista única.
    O CSV deve conter as colunas: 'categoria_grupo', 'categoria_subgrupo', 'categoria_item', 'categoria_subitem'.
    """
    df = pd.read_csv(csv_filepath)
    keywords_adicionais = pd.unique(
        df[['categoria_grupo', 'categoria_subgrupo', 'categoria_item', 'categoria_subitem']].values.ravel()
    )
    keywords_adicionais = [str(keyword).strip() for keyword in keywords_adicionais if pd.notna(keyword)]
    return keywords_adicionais

def get_default_keywords() -> List[str]:
    """
    Retorna uma lista padrão de palavras-chave.
    """
    return ['inflação', 'preço dos alimentos', 'alta dos preços', 'IPCA', 'alimentação', 'bebidas']

def search_keywords_in_rss(feed_urls: List[str], keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Busca notícias em feeds RSS que contenham as palavras-chave especificadas.

    Args:
        feed_urls: Lista de URLs de feeds RSS.
        keywords: Lista de palavras-chave para a busca.

    Returns:
        Uma lista de dicionários com os dados das notícias encontradas.
    """
    matches = []
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; RSSBot/1.0)'}

    # Pré-compila as expressões regulares com boundary \b para cada keyword
    keyword_patterns = {
        keyword: re.compile(rf'\b{re.escape(keyword.lower())}\b', re.IGNORECASE)
        for keyword in keywords
    }

    for url in feed_urls:
        print(f"Analisando feed: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.content)
                except ET.ParseError as e:
                    print(f"Erro de parse XML no feed {url}: {e}")
                    continue

                items = root.findall('.//item')
                print(f"Foram encontrados {len(items)} itens no feed {url}.")

                for item in items:
                    title = item.find('title').text if item.find('title') is not None else ""
                    description = item.find('description').text if item.find('description') is not None else ""
                    link = item.find('link').text if item.find('link') is not None else ""
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    content = f"{title} {description}".lower()

                    for keyword, pattern in keyword_patterns.items():
                        if pattern.search(content):
                            matches.append({
                                'title': title,
                                'description': description,
                                'link': link,
                                'pub_date': pub_date,
                                'feed_url': url,
                                'matched_keyword': keyword
                            })
                            break  # Evita duplicação se mais de uma keyword casar
            else:
                print(f"Falha ao acessar feed: {url}, status: {response.status_code}")
        except requests.RequestException as e:
            print(f"Erro ao tentar acessar {url}: {e}")

    return matches



# Usa a IA para Aprimorar o Resultado da Busca
def classificar_artigo(artigo):
    """
    Função que recebe um dicionário com os dados do artigo e chama a API da OpenAI para classificar.
    
    Parâmetros do artigo (dicionário):
      - title: título do artigo
      - description: descrição do artigo
      - link: link do artigo
      - feed_url: fonte do artigo
      - pub_date: data de publicação
      - matched_keyword: palavra-chave que originou o artigo
      
    Retorna:
      - O dicionário do artigo atualizado com as classificações extraídas da resposta da API.
    """
    # Mensagem do sistema com as instruções de classificação
    system_message = (
        "Como economista especializado em inflação de alimentos, sua tarefa é analisar artigos de jornais e classificá-los conforme as seguintes perguntas:\n"
        "1. O artigo aborda o tema da inflação? (Responda com 'Sim' ou 'Não')\n"
           "- Se 'Sim':\n"
           "2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral? (Responda com 'Sim', 'Não' ou 'Não se aplica')\n"
           "3. O artigo aborda especificamente a inflação de alimentos? (Responda com 'Sim', 'Não' ou 'Não se aplica')\n"
              "- Se 'Sim':\n"
              "4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor? (Responda com 'Sim', 'Não' ou 'Não se aplica')\n"
        "Por favor, utilize apenas as palavras 'Sim', 'Não' ou 'Não se aplica' para responder a cada pergunta. Não é necessário justificar as respostas. \n"
        "Em caso de informações insuficientes no artigo para responder a alguma pergunta, responda 'Não'. \n"
        "Utilize apenas texto puro, sem aplicar estilos de formatação."
    )
    
    # Mensagem do usuário com os dados do artigo
    # user_message = (
    #     f"Classifique:\n"
    #     f"Título: {artigo['title']}\n"
    #     f"Descrição: {artigo['description']}\n"
    #     f"Link: {artigo['link']}\n"
    #     f"Fonte: {artigo['feed_url']}\n"
    #     f"Data de publicação: {artigo['pub_date']}\n"
    #     f"Palavra-chave: {artigo['matched_keyword']}"
    # )
    user_message = (
        f"Classifique:\n"
        f"Título: {artigo['title']}\n"
    )

    
    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0  # para respostas mais determinísticas
        )
        #print("Resposta da API:", resposta)
    except Exception as e:
        print("Erro ao chamar a API:", e)
        return {}
    
    # Extrai o conteúdo da resposta
    conteudo = resposta.choices[0].message.content
    #print("Conteúdo da resposta:", conteudo)
    
    # Mapeamento das perguntas para suas respectivas chaves
    perguntas = {
        "1. O artigo aborda o tema da inflação?": None,
        "2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral?": None,
        "3. O artigo aborda especificamente a inflação de alimentos?": None,
        "4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor?": None
    }
    
    # Divide o conteúdo da resposta em linhas e preenche o dicionário de perguntas com as respostas correspondentes
    for i, linha in enumerate(conteudo.strip().splitlines(), start=1):
        resposta_linha = linha.split('. ', 1)[-1].strip()
        chave_pergunta = list(perguntas.keys())[i - 1]
        perguntas[chave_pergunta] = resposta_linha
    
    #imprimir o resultado
    print("Respostas:", perguntas)        
    
    # Apensa os resultados (as classificações) ao dicionário do artigo
    artigo.update(perguntas)
    
    # Retorna apenas o dicionário do artigo, já atualizado com as classificações
    return artigo


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



##### Nuvem de palavras #####
import pandas as pd
import string
from wordcloud import WordCloud
import nltk
from nltk.corpus import stopwords
import os

# Se ainda não baixou as stopwords do NLTK, descomente a linha abaixo:
# nltk.download('stopwords')

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

import pandas as pd
import string
from wordcloud import WordCloud
import nltk
from nltk.corpus import stopwords
import numpy as np
from PIL import Image


# Stopwords padrão do NLTK para o português com complementos

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
        pub_dates = pd.to_datetime(df["pub_date"], errors='coerce', utc=True).dt.date
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








##### Nuvem de palavras #####
# ======================
