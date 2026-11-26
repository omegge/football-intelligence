"""F aşaması: devre olay uzayı ve bağımsız devre dağılımı (FA1–FA4)."""
import unittest

import numpy as np

from fi.model import f_asamasi as F
from fi import olay_uzayi as ES


class FA(unittest.TestCase):
    def test_FA1_dagilim_ve_marjinaller(self):
        p = F.ortak_dagilim(1.6, 1.1, 0.45, 0.43)
        self.assertAlmostEqual(p.sum(), 1.0, places=9)
        # 1Y KG ve 2Y KG maç içinde bağımsız: P(ikisi) = P(1Y KG)·P(2Y KG)
        a, b = p[F.OLAYLAR["452|Var"][1]].sum(), p[F.OLAYLAR["599|Var"][1]].sum()
        self.assertAlmostEqual(p[F.OLAYLAR["801|Evet/Evet"][1]].sum(), a * b, places=9)

    def test_FA2_nokta(self):
        m = {"iy_ev": 1, "iy_dep": 0, "ev_gol": 2, "dep_gol": 1}
        k = F.nokta(m)
        self.assertEqual((ES.H1[k], ES.A1[k], ES.H2[k], ES.A2[k]), (1, 0, 1, 1))
        self.assertEqual(F.nokta({"iy_ev": 2, "iy_dep": 0, "ev_gol": 1, "dep_gol": 0}), -1)   # çelişkili

    def test_FA2b_mantiksal_tamamlama(self):
        self.assertEqual(F.nokta({"iy_ev": None, "iy_dep": None, "ev_gol": 0, "dep_gol": 0}), 0)
        self.assertIsNone(F.nokta({"iy_ev": None, "iy_dep": None, "ev_gol": 0, "dep_gol": 0}, tamamla=False))
        self.assertIsNone(F.nokta({"iy_ev": None, "iy_dep": None, "ev_gol": 1, "dep_gol": 0}))   # tahmin edilmez

    def test_FA3_olay_tanimlari_esdegerlik_ile_ayni(self):
        t, _ = ES._tablo(5, 0.0, "", None)
        self.assertTrue((F.OLAYLAR["5|X/1"][1] == t["X/1"]).all())
        self.assertEqual(F.OLAYLAR["801|Evet/Evet"][0], "birlesik")
        self.assertEqual(F.OLAYLAR["452|Var"][0], "marjinal")

    def test_FA4_oran_yok(self):
        kaynak = open(F.__file__, encoding="utf-8").read().lower()
        for yasak in ("nesine_bulletin", "bahis_oran", '["oran"]', "b365"):
            self.assertNotIn(yasak, kaynak)


if __name__ == "__main__":
    unittest.main()
