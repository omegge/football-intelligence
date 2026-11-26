"""D aşaması: ligler arası güç prototipi (LA1–LA5) ve kupa/lig biçimi tarih denetimi (LA6–LA7)."""
import copy
import unittest

from fi.kaynaklar.openfootball import tarih_denetimi
from fi.model import ligler_arasi as L


def ym(lig, sezon, tarih, ev, dep, eg, dg):
    return {"lig": lig, "sezon": sezon, "tarih": tarih, "ev": ev, "dep": dep, "ev_ad": ev, "dep_ad": dep,
            "ev_gol": eg, "dep_gol": dg, "tur": "Matchday 1"}


def um(sezon, tarih, ev, dep, eg, dg, ev_lig, dep_lig, tur="Group A"):
    return {"lig": "uefa.cl", "sezon": sezon, "tarih": tarih, "ev": ev, "dep": dep, "ev_ad": ev, "dep_ad": dep,
            "ev_gol": eg, "dep_gol": dg, "tur": tur, "ev_yurt_ici_lig": ev_lig, "dep_yurt_ici_lig": dep_lig}


def veri():
    yi = [ym("en.1", "2011-12", "2011-08-10", "a1", "a2", 2, 0), ym("en.1", "2011-12", "2011-08-17", "a2", "a1", 1, 1),
          ym("nl.1", "2011-12", "2011-08-10", "b1", "b2", 0, 1), ym("nl.1", "2011-12", "2011-08-17", "b2", "b1", 3, 0)]
    ucl = [um("2011-12", "2011-09-14", "a1", "b1", 3, 0, "en.1", "nl.1"),
           um("2011-12", "2011-09-28", "b2", "avrupa:x", 1, 0, "nl.1", None),
           um("2011-12", "2012-05-19", "a1", "b2", 1, 1, "en.1", "nl.1", tur="Final")]
    return {"yurt_ici": yi, "ucl": ucl, "atlanan_sezonlar": [], "esleme_durumu": {}, "eslenmeyen_takim_sezon": []}


class LA(unittest.TestCase):
    def test_LA1_aktarim_farki(self):
        s = L.calistir(veri())
        b1, m1 = s["modeller"]["B1_ayri_lig"], s["modeller"]["M1_ortak_elo"]
        # B1: Avrupa maçları lig toplamını değiştirmez (her lig kendi içinde sıfır toplamlı)
        self.assertAlmostEqual(b1.puan["a1"] + b1.puan["a2"], 3000.0, places=6)
        self.assertAlmostEqual(b1.puan["b1"] + b1.puan["b2"], 3000.0, places=6)
        # M1: Avrupa sonucu lig seviyesini kaydırır (en.1 kazandı → en.1 toplamı arttı), genel toplam korunur
        self.assertGreater(m1.puan["a1"] + m1.puan["a2"], 3000.0)
        self.assertAlmostEqual(sum(m1.puan.values()), 1500.0 * len(m1.puan), places=6)

    def test_LA2_yurt_ici_verisiz_takim_B1_hesaplanamaz(self):
        s = L.calistir(veri())
        k = [k for k in s["kayitlar"] if k["dep_ad"] == "avrupa:x"][0]
        self.assertIsNone(k["B1_ayri_lig"])
        # ilk Avrupa maçında geçmişi yok: M1 de hesaplanamaz; puanı bu maçtan SONRA oluşur
        self.assertIsNone(k["M1_ortak_elo"])
        self.assertIn("avrupa:x", L.calistir(veri())["modeller"]["M1_ortak_elo"].puan)
        self.assertNotIn("avrupa:x", L.calistir(veri())["modeller"]["B1_ayri_lig"].puan)

    def test_LA3_final_tarafsiz(self):
        s = L.calistir(veri())
        k = [k for k in s["kayitlar"] if k["tur"] == "Final"][0]
        self.assertTrue(k["tarafsiz"])
        m = L.GenelElo(True)
        m.puan = {"a": 1500.0, "b": 1500.0}
        self.assertEqual(m.x("a", "b", True), 0.0)
        self.assertEqual(m.x("a", "b", False), 60.0 / 400)

    def test_LA4_sizinti_yok(self):
        v1, v2 = veri(), veri()
        v2["ucl"][-1]["ev_gol"], v2["ucl"][-1]["dep_gol"] = 0, 5     # son maçın sonucu değişirse
        k1, k2 = L.calistir(v1)["kayitlar"], L.calistir(v2)["kayitlar"]
        for a, b in zip(k1, k2):                                       # hiçbir tahmin değişmez (sonuç işlenmeden önce)
            self.assertEqual(a["M1_ortak_elo"], b["M1_ortak_elo"])
            self.assertEqual(a["B1_ayri_lig"], b["B1_ayri_lig"])

    def test_LA5_oran_anahtari_yok(self):
        kaynak = open(L.__file__, encoding="utf-8").read().lower()
        for yasak in ("nesine", "odds", "b365", "bilyoner", '["oran"]', "'oran'"):
            self.assertNotIn(yasak, kaynak)


class TarihBicim(unittest.TestCase):
    def m(self, sezon, tarih, ev, dep, tur):
        return {"sezon": sezon, "tarih": tarih, "ev": ev, "dep": dep, "ev_ad": ev, "dep_ad": dep, "tur": tur}

    def test_LA6_kupa_farkli_asama_mesru(self):
        ms = [self.m("2011-12", "2011-09-13", "a", "b", "Group H"), self.m("2011-12", "2012-04-03", "a", "b", "Quarterfinals"),
              self.m("2024-25", "2024-09-17", "c", "d", "League, Matchday 1"),
              self.m("2024-25", "2025-02-11", "c", "d", "Playoffs, Matchday 1")]
        self.assertEqual(tarih_denetimi(ms)[0], [])
        ayni = [self.m("2011-12", "2011-09-13", "a", "b", "Group H"), self.m("2011-12", "2011-10-13", "a", "b", "Group H")]
        self.assertEqual(len(tarih_denetimi(ayni)[0]), 1)

    def test_LA7_lig_bicimi_ust_siniri(self):
        ms = [self.m("2018-19", "2018-08-10", "a", "b", "Matchday 1"), self.m("2018-19", "2019-01-10", "a", "b", "Matchday 20")]
        self.assertEqual(len(tarih_denetimi(ms)[0]), 1)                 # varsayılan lig: tekrar serttir
        self.assertEqual(tarih_denetimi(ms, ust_sinir=2)[0], [])        # sco.1/at.1/ch.1/hu.1 biçimi
        ms.append(self.m("2018-19", "2019-04-10", "a", "b", "Matchday 30"))
        self.assertEqual(len(tarih_denetimi(ms, ust_sinir=2)[0]), 1)


if __name__ == "__main__":
    unittest.main()
