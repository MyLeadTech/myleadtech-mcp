"""Tests hors ligne du serveur stdio contre un faux serveur HTTP local (ledger simulé par clé d'idempotence)."""

import asyncio
import http.server
import json
import pathlib
import re
import threading
import unittest

import myleadtech_mcp
from myleadtech_mcp import server

RACINE = pathlib.Path(__file__).resolve().parents[1]


class Faux:
    def __init__(self, scenario):
        self.scenario, self.appels, self.cles, self.debits, self.vues = list(scenario), 0, [], 0, {}
        self.corps = []
        faux = self

        class H(http.server.BaseHTTPRequestHandler):
            def _rep(self):
                n = int(self.headers.get("Content-Length", 0))
                faux.corps.append(json.loads(self.rfile.read(n) or b"{}"))
                cle = self.headers.get("Idempotency-Key")
                faux.cles.append(cle)
                faux.ua = self.headers.get("User-Agent")
                i = min(faux.appels, len(faux.scenario) - 1)
                faux.appels += 1
                statut, corps, entetes = faux.scenario[i]
                if statut == 200 and cle:  # ledger : un débit par clé, rejeu sinon
                    if cle not in faux.vues:
                        faux.debits += 1
                        faux.vues[cle] = corps
                    corps = faux.vues[cle]
                raw = json.dumps(corps).encode()
                self.send_response(statut)
                self.send_header("X-Request-Id", "rid-%d" % faux.appels)
                for k, v in entetes.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            do_POST = do_GET = _rep

            def log_message(self, *a, **k):
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:%d" % self.srv.server_port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


OK = (200, {"request_id": "r", "status": "ok", "answer": "Illustrative answer.", "usage": {"debited": True, "units": 1}}, {})


def err(statut, code, retry=None):
    e = {"code": code, "message": "msg-" + code}
    if retry is not None:
        e["retry_after_seconds"] = retry
    return (statut, {"request_id": "r", "error": e}, {})


class TestStdio(unittest.TestCase):
    def setUp(self):
        self.attentes = []
        self._old = (server.API_URL, server._sleep)
        server._sleep = self.attentes.append
        import os
        os.environ["MYLEADTECH_API_KEY"] = "test-key"
        self.addCleanup(lambda: (setattr(server, "API_URL", self._old[0]), setattr(server, "_sleep", self._old[1])))

    def faux(self, scenario):
        f = Faux(scenario)
        self.addCleanup(f.close)
        server.API_URL = f.url
        return f

    def test_retry_apres_503_debite_une_seule_fois(self):
        f = self.faux([err(503, "dependency_unavailable", 1), OK])
        rep = server.answer_hvac_question("q")
        self.assertEqual(rep["status"], "ok")
        self.assertEqual(f.appels, 2)
        self.assertEqual(len(set(f.cles)), 1)  # même clé aux deux tentatives
        self.assertEqual(f.debits, 1)  # débité UNE fois
        self.assertEqual(self.attentes, [1.0])

    def test_reprises_bornees(self):
        f = self.faux([err(429, "rate_limited", 1)])
        with self.assertRaises(RuntimeError) as cm:
            server.search_hvac_documents("q")
        self.assertEqual(f.appels, server.MAX_RETRIES + 1)
        self.assertEqual(len(set(f.cles)), 1)
        self.assertIn("rate_limited: msg-rate_limited (request_id=rid-4)", str(cm.exception))

    def test_jamais_repris(self):
        for e in (err(429, "quota_exceeded", 1000000), err(503, "service_closed", 3600),
                  err(409, "conflict"), err(403, "not_entitled"), err(400, "invalid_request")):
            f = self.faux([e])
            with self.assertRaises(RuntimeError) as cm:
                server.answer_hvac_question("q")
            self.assertEqual(f.appels, 1)
            self.assertIn("request_id=rid-1", str(cm.exception))
            self.assertNotIn("{", str(cm.exception))  # message, jamais le corps brut

    def test_operation_id_est_la_cle(self):
        f = self.faux([OK])
        server.answer_hvac_question("q", operation_id="op-1")
        self.assertEqual(f.cles, ["op-1"])

    def test_audience_transmis_seulement_si_non_defaut(self):
        f = self.faux([OK])
        server.answer_hvac_question("q")
        server.answer_hvac_question("q", audience="homeowner")
        self.assertNotIn("audience", f.corps[0])
        self.assertEqual(f.corps[1]["audience"], "homeowner")

    def test_get_usage(self):
        f = self.faux([(200, {"remaining": 92.0}, {})])
        self.assertEqual(server.get_usage()["remaining"], 92.0)

    def test_lookup_fault_code_cle_prefixee(self):
        f = self.faux([OK])
        server.lookup_fault_code("E1", brand="carrier")
        self.assertTrue(f.cles[0].startswith("fc:"))
        self.assertEqual(f.corps[0], {"code": "E1", "language": "en-US", "brand": "carrier"})

    def test_user_agent_et_versions_alignes(self):
        f = self.faux([OK])
        server.answer_hvac_question("q")
        v = myleadtech_mcp.__version__
        self.assertEqual(f.ua, f"myleadtech-mcp/{v}")
        self.assertIn(f'version = "{v}"', (RACINE / "pyproject.toml").read_text())
        for nom in ("server.json", "plugin.json"):
            self.assertEqual(json.loads((RACINE / nom).read_text())["version"], v, nom)

    def test_outils_exposes(self):
        noms = {t.name for t in asyncio.run(server.mcp.list_tools())}
        self.assertEqual(noms, {"resolve_equipment", "search_hvac_documents", "get_hvac_source",
                                "answer_hvac_question", "get_hvac_document_page", "get_usage",
                                "lookup_fault_code"})  # 7 outils = server-card en production (14/11)

    def test_lookup_fault_code_retire_par_drapeau_0(self):
        import os
        server.mcp._tool_manager._tools.pop("lookup_fault_code", None)
        os.environ["MYLEADTECH_ENABLE_LOOKUP_FAULT_CODE"] = "0"
        try:
            server.register_optional_tools()
            noms = {t.name for t in asyncio.run(server.mcp.list_tools())}
            self.assertNotIn("lookup_fault_code", noms)
        finally:
            os.environ.pop("MYLEADTECH_ENABLE_LOOKUP_FAULT_CODE", None)
            server.register_optional_tools()  # rétablit l'état par défaut
        self.assertIn("lookup_fault_code", {t.name for t in asyncio.run(server.mcp.list_tools())})

    def test_max_chars_transmis_seulement_si_pose(self):
        f = self.faux([OK])
        server.search_hvac_documents("q")
        server.answer_hvac_question("q", max_chars=300)
        self.assertNotIn("max_chars", f.corps[0])
        self.assertEqual(f.corps[1]["max_chars"], 300)

    def test_facturation_answer_exacte(self):
        desc = {t.name: t.description for t in asyncio.run(server.mcp.list_tools())}
        self.assertIn("established", desc["answer_hvac_question"])
        self.assertNotIn("Billed: 1 unit when status is ok. audience", desc["answer_hvac_question"])

    def test_aucun_id_reel_dans_les_fichiers_publies(self):
        uuid_re = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
        for chemin in list(RACINE.glob("*.md")) + list(RACINE.glob("*.json")) + list((RACINE / "docs").rglob("*.md")):
            for u in uuid_re.findall(chemin.read_text()):
                self.assertTrue(u.startswith("00000000-0000-4000-8000-"), f"{chemin.name}: {u}")


if __name__ == "__main__":
    unittest.main()
