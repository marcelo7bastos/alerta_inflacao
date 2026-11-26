import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from backend import coleta_teste


class ColetaTeste(unittest.TestCase):
    def test_dicionario_preserva_subitens(self):
        with Path(coleta_teste.KEYWORDS_CSV).open(encoding="utf-8-sig", newline="") as arquivo:
            linhas = list(csv.DictReader(arquivo))

        self.assertTrue(linhas)
        self.assertTrue(all(None not in linha and all(linha.values()) for linha in linhas))
        subitens = {linha["categoria_subitem"] for linha in linhas}
        self.assertTrue({"Arroz", "Fava", "Feijão - branco"} <= subitens)

    def test_coleta_usa_dicionario_e_preserva_historico(self):
        rss = b"""<rss><channel>
            <item><title>Preco do arroz sobe</title>
                <link>https://example.com/arroz?utm_source=teste&amp;id=1</link></item>
            <item><title>Preco do arroz sobe</title>
                <link>https://example.com/arroz?id=1#noticia</link></item>
            <item><title>Fed comenta inflacao</title><description>IPCA</description>
                <link>https://example.com/fed</link></item>
        </channel></rss>"""
        # O RSS pode repetir links e uma fonte pode responder com erro.
        respostas = [
            SimpleNamespace(status_code=200, content=rss),
            SimpleNamespace(status_code=503, content=b""),
        ]
        feeds = ("https://example.com/rss", "https://example.com/rss2")
        with TemporaryDirectory() as pasta:
            saida = Path(pasta)
            acervo = saida / "noticias.csv"
            acervo.write_text("link\nhttps://example.com/fed?fbclid=1\n", encoding="utf-8")
            antes = acervo.read_bytes()
            with (
                patch.object(coleta_teste, "RSS_FEEDS", feeds),
                patch.object(coleta_teste, "HISTORICO", acervo),
                patch("backend.atualiza_noticias.requests.get", side_effect=respostas),
            ):
                self.assertEqual(coleta_teste.executar(saida), 0)
            self.assertEqual(acervo.read_bytes(), antes)

            with (saida / "coleta-teste.csv").open(encoding="utf-8-sig", newline="") as arq:
                linhas = list(csv.DictReader(arq))
            resumo = json.loads((saida / "resumo.json").read_text(encoding="utf-8"))

        self.assertEqual([linha["situacao_url"] for linha in linhas], [
            "nova", "repetida_no_lote", "ja_no_historico",
        ])
        self.assertEqual([linha["triagem"] for linha in linhas], [
            "priorizar_revisao", "priorizar_revisao", "revisar_contexto",
        ])
        self.assertEqual([fonte["status"] for fonte in resumo["feeds"]], ["ok", "falha_http"])
        self.assertEqual(resumo["candidatas"], 3)


if __name__ == "__main__":
    unittest.main()
