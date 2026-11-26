import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pandas as pd
from openai import OpenAIError

from backend import noticias
from backend.atualiza_noticias import atualizar_historico


class NoticiasTeste(unittest.TestCase):
    def test_busca_no_acervo_preserva_datas_mistas(self):
        acervo = pd.DataFrame([
            {
                "title": "Preços do açúcar", "description": "Consumo",
                "pub_date": "2025-03-31T01:10:00+00:00",
                noticias.INFLACAO: "Sim", noticias.ALIMENTOS: "Sim",
            },
            {
                "title": "Açúcar no IPCA", "description": "",
                "pub_date": "2025-03-31T01:10:00",
                noticias.INFLACAO: "Sim", noticias.ALIMENTOS: "Sim",
            },
            {
                "title": "Inflação geral", "description": "Menção ao açúcar",
                "pub_date": "2025-04-01", noticias.INFLACAO: "Sim", noticias.ALIMENTOS: "Não",
            },
        ])
        filtradas = noticias.filtrar_historico(acervo, termo="acucar")
        self.assertEqual(filtradas["data_local"].dt.strftime("%Y-%m-%d").tolist(), [
            "2025-03-31", "2025-03-30",
        ])
        self.assertEqual(len(noticias.filtrar_historico(acervo, False, "acucar")), 3)

    def test_atualizacao_preserva_rotulos_e_repete_classificacao_pendente(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "noticias.csv"
            antiga = {
                "title": "Manchete antiga", "pub_date": "2025-03-31T01:10:00",
                "link": "https://example.com/antiga",
                noticias.INFLACAO: "Sim", noticias.ALIMENTOS: "Não",
            }
            pd.DataFrame([antiga]).to_csv(caminho, index=False)
            nova = {
                "title": "Preço do arroz", "description": "<p>Safra de arroz no Brasil.</p>",
                "pub_date": "2026-11-26T09:00:00-03:00",
                "link": "https://example.com/arroz?utm_source=rss",
            }
            cliente = Mock()
            mensagem = cliente.chat.completions.create.return_value
            recusa = Mock()
            recusa.message.content = None
            mensagem.choices = [recusa]
            self.assertEqual(atualizar_historico(caminho, [nova], cliente), (1, 0, 1))
            self.assertEqual(len(noticias.ler_historico(caminho)), 2)

            recusa.message.content = json.dumps({
                "inflacao": "Sim", "alimentos": "Sim",
                "queda_geral": "Não se aplica", "queda_alimentos": "Não",
            })
            repetida = {**nova, "link": "https://example.com/arroz#texto"}
            self.assertEqual(atualizar_historico(caminho, [repetida], cliente), (0, 1, 0))
            acervo = noticias.ler_historico(caminho)
            self.assertEqual(acervo[noticias.ALIMENTOS].tolist(), ["Não", "Sim"])
            self.assertEqual(acervo["pub_date"].tolist(), [antiga["pub_date"], nova["pub_date"]])
            self.assertTrue(acervo.loc[1, "collected_at"])

            args = cliente.chat.completions.create.call_args.kwargs
            self.assertEqual(args["model"], noticias.MODELO_CLASSIFICACAO)
            self.assertEqual(json.loads(args["messages"][1]["content"])["resumo"], "Safra de arroz no Brasil.")
            self.assertEqual(args["response_format"]["type"], "json_schema")

    def test_queda_da_api_preserva_lote_para_nova_tentativa(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "noticias.csv"
            lote = [
                {"title": "Arroz em alta", "link": "https://example.com/arroz"},
                {"title": "Preço do feijão", "link": "https://example.com/feijao"},
            ]
            cliente = Mock()
            cliente.chat.completions.create.side_effect = OpenAIError("API indisponível")
            self.assertEqual(atualizar_historico(caminho, lote, cliente), (2, 0, 2))
            self.assertEqual(noticias.ler_historico(caminho)[noticias.INFLACAO].tolist(), ["", ""])
            cliente.chat.completions.create.assert_called_once()

    def test_cota_da_api_tem_motivo_sem_detalhes_do_provedor(self):
        cliente = Mock()
        erro = OpenAIError("Detalhes internos")
        erro.code = "insufficient_quota"
        cliente.chat.completions.create.side_effect = erro
        with self.assertRaisesRegex(noticias.ClassificacaoIndisponivel, "^Cota da API indisponível$"):
            noticias.classificar_artigo({"title": "Preço do arroz"}, cliente)


if __name__ == "__main__":
    unittest.main()
