"""Coleta um lote para revisão editorial, sem gravar no histórico."""

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

from .atualiza_noticias import KEYWORDS_CSV, KEYWORDS_PADRAO, RSS_FEEDS
from .atualiza_noticias import load_keywords_from_csv, search_keywords_in_rss
from .noticias import HISTORICO_CSV as HISTORICO, chave_url


COLUNAS = (
    "titulo", "url", "data_publicacao", "feed", "termo_coleta",
    "situacao_url", "triagem", "indicio_no_titulo",
)
TERMOS_COLETIVOS = ("alimento", "alimentos", "alimentação e bebidas", "alimentação no domicílio")
TERMOS_PRECO = re.compile(r"\b(?:precos?|inflacao|ipca|encarec\w*|barate\w*)\b")


def normalizar_texto(texto):
    decomposto = unicodedata.normalize("NFKD", unescape(texto or "").casefold())
    return "".join(letra for letra in decomposto if not unicodedata.combining(letra))


def gerar_linhas(candidatas, urls_historico, produtos):
    termos = set(TERMOS_COLETIVOS)
    termos.update(produto.strip() for produto in produtos if produto and produto.strip())
    termos = sorted(termos, key=lambda termo: (-len(termo), termo))
    por_termo = {normalizar_texto(termo): termo for termo in termos}
    padrao_produto = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, por_termo)) + r")(?!\w)")
    urls_lote = set()

    for noticia in candidatas:
        chave = chave_url(noticia["link"])
        if not chave:
            situacao = "url_ausente_ou_invalida"
        elif chave in urls_historico:
            situacao = "ja_no_historico"
        elif chave in urls_lote:
            situacao = "repetida_no_lote"
        else:
            situacao = "nova"
            urls_lote.add(chave)

        titulo = normalizar_texto(noticia["title"])
        produto = padrao_produto.search(titulo)
        preco = TERMOS_PRECO.search(titulo)
        triagem = "priorizar_revisao" if produto and preco else "revisar_contexto"
        yield {
            "titulo": noticia["title"],
            "url": noticia["link"],
            "data_publicacao": noticia["pub_date"],
            "feed": noticia["feed_url"],
            "termo_coleta": noticia["matched_keyword"],
            "situacao_url": situacao,
            "triagem": triagem,
            "indicio_no_titulo": por_termo[produto.group()] if produto else "",
        }


def celula_csv(valor):
    texto = valor or ""
    if texto.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + texto
    return texto


def executar(diretorio_saida):
    with HISTORICO.open(encoding="utf-8-sig", newline="") as arquivo:
        urls_historico = {chave_url(linha["link"]) for linha in csv.DictReader(arquivo)}
    with Path(KEYWORDS_CSV).open(encoding="utf-8-sig", newline="") as arquivo:
        produtos = [linha["categoria_subitem"] for linha in csv.DictReader(arquivo)]

    relatorio_feeds = []
    candidatas = search_keywords_in_rss(
        RSS_FEEDS, [*KEYWORDS_PADRAO, *load_keywords_from_csv(KEYWORDS_CSV)], relatorio_feeds,
    )
    linhas = list(gerar_linhas(candidatas, urls_historico, produtos))
    diretorio_saida.mkdir(parents=True, exist_ok=True)
    with (diretorio_saida / "coleta-teste.csv").open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS, delimiter=";")
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({campo: celula_csv(valor) for campo, valor in linha.items()})

    feeds_ok = sum(feed["status"] == "ok" for feed in relatorio_feeds)
    resumo = {
        "executada_em_utc": datetime.now(timezone.utc).isoformat(),
        "feeds_ok": feeds_ok,
        "feeds": relatorio_feeds,
        "itens_lidos": sum(feed["itens"] for feed in relatorio_feeds),
        "candidatas": len(linhas),
        "por_situacao_url": dict(Counter(linha["situacao_url"] for linha in linhas)),
        "por_triagem": dict(Counter(linha["triagem"] for linha in linhas)),
    }
    com_indentacao = json.dumps(resumo, ensure_ascii=False, indent=2) + "\n"
    (diretorio_saida / "resumo.json").write_text(com_indentacao, encoding="utf-8")
    print(f"{feeds_ok}/{len(relatorio_feeds)} feeds lidos, {len(linhas)} candidatas. Saída em {diretorio_saida}.")
    return 0 if feeds_ok else 1


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--saida", required=True, type=Path, help="Pasta do CSV de revisão e do resumo do teste.")
    return executar(cli.parse_args().saida)


if __name__ == "__main__":
    raise SystemExit(main())
