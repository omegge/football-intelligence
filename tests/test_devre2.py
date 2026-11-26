"""F2: durum bağımlı devre modeli (DV1–DV3)."""
import unittest

import numpy as np

from fi.model import devre2 as D


class DV(unittest.TestCase):
    def test_DV1_beta_sifir_F0_ile_ayni(self):
        a = D.dagilim(1.5, 1.1, 0.45, 0.44)
        b = D.dagilim(1.5, 1.1, 0.45, 0.44, (0.0, 0.0))
        self.assertTrue(np.allclose(a, b, atol=1e-12))
        self.assertAlmostEqual(a.sum(), 1.0, places=9)

    def test_DV2_bagimlilik_ortaya_cikar(self):
        # β ≠ 0 iken 1Y KG ve 2Y KG artık maç içinde bağımsız değildir
        p = D.dagilim(1.5, 1.1, 0.45, 0.44, (-0.3, 0.3))
        a, b = p[D.OLAYLAR["452|Var"][1]].sum(), p[D.OLAYLAR["599|Var"][1]].sum()
        self.assertGreater(abs(p[D.OLAYLAR["801|Evet/Evet"][1]].sum() - a * b), 1e-4)
        # 1Y marjinali β'dan etkilenmez
        p0 = D.dagilim(1.5, 1.1, 0.45, 0.44)
        self.assertAlmostEqual(p0[D.OLAYLAR["7|1.Y 1"][1]].sum(), p[D.OLAYLAR["7|1.Y 1"][1]].sum(), places=9)

    def test_DV3_nokta_kirpmaz_ve_mantiksal_tamamlar(self):
        self.assertIsNone(D.nokta({"iy_ev": 8, "iy_dep": 0, "ev_gol": 8, "dep_gol": 0}))
        self.assertEqual(D.nokta({"iy_ev": None, "iy_dep": None, "ev_gol": 0, "dep_gol": 0}), 0)
        self.assertIsNone(D.nokta({"iy_ev": None, "iy_dep": None, "ev_gol": 1, "dep_gol": 0}))


if __name__ == "__main__":
    unittest.main()
