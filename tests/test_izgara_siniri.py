"""Skor ızgarası sınırı: eşdeğerlik grupları ızgara büyütülünce değişmemeli (IZ1–IZ4)."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]

# Yüksek çizgiler, uç skorlar ve "diğer" seçenekleri içeren sentetik bülten
def _s(no, ad, oran=2.0):
    return {"secenek_no": no, "secenek_adi": ad, "oran": oran, "oynanabilirlik": "oynanabilir"}

MARKETLER = [
    {"market_kodu": 777, "market_adi": "Maç Skoru", "cizgi": 0.0, "market_durumu_MS": 1, "adsiz": False, "handikap": None,
     "secenekler": [_s(i, f"{a}:{b}") for i, (a, b) in enumerate([(0, 0), (6, 0), (13, 0), (14, 0), (7, 7)])] + [_s(99, "diğer")]},
    {"market_kodu": 779, "market_adi": "1. Yarı Skoru", "cizgi": 0.0, "market_durumu_MS": 1, "adsiz": False, "handikap": None,
     "secenekler": [_s(1, "0:0"), _s(2, "6:0"), _s(3, "7:0"), _s(10, "diğer")]},
] + [{"market_kodu": k, "market_adi": f"{c} Gol Alt/Üst", "cizgi": c, "market_durumu_MS": 1, "adsiz": False, "handikap": None,
      "secenekler": [_s(1, "Alt"), _s(2, "Üst")]} for k, c in ((207, 0.5), (12, 2.5), (155, 4.5), (13, 6.5), (11, 12.5), (11, 13.5))] + [
    {"market_kodu": 20, "market_adi": f"Ev Sahibi {c} Gol Alt/Üst", "cizgi": c, "market_durumu_MS": 1, "adsiz": False,
     "handikap": None, "secenekler": [_s(1, "Alt"), _s(2, "Üst")]} for c in (0.5, 5.5, 12.5, 13.5)] + [
    {"market_kodu": 209, "market_adi": f"1. Yarı {c} Gol Alt/Üst", "cizgi": c, "market_durumu_MS": 1, "adsiz": False,
     "handikap": None, "secenekler": [_s(1, "Alt"), _s(2, "Üst")]} for c in (0.5, 5.5, 6.5)] + [
    {"market_kodu": 43, "market_adi": "Toplam Gol Aralığı", "cizgi": 0.0, "market_durumu_MS": 1, "adsiz": False,
     "handikap": None, "secenekler": [_s(1, "0-1 Gol"), _s(4, "6+ Gol")]},
    {"market_kodu": 588, "market_adi": "Hangi Takım Kaç Farkla Kazanır?", "cizgi": 0.0, "market_durumu_MS": 1,
     "adsiz": False, "handikap": None, "secenekler": [_s(1, "Ev. 3+"), _s(7, "0")]},
    {"market_kodu": 49, "market_adi": "Tek/Çift", "cizgi": 0.0, "market_durumu_MS": 1, "adsiz": False, "handikap": None,
     "secenekler": [_s(1, "Tek"), _s(2, "Çift")]},
]

BETIK = r'''
import json, sys
from fi.pazar import esdegerlik as E
mk = json.loads(sys.stdin.read())
ss = [s for m in mk for s in E.market_olaylari(m, 1)]
imza = {}
for s in ss:
    if s.olay is not None:
        imza.setdefault(E._imza(s.olay.maske), []).append(s.kimlik)
print(json.dumps({"ust": E.UST, "gruplar": sorted(sorted(v) for v in imza.values()),
                  "eslenen": sorted(s.kimlik for s in ss if s.olay is not None)}))
'''


def calistir(ust: int, marketler) -> dict:
    env = dict(os.environ, FI_PAZAR_UST=str(ust), PYTHONPATH=str(KOK / "lib"))
    r = subprocess.run([sys.executable, "-c", BETIK], input=json.dumps(marketler), capture_output=True, text=True,
                       env=env, timeout=120)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


class IZ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a, cls.b = calistir(7, MARKETLER), calistir(10, MARKETLER)

    def test_IZ1_sinirda_esleme_yok(self):
        e = set(self.a["eslenen"])
        self.assertNotIn("777|0|3", e)          # 14:0 (sınır)
        self.assertIn("777|0|2", e)             # 13:0
        self.assertNotIn("779|0|3", e)          # 1Y 7:0 (sınır)
        self.assertNotIn("11|13.5|1", e)        # 13,5 toplam çizgisi
        self.assertNotIn("209|6.5|1", e)        # 1Y 6,5
        self.assertNotIn("20|13.5|1", e)

    def test_IZ2_gruplar_izgaradan_bagimsiz(self):
        # UST=7'de eşlenen seçeneklerin eşdeğerlik bölümlemesi UST=10'da aynı olmalı
        ortak = set(self.a["eslenen"])
        b = [sorted(x for x in g if x in ortak) for g in self.b["gruplar"]]
        self.assertEqual(sorted(x for x in b if x), self.a["gruplar"])

    def test_IZ3_diger_tumleyeni_sinirdan_etkilenmez(self):
        # "diğer" listelenen skorların tümleyeni: iki ızgarada da ayrı grupta, hiçbir skorla çakışmaz
        for r in (self.a, self.b):
            g = [x for x in r["gruplar"] if "777|0|99" in x][0]
            self.assertEqual(g, ["777|0|99"])

    def test_IZ4_gozlenen_kirpmasiz(self):
        from fi.model.pazar_modelleri import gozlenen
        y = gozlenen(0, 13)                      # nl.1 2020-21 VVV–Ajax: v1'de 10'a kırpılıp 'çift' sayılıyordu
        self.assertTrue(y["tek"] and not y["cift"] and y["MS_2"])
        y = gozlenen(11, 10)                     # kırpılsa beraberlik olurdu
        self.assertTrue(y["MS_1"] and not y["MS_X"])


if __name__ == "__main__":
    unittest.main()
