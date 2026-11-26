"""E aşaması: ortak skor dağılımından market türetimi ve tutarlılık (PM1–PM5)."""
import unittest

import numpy as np

from fi.model import pazar_modelleri as P
from fi.model.goller import skor_matrisi
from fi.pazar import esdegerlik as E


class PM(unittest.TestCase):
    def test_PM1_tutarlilik_rastgele(self):
        rng = np.random.default_rng(3)
        for _ in range(200):
            lh, la, rho = rng.uniform(0.2, 3.5), rng.uniform(0.2, 3.5), rng.uniform(-0.1, 0.1)
            m = skor_matrisi(lh, la, rho)
            self.assertEqual(P.tutarlilik_denetimi(P.market_olasiliklari(m), m), [])

    def test_PM2_tutarsizlik_yakalanir(self):
        m = skor_matrisi(1.4, 1.1)
        p = P.market_olasiliklari(m)
        p["CS_1X"] += 0.01
        p["AU1.5_alt"] = p["AU2.5_alt"] + 0.01
        h = P.tutarlilik_denetimi(p, m)
        self.assertTrue(any("CS_1X" in x for x in h))
        self.assertTrue(any("artan" in x for x in h))

    def test_PM3_gozlenen(self):
        y = P.gozlenen(1, 1)
        self.assertTrue(y["skor_1_1"] and y["MSX_AU2.5_alt"] and y["KG_var"] and y["MSX_KG_var"])
        self.assertFalse(y["AU0.5_alt"] or y["MS_1"])
        y = P.gozlenen(2, 0)
        self.assertTrue(y["H-1_1"] and y["ev1.5_ust"] and y["dep0.5_alt"] and y["cift"])
        y = P.gozlenen(12, 0)               # ızgara dışı gol: 10'a kırpılır, olay yönleri korunur
        self.assertTrue(y["MS_1"] and y["AU4.5_ust"] and y["aralik_6p"])

    def test_PM4_esdegerlik_modulu_ile_ayni_olaylar(self):
        """Fiyat denetimindeki olay tanımları (fi.pazar) ile olasılık katmanındaki tanımlar aynı skor kümeleridir."""
        def ms_maske(e_maske):
            out = np.zeros((11, 11), bool)
            for h, a, v in zip(E.H.tolist(), E.A.tolist(), e_maske.tolist()):
                if v and h <= 10 and a <= 10:
                    out[h, a] = True
            return out
        mk = {"market_kodu": 446, "market_adi": "2,5 Alt/Üst ve Karşılıklı Gol", "cizgi": 2.5, "market_durumu_MS": 1,
              "adsiz": False, "handikap": None,
              "secenekler": [{"secenek_no": 1, "secenek_adi": "Alt & Var", "oran": 6.0, "oynanabilirlik": "oynanabilir"}]}
        alt_var = E.market_olaylari(mk, 1)[0].olay.maske
        self.assertTrue((ms_maske(alt_var) == P.OLAYLAR["skor_1_1"]).all())
        mk2 = dict(mk, market_kodu=342, market_adi="Maç Sonucu ve 1,5 Alt/Üst", cizgi=1.5,
                   secenekler=[{"secenek_no": 2, "secenek_adi": "MSX & Alt", "oran": 9.0, "oynanabilirlik": "oynanabilir"}])
        self.assertTrue((ms_maske(E.market_olaylari(mk2, 1)[0].olay.maske) == P.OLAYLAR["skor_0_0"]).all())

    def test_PM5_devre_marketi_yok(self):
        self.assertFalse(any(k.startswith(("IY", "1Y", "2Y")) for k in P.OLAYLAR))


if __name__ == "__main__":
    unittest.main()
