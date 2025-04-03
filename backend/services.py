# backend.py
import re
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from typing import List, Dict, Any

### Funcionamento da API da OpenAI
import openai
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

