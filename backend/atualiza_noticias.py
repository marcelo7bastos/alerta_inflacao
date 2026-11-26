"""Coleta RSS e atualiza o histórico de notícias."""

import argparse
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import requests
from dateutil import parser

if __package__:
    from . import noticias
else:
    import noticias


RSS_FEEDS = (
    'https://g1.globo.com/rss/g1/',
    'https://feeds.folha.uol.com.br/emcimadahora/rss091.xml',
    'https://www.bbc.com/portuguese/index.xml',
    'https://exame.com/feed/',
    'https://www.cartacapital.com.br/feed/',
    'https://www.istoedinheiro.com.br/feed/',
    'https://www.infomoney.com.br/feed/',
    'https://www.jovempan.com.br/feed',
    'https://economia.ig.com.br/rss.xml',
)
KEYWORDS_CSV = 'data/keywords/ipca_alimentacao_bebidas.csv'
KEYWORDS_PADRAO = ('inflação', 'preço dos alimentos', 'alta dos preços', 'IPCA', 'alimentação', 'bebidas')


def search_keywords_in_rss(feed_urls, keywords, informacoes_feeds=None):
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

    # Delimita por caracteres de palavra, inclusive quando o termo termina em pontuação.
    keyword_patterns = {
        keyword: re.compile(rf'(?<!\w){re.escape(keyword.lower())}(?!\w)', re.IGNORECASE)
        for keyword in keywords
    }

    for url in feed_urls:
        status = {"feed": url, "status": "falha_requisicao", "itens": 0, "candidatas": 0}
        if informacoes_feeds is not None:
            informacoes_feeds.append(status)
        print(f"Analisando feed: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            status["http"] = response.status_code
            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.content)
                except ET.ParseError as e:
                    status["status"] = "xml_invalido"
                    print(f"Erro de parse XML no feed {url}: {e}")
                    continue

                items = root.findall('.//item')
                if root.tag != "rss" and not items:
                    status["status"] = "formato_nao_suportado"
                    print(f"Formato de feed não suportado: {url}")
                    continue
                status.update(status="ok", itens=len(items))
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
                        except (ValueError, TypeError, OverflowError):
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
                            status["candidatas"] += 1
                            break  # evita duplicação
            else:
                status["status"] = "falha_http"
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


def coletar_noticias(informacoes_feeds=None):
    palavras = [*KEYWORDS_PADRAO, *load_keywords_from_csv(KEYWORDS_CSV)]
    return search_keywords_in_rss(RSS_FEEDS, palavras, informacoes_feeds)


def chave_noticia(noticia):
    return noticias.chave_url(noticia.get("link")) or (
        noticia.get("feed_url"), noticia.get("pub_date"), noticia.get("title"),
    )


def salvar_historico(caminho, linhas, colunas):
    with NamedTemporaryFile(dir=caminho.parent, delete=False) as arquivo:
        temporario = Path(arquivo.name)
    try:
        pd.DataFrame(linhas, columns=colunas).fillna("").to_csv(temporario, index=False, encoding="utf-8")
        os.replace(temporario, caminho)
    finally:
        temporario.unlink(missing_ok=True)


def atualizar_historico(caminho, candidatas, client=None):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    trava = caminho.with_name(f".{caminho.name}.lock")
    try:
        trava.touch(exist_ok=False)
    except FileExistsError as erro:
        raise RuntimeError(f"O histórico está bloqueado para atualização: {trava}") from erro

    try:
        historico = noticias.ler_historico(caminho)
        colunas = list(dict.fromkeys([
            *historico.columns, *noticias.COLUNAS_NOTICIA,
            *noticias.CAMPOS_CLASSIFICACAO.values(), "collected_at",
        ]))
        linhas = historico.to_dict("records")
        chaves = {chave_noticia(noticia) for noticia in linhas}
        coletada_em = datetime.now(timezone.utc).isoformat()
        adicionadas = 0
        for noticia in candidatas:
            if not noticia.get("title"):
                continue
            chave = chave_noticia(noticia)
            if chave not in chaves:
                linhas.append({**noticia, "collected_at": coletada_em})
                chaves.add(chave)
                adicionadas += 1

        classificadas = 0
        pendentes = 0
        for noticia in linhas:
            if not noticias.tem_classificacao(noticia):
                classificacao = None
                if client:
                    try:
                        classificacao = noticias.classificar_artigo(noticia, client)
                    except noticias.ClassificacaoIndisponivel as erro:
                        print(f"{erro}. As notícias restantes ficarão pendentes.")
                        client = None
                if classificacao:
                    noticia.update(classificacao)
                    classificadas += 1
                else:
                    pendentes += 1

        if adicionadas or classificadas:
            salvar_historico(caminho, linhas, colunas)
        return adicionadas, classificadas, pendentes
    finally:
        trava.unlink()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--historico", type=Path, default=noticias.HISTORICO_CSV)
    cli.add_argument("--somente-coleta", action="store_true", help="Guardar candidatas para classificação posterior.")
    args = cli.parse_args()

    client = None
    if not args.somente_coleta:
        from dotenv import load_dotenv

        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            cli.error("Configure OPENAI_API_KEY ou use --somente-coleta para guardar notícias pendentes.")
        client = noticias.criar_cliente_openai()

    fontes = []
    candidatas = coletar_noticias(fontes)
    try:
        novas, classificadas, pendentes = atualizar_historico(args.historico, candidatas, client)
    except RuntimeError as erro:
        cli.exit(1, f"{erro}\n")
    quantas_ok = sum(fonte["status"] == "ok" for fonte in fontes)
    print(f"{quantas_ok}/{len(fontes)} feeds lidos, {novas} novas, {classificadas} classificadas, {pendentes} pendentes.")
    return 0 if quantas_ok and (client is None or not pendentes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
