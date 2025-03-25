# backend.py
import re
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from typing import List, Dict, Any

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