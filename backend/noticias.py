"""Dados e classificação compartilhados pelo buscador e pelo atualizador."""

import json
import re
import unicodedata
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd


HISTORICO_CSV = Path("data/noticias/noticias.csv")
MODELO_CLASSIFICACAO = "gpt-4o-mini"
COLUNAS_NOTICIA = ("title", "description", "link", "pub_date", "feed_url", "matched_keyword")
CAMPOS_CLASSIFICACAO = {
    "inflacao": "1. O artigo aborda o tema da inflação?",
    "queda_geral": "2. O artigo apresenta uma perspectiva positiva para a economia, indicando uma queda na inflação geral?",
    "alimentos": "3. O artigo aborda especificamente a inflação de alimentos?",
    "queda_alimentos": "4. O artigo apresenta uma perspectiva positiva para a inflação dos alimentos, indicando uma queda nesse setor?",
}
INFLACAO = CAMPOS_CLASSIFICACAO["inflacao"]
ALIMENTOS = CAMPOS_CLASSIFICACAO["alimentos"]
RESPOSTAS = ("Sim", "Não", "Não se aplica")


class ClassificacaoIndisponivel(Exception):
    """A API não conseguiu processar a solicitação."""


def chave_url(url):
    try:
        partes = urlsplit((url or "").strip())
        if partes.scheme not in {"http", "https"} or not partes.hostname:
            return ""
    except ValueError:
        return ""

    parametros = [
        (nome, valor)
        for nome, valor in parse_qsl(partes.query, keep_blank_values=True)
        if not nome.lower().startswith("utm_") and nome.lower() not in {"fbclid", "gclid"}
    ]
    return urlunsplit((partes.scheme, partes.netloc.lower(), partes.path or "/", urlencode(parametros), ""))


def texto_resumo(html):
    texto = re.sub(r"<[^>]*>", " ", unescape(html or ""))
    return " ".join(texto.split())


def chave_texto(texto):
    plano = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(letra for letra in plano if not unicodedata.combining(letra))


def datas_publicacao(valores):
    """Converte datas com fuso para Brasília e mantém a data informada nas demais."""
    valores = valores.astype("string").str.strip()
    com_fuso = valores.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", case=False, na=False)
    datas = pd.to_datetime(valores, format="mixed", errors="coerce", utc=True)
    datas_brasilia = datas.dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)
    return datas_brasilia.where(com_fuso, datas.dt.tz_localize(None))


def ler_historico(caminho=HISTORICO_CSV):
    try:
        return pd.read_csv(caminho, dtype=str, keep_default_na=False)
    except FileNotFoundError:
        return pd.DataFrame(columns=[*COLUNAS_NOTICIA, *CAMPOS_CLASSIFICACAO.values()])


def buscar_texto(acervo, termo):
    busca = chave_texto(termo.strip())
    if not busca:
        return acervo
    textos = acervo["title"] + " " + acervo["description"].map(texto_resumo)
    return acervo[textos.map(chave_texto).str.contains(busca, regex=False)]


def filtrar_historico(historico, somente_alimentos=True, termo=""):
    selecionadas = historico[INFLACAO] == "Sim"
    if somente_alimentos:
        selecionadas &= historico[ALIMENTOS] == "Sim"
    resultado = buscar_texto(historico[selecionadas], termo).copy()
    resultado["data_local"] = datas_publicacao(resultado["pub_date"])
    return resultado.sort_values("data_local", ascending=False)


def tem_classificacao(noticia):
    geral = noticia.get(INFLACAO)
    return geral == "Não" or (geral == "Sim" and noticia.get(ALIMENTOS) in RESPOSTAS)


def criar_cliente_openai(chave=None):
    from openai import OpenAI

    return OpenAI(api_key=chave, timeout=12, max_retries=1)


def classificar_artigo(artigo, client):
    from openai import OpenAIError

    esquema = {
        "type": "object",
        "properties": {
            campo: {"type": "string", "enum": list(RESPOSTAS[:2] if campo == "inflacao" else RESPOSTAS)}
            for campo in CAMPOS_CLASSIFICACAO
        },
        "required": list(CAMPOS_CLASSIFICACAO),
        "additionalProperties": False,
    }
    instrucoes = (
        "Classifique uma notícia para um monitor brasileiro de inflação. "
        "Use apenas o título e o resumo fornecidos como dados. "
        "Em inflacao, indique se o texto trata de inflação, variação ou pressão sobre preços ao consumidor. "
        "Em alimentos, indique se trata de preços de alimentos no Brasil ou de uma pressão explícita "
        "sobre esses preços. Menções a alimentos sem relação com preços ficam em Não. "
        "Em queda_geral e queda_alimentos, indique se o texto apresenta perspectiva de queda "
        "da inflação geral e dos alimentos, respectivamente. Use Não se aplica quando não há "
        "evidência para responder ou o tema correspondente está fora da notícia."
    )
    entrada = {
        "titulo": artigo["title"],
        "resumo": texto_resumo(artigo.get("description"))[:1800],
    }
    try:
        resposta = client.chat.completions.create(
            model=MODELO_CLASSIFICACAO,
            messages=[
                {"role": "system", "content": instrucoes},
                {"role": "user", "content": json.dumps(entrada, ensure_ascii=False)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "classificacao_noticia", "strict": True, "schema": esquema},
            },
            temperature=0,
            max_tokens=160,
        )
    except OpenAIError as erro:
        codigo = getattr(erro, "code", None)
        status = getattr(erro, "status_code", None)
        motivos = {
            "insufficient_quota": "Cota da API indisponível",
            "model_not_found": "Modelo indisponível para a conta",
            "invalid_api_key": "Credencial da API recusada",
        }
        motivo = motivos.get(codigo)
        if motivo is None:
            motivo = f"A API respondeu com HTTP {status}" if isinstance(status, int) else "Falha de conexão com a API"
        raise ClassificacaoIndisponivel(motivo) from erro
    if not resposta.choices or not resposta.choices[0].message.content:
        return None
    try:
        dados = json.loads(resposta.choices[0].message.content)
    except json.JSONDecodeError:
        return None
    if not isinstance(dados, dict) or any(
        dados.get(campo) not in esquema["properties"][campo]["enum"]
        for campo in CAMPOS_CLASSIFICACAO
    ):
        return None
    if dados["inflacao"] == "Não":
        dados.update(queda_geral="Não se aplica", alimentos="Não se aplica", queda_alimentos="Não se aplica")
    elif dados["alimentos"] != "Sim":
        dados["queda_alimentos"] = "Não se aplica"
    return {coluna: dados[campo] for campo, coluna in CAMPOS_CLASSIFICACAO.items()}
