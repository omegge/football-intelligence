"""H aşaması: kart verisi kuralları (HA1–HA2)."""
import math
import unittest

from fi.model import h_asamasi as H


class HA(unittest.TestCase):
    def test_HA1_kayitsiz_mac_sifir_sayilmaz(self):
        ms, say = H.veri()
        self.assertEqual(say["mac"] - say["kart_kaydi_yok"], len(ms))
        self.assertTrue(all(m["kart_ev"] + m["kart_dep"] >= 0 for m in ms))

    def test_HA2_poisson_yardimcilari(self):
        self.assertAlmostEqual(H._p_en_az(0, 3.0), 1.0)
        self.assertAlmostEqual(H._p_en_az(1, 3.0), 1 - math.exp(-3.0))
        self.assertAlmostEqual(H._pois_ll(2, 2.0), 2 * math.log(2) - 2 - math.log(2))


if __name__ == "__main__":
    unittest.main()
