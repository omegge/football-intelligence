"""C aşaması: veri uygunluğu matrisi (U1–U3). Ağsız; geçici klasörde sentetik veri."""
import json
import tempfile
import unittest
from pathlib import Path

from fi.kaynaklar import uygunluk as U


def mac(t1, t2, ft, ht=None, tarih="2020-08-01"):
    s = {"ft": ft}
    if ht:
        s["ht"] = ht
    return {"date": tarih, "team1": t1, "team2": t2, "score": s}


class U_(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        for sezon, ms in {"2018-19": [mac("A", "B", [1, 0], [0, 0]), mac("B", "A", [2, 2])],
                          "2020-21": [mac("A", "B", [0, 0], [0, 0], "2021-05-01"),
                                      {"date": "2021-05-08", "team1": "B", "team2": "A"}]}.items():
            (self.d / sezon).mkdir()
            (self.d / sezon / "xx.1.json").write_text(json.dumps({"name": "x", "matches": ms}))

    def test_U1_openfootball_ozeti(self):
        o = U.openfootball_ozeti("xx.1", self.d)
        self.assertEqual(o["sezon_sayisi"], 2)
        self.assertEqual(o["skorlu_mac"], 3)
        self.assertEqual(o["tam_sezon_sayisi"], 1)          # 2020-21: 1/2 skorlu
        self.assertAlmostEqual(o["ilk_yari_orani"], round(2 / 3, 3))
        self.assertEqual(o["eksik_sezon_araligi"], ["2019-20"])
        self.assertEqual(o["son_skorlu_tarih"], "2021-05-01")
        self.assertIsNone(U.openfootball_ozeti("yy.1", self.d))

    def test_U2_openligadb_ozeti(self):
        veri = [{"matchIsFinished": True, "matchDateTimeUTC": "2026-11-05T20:00:00Z",
                 "matchResults": [{"resultTypeID": 1}, {"resultTypeID": 2}],
                 "goals": [{"matchMinute": 10}, {"matchMinute": None}]},
                {"matchIsFinished": False, "matchDateTimeUTC": "2026-11-26T20:00:00Z", "matchResults": [], "goals": []}]
        (self.d / "f.json").write_text(json.dumps(veri))
        l = U.openligadb_ozeti("f.json", self.d)
        self.assertEqual((l["mac"], l["biten"], l["ilk_yari_skorlu"]), (2, 1, 1))
        self.assertEqual(l["dakikali_gol_orani"], 0.5)
        self.assertEqual(l["son_biten_utc"], "2026-11-05T20:00:00Z")

    def test_U3_pasif_kaynak_ve_veri_yok_satirlari(self):
        adlar = {r[0]: r for r in U.KAPSAM}
        for lig in ("Danimarka Superliga", "Norveç Eliteserien", "İsveç Allsvenskan"):
            self.assertIsNone(adlar[lig][1])
        self.assertNotIn("footballdata", U.__dict__.get("KULLANILAN", []))
        kaynak = Path(U.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import urllib", kaynak)          # matris ağ isteği atmaz
        self.assertNotIn("requests", kaynak)


if __name__ == "__main__":
    unittest.main()
