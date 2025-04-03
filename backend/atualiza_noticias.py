#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Arquivo: atualiza_noticias.py
Descrição: Coleta novas notícias a partir de feeds RSS, atualiza o arquivo CSV com as notícias encontradas
           (evitando duplicatas) e, em seguida, classifica as notícias que ainda não foram avaliadas pela IA.
"""

##### IMPORTS GERAIS #####
import os
import re
import time
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime

##### CONFIGURAÇÃO DA API OPENAI #####
from dotenv import load_dotenv
import openai

# Carrega as variáveis definidas em .env
load_dotenv()

# Obtém a chave da API da OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if api_key is None:
    raise ValueError("A chave da API da OpenAI não foi encontrada. Verifique seu arquivo .env.")

# Inicializa o cliente da OpenAI
client = openai.OpenAI(api_key=api_key)

import re
import requests
import xml.etree.ElementTree as ET
from dateutil import parser  # Biblioteca que facilita o parse de datas em formatos variados

def search_keywords_in_rss(feed_urls, keywords):
    """
    Busca notícias nos feeds RSS que contenham as palavras-chave especificadas.
    
    Parâmetros:
      feed_urls (list): Lista de URLs de feeds RSS.
      keywords (list): Lista de palavras-chave a serem procuradas.
      
    Retorna:
      matches (list): Lista de dicionários contendo os dados dos artigos encontrados,
                      com 'pub_date' em formato padronizado (ISO 8601).
    """
    matches = []
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; RSSBot/1.0)'}

    # Pré-compila expressões regulares para cada keyword
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
                print(f"Foram encontrados {len(items)} itens no feed.")

                for item in items:
                    title = item.find('title').text if item.find('title') is not None else ""
                    description = item.find('description').text if item.find('description') is not None else ""
                    link = item.find('link').text if item.find('link') is not None else ""
                    raw_pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""

                    # Tenta converter a data para formato ISO-8601
                    if raw_pub_date:
                        try:
                            dt_parsed = parser.parse(raw_pub_date)
                            pub_date = dt_parsed.isoformat()  # Ex: "2025-03-31T16:30:00-03:00"
                        except (ValueError, TypeError):
                            # Se não conseguir fazer o parse, mantemos o texto original
                            pub_date = raw_pub_date
                    else:
                        pub_date = ""

                    # Checagem de keywords
                    content = f"{title} {description}".lower()
                    for keyword, pattern in keyword_patterns.items():
                        if pattern.search(content):
                            matches.append({
                                'title': title,
                                'description': description,
                                'link': link,
                                'pub_date': pub_date,      # <-- já padronizado
                                'feed_url': url,
                                'matched_keyword': keyword
                            })
                            break  # evita duplicação
            else:
                print(f"Falha ao acessar feed: {url}, status: {response.status_code}")
        except requests.RequestException as e:
            print(f"Erro ao tentar acessar {url}: {e}")

    return matches


##### FUNÇÃO: Carregar keywords adicionais a partir de um CSV #####
def load_keywords_from_csv(csv_filepath):
    """
    Carrega e retorna uma lista de keywords adicionais a partir de um CSV.
    O CSV deve conter as colunas: categoria_grupo, categoria_subgrupo, categoria_item, categoria_subitem.
    """
    df = pd.read_csv(csv_filepath)
    # Remove duplicatas e valores ausentes
    keywords_adicionais = pd.unique(df[['categoria_grupo', 'categoria_subgrupo', 'categoria_item', 'categoria_subitem']].values.ravel())
    keywords_adicionais = [str(keyword).strip() for keyword in keywords_adicionais if pd.notna(keyword)]
    return keywords_adicionais

##### FUNÇÃO: Atualizar CSV com novas notícias #####
def update_noticias_csv(resultados):
    """
    Atualiza o arquivo CSV com novas notícias a partir da lista 'resultados', evitando duplicatas
    e adicionando colunas para a classificação.
    A chave de verificação é composta por (feed_url, pub_date, title).
    """
    # Define o caminho relativo do arquivo CSV
    csv_filepath = os.path.join('data', 'noticias', 'noticias.csv')
    # Garante que a pasta exista
    os.makedirs(os.path.dirname(csv_filepath), exist_ok=True)
    
    # Colunas de classificação a serem incorporadas
    classification_columns = [
        "1. O artigo aborda o tema da inflação?",
        "2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral?",
        "3. O artigo aborda especificamente a inflação de alimentos?",
        "4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor?"
    ]
    
    # Carrega ou cria o DataFrame
    if os.path.exists(csv_filepath):
        df = pd.read_csv(csv_filepath)
    else:
        df = pd.DataFrame(columns=['title', 'description', 'link', 'pub_date', 'feed_url', 'matched_keyword'] + classification_columns)
    
    # Garante que as colunas de classificação existam
    for col in classification_columns:
        if col not in df.columns:
            df[col] = ""
    
    # Cria um conjunto com a chave composta das notícias já existentes
    existing_keys = set(df.apply(lambda row: (row['feed_url'], row['pub_date'], row['title']), axis=1))
    new_entries = []
    
    for noticia in resultados:
        composite_key = (noticia['feed_url'], noticia['pub_date'], noticia['title'])
        if composite_key not in existing_keys:
            # Inicializa as colunas de classificação com valor vazio
            for col in classification_columns:
                noticia[col] = ""
            new_entries.append(noticia)
            existing_keys.add(composite_key)
        else:
            print(f"Notícia já cadastrada: {noticia['title']}")
    
    if new_entries:
        df_new = pd.DataFrame(new_entries)
        df = pd.concat([df, df_new], ignore_index=True)
        df.to_csv(csv_filepath, index=False)
        print(f"{len(new_entries)} novas notícias adicionadas.")
    else:
        print("Nenhuma nova notícia foi encontrada para adicionar.")
    
    return df

##### FUNÇÃO: Classificar artigo via API da OpenAI #####
def classificar_artigo(artigo):
    """
    Recebe um dicionário com os dados do artigo, invoca a API da OpenAI para classificação e retorna o artigo atualizado.
    """
    system_message = (
        "Como economista especializado em inflação de alimentos, sua tarefa é analisar artigos de jornais e classificar "
        "conforme as seguintes perguntas:\n"
        "1. O artigo aborda o tema da inflação? (Responda com 'Sim' ou 'Não')\n"
           "- Se 'Sim':\n"
           "2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral? "
           "(Responda com 'Sim', 'Não' ou 'Não se aplica')\n"
        "3. O artigo aborda especificamente a inflação de alimentos? (Responda com 'Sim', 'Não' ou 'Não se aplica')\n"
           "- Se 'Sim':\n"
           "4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor? "
           "(Responda com 'Sim', 'Não' ou 'Não se aplica')\n"
        "Por favor, utilize apenas as palavras 'Sim', 'Não' ou 'Não se aplica' para responder a cada pergunta. "
        "Não é necessário justificar as respostas.\n"
        "Em caso de informações insuficientes, responda 'Não'.\n"
        "Retorne a resposta com cada linha correspondendo a uma pergunta."
    )
    
    user_message = f"Classifique:\nTítulo: {artigo['title']}\n"
    
    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0
        )
    except Exception as e:
        print("Erro ao chamar a API:", e)
        return {}
    
    conteudo = resposta.choices[0].message.content
    
    # Mapeia as perguntas para as chaves desejadas
    perguntas = {
        "1. O artigo aborda o tema da inflação?": None,
        "2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral?": None,
        "3. O artigo aborda especificamente a inflação de alimentos?": None,
        "4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor?": None
    }
    
    for i, linha in enumerate(conteudo.strip().splitlines(), start=1):
        resposta_linha = linha.split('. ', 1)[-1].strip()
        chave_pergunta = list(perguntas.keys())[i - 1]
        perguntas[chave_pergunta] = resposta_linha
    
    artigo.update(perguntas)
    return artigo

##### FUNÇÃO: Processar classificação de artigos no CSV #####
def processar_classificacao_csv():
    """
    Carrega o CSV 'data/noticias/noticias.csv', filtra os artigos não classificados (baseado na coluna 
    "1. O artigo aborda o tema da inflação?"), classifica cada artigo via API e atualiza o CSV.
    """
    csv_filepath = os.path.join('data', 'noticias', 'noticias.csv')
    
    if not os.path.exists(csv_filepath):
        print("Arquivo CSV não encontrado:", csv_filepath)
        return
    
    # Lê o CSV forçando todas as colunas como string
    df = pd.read_csv(csv_filepath, dtype=str)
    
    col_classificacao = [
        "1. O artigo aborda o tema da inflação?",
        "2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral?",
        "3. O artigo aborda especificamente a inflação de alimentos?",
        "4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor?"
    ]
    
    # Garante que as colunas de classificação existam e preenche valores ausentes
    for col in col_classificacao:
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("").astype(str)
    
    # Itera apenas sobre os artigos ainda não classificados
    for index, row in df.iterrows():
        if row[col_classificacao[0]] == "":
            artigo = row.to_dict()
            print(f"Classificando artigo: {artigo['title']}")
            artigo_classificado = classificar_artigo(artigo)
            
            for col in col_classificacao:
                valor = artigo_classificado.get(col, "")
                df.at[index, col] = str(valor)
            
            # Imprime o resultado da classificação para o artigo atual
            print(f"Artigo '{artigo['title']}' classificado como:")
            for col in col_classificacao:
                print(f"  {col}: {df.at[index, col]}")
            
            time.sleep(1)
    
    df.to_csv(csv_filepath, index=False, encoding='utf-8')
    print("Classificação atualizada no arquivo CSV.")

##### EXECUÇÃO PRINCIPAL #####
if __name__ == '__main__':
    # Lista de feeds RSS
    rss_feed_url = [
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
    print("Feeds RSS:", rss_feed_url)
    
    # Carrega keywords adicionais a partir do CSV
    keywords_csv = 'data/keywords/ipca_alimentacao_bebidas.csv'
    keywords_adicionais = load_keywords_from_csv(keywords_csv)
    
    # Define as keywords já existentes e combina com as adicionais
    keywords = ['inflação', 'preço dos alimentos', 'alta dos preços', 'IPCA', 'alimentação', 'bebidas']
    keywords.extend(keywords_adicionais)
    print("Palavras-chave utilizadas:", keywords)
    
    # Busca novas notícias e atualiza o CSV
    resultados = search_keywords_in_rss(rss_feed_url, keywords)
    df_atualizado = update_noticias_csv(resultados)
    
    # Processa a classificação dos artigos que ainda não foram avaliados pela IA
    processar_classificacao_csv()
