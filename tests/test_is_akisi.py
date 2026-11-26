"""K + L: tek maç iş akışı, dondurma, sonradan fiyat karşılaştırması, ileri puanlama (K1–K7, L1)."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fi import is_akisi as K
from fi.girdi import OranSizintisi


def fikstur():
    return {"maclar": [
        {"mac_id": "nesine:1", "lig": "Test Lig", "ev": "Alfa", "deplasman": "Beta", "karsilasma": "Alfa - Beta",
         "baslama_tr": "2026-11-26T23:45:00+03:00"},
        {"mac_id": "nesine:2", "lig": "Test Lig", "ev": "Gama", "deplasman": "Delta", "karsilasma": "Gama - Delta",
         "baslama_tr": "2026-11-27T00:15:00+03:00"},
        {"mac_id": "nesine:3", "lig": "Test Lig", "ev": "Alfa", "deplasman": "Gama", "karsilasma": "Alfa - Gama",
         "baslama_tr": "2026-11-26T20:45:00+03:00"}]}


def lig_verisi(son="2026-11-20"):
    import random
    r = random.Random(1)
    ts = ["Alfa", "Beta", "Gama", "Delta"]
    ms = []
    d = datetime(2026, 8, 1)
    while d.date().isoformat() <= son:
        for i, e in enumerate(ts):
            for dp in ts[i + 1:]:
                ms.append({"sezon": "2026-27", "tarih": d.date().isoformat(), "ev": e.lower(), "dep": dp.lower(),
                           "ev_ad": e, "dep_ad": dp, "ev_gol": r.randint(0, 3), "dep_gol": r.randint(0, 2)})
        d += timedelta(days=7)
    return ms


KAPSAM = ({"modeller": {"poisson_E": {"tanim": "test", "degerlendirme_ligleri": ["xx.1"], "marketler": {
    "MS_1": {"kapsamda": True, "nedenler": []}, "MS_X": {"kapsamda": True, "nedenler": []},
    "MS_2": {"kapsamda": True, "nedenler": []}, "AU2.5_ust": {"kapsamda": False, "nedenler": ["tabanı geçmiyor"]}}}}},
          "0" * 64)


class K_(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_K1_gun_filtresi_gece_yarisi_disarida(self):
        g = K.gunun_maclari(fikstur(), "2026-11-26")
        self.assertEqual([m["mac_id"] for m in g], ["nesine:3", "nesine:1"])

    def test_K2_lig_eslemesi_yoksa_hesaplanamaz(self):
        t = K.bagimsiz_tahmin(fikstur()["maclar"][0], lig_verisi(), None, kapsam=KAPSAM)
        self.assertEqual(t["durum"], "hesaplanamaz")
        self.assertIn("lig_eslemesi_onayli", t["nedenler"][0])
        self.assertIsNone(K.lig_eslemesi("İngiltere 1. Lig"))          # depoda onaylı kayıt yok

    def test_K3_eski_veri_hesaplanamaz(self):
        t = K.bagimsiz_tahmin(fikstur()["maclar"][0], lig_verisi("2026-09-20"), "xx.1", kapsam=KAPSAM)
        self.assertEqual(t["durum"], "hesaplanamaz")
        self.assertTrue(any(n.startswith("veri_guncel") for n in t["nedenler"]))

    def test_K4_tam_akis(self):
        mac = fikstur()["maclar"][0]
        t = K.bagimsiz_tahmin(mac, lig_verisi(), "xx.1", kapsam=KAPSAM)
        self.assertEqual(t["durum"], "hesaplandi", t.get("nedenler"))
        p = t["olasiliklar"]
        self.assertAlmostEqual(p["MS_1"] + p["MS_X"] + p["MS_2"], 1.0, places=9)
        self.assertNotIn("AU2.5_ust", p)                                 # doğrulanmamış market yok
        donma = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
        z = K.dondur(mac, t, self.d, simdi=donma)
        nesine = {"mac_kodu": 1, "marketler": [
            {"market_kodu": 1, "market_adi": "Maç Sonucu", "cizgi": 0.0, "market_durumu_MS": 1, "adsiz": False,
             "handikap": None, "secenekler": [
                 {"secenek_no": 1, "secenek_adi": "MS 1", "oran": 2.0, "oynanabilirlik": "oynanabilir"},
                 {"secenek_no": 2, "secenek_adi": "MS X", "oran": 3.4, "oynanabilirlik": "oynanabilir"},
                 {"secenek_no": 3, "secenek_adi": "MS 2", "oran": 3.9, "oynanabilirlik": "durumu_dogrulanmamis"}]},
            {"market_kodu": 12, "market_adi": "2,5 Gol Alt/Üst", "cizgi": 2.5, "market_durumu_MS": 1, "adsiz": False,
             "handikap": None, "secenekler": [{"secenek_no": 2, "secenek_adi": "Üst", "oran": 1.9,
                                               "oynanabilirlik": "oynanabilir"}]}]}
        k = K.fiyat_karsilastir(Path(z["yol"]), nesine, simdi=donma + timedelta(minutes=5))
        s = {x["secenek_adi"]: x for x in k["satirlar"]}
        self.assertAlmostEqual(s["MS 1"]["beklenen_deger"], round(p["MS_1"] * 2.0 - 1, 4), places=4)
        self.assertEqual(s["MS 1"]["basabas_esigi"], 0.5)
        self.assertNotIn("beklenen_deger", s["MS 2"])                    # oynanabilir değil
        self.assertEqual(s["Üst"]["bagimsiz_olasilik"], "hesaplanamaz")  # E'de doğrulanmadı
        self.assertEqual(k["donmus_sha256"], z["sha256"])

    def test_K5_mac_basladiktan_sonra_dondurma_yok(self):
        mac = fikstur()["maclar"][0]
        with self.assertRaises(ValueError):
            K.dondur(mac, {"durum": "hesaplanamaz"}, self.d, simdi=datetime(2026, 11, 26, 21, 0, tzinfo=timezone.utc))

    def test_K6_degistirilmis_donmus_tahmin_reddedilir(self):
        mac = fikstur()["maclar"][0]
        z = K.dondur(mac, {"durum": "hesaplanamaz", "nedenler": ["x"]}, self.d,
                     simdi=datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc))
        k = json.loads(Path(z["yol"]).read_text())
        k["tahmin"]["durum"] = "hesaplandi"
        Path(z["yol"]).write_text(json.dumps(k))
        with self.assertRaises(ValueError):
            K.donmus_oku(Path(z["yol"]))
        with self.assertRaises(ValueError):                              # dondurmadan önce karşılaştırma yok
            z2 = K.dondur(mac, {"durum": "hesaplanamaz"}, self.d, simdi=datetime(2026, 11, 26, 11, 0, tzinfo=timezone.utc))
            K.fiyat_karsilastir(Path(z2["yol"]), {"marketler": []}, simdi=datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc))

    def test_K7_oran_tahmin_girdisine_giremez(self):
        mac = dict(fikstur()["maclar"][0], oran_1=2.0)
        with self.assertRaises(OranSizintisi):
            K.bagimsiz_tahmin(mac, lig_verisi(), "xx.1", kapsam=KAPSAM)
        with self.assertRaises(OranSizintisi):
            K.dondur(fikstur()["maclar"][0], {"durum": "hesaplandi", "nesine_oran": 2.0}, self.d,
                     simdi=datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc))

    def test_K8_hazirlik_kapisi(self):
        mac = fikstur()["maclar"][0]
        t = K.bagimsiz_tahmin(mac, lig_verisi(), "yy.1", kapsam=KAPSAM)          # model bu ligde değerlendirilmedi
        self.assertEqual(t["durum"], "hesaplanamaz")
        self.assertIn("model_bu_ligde_degerlendirildi", " ".join(t["nedenler"]))
        t = K.bagimsiz_tahmin(mac, lig_verisi(), "xx.1", kapsam=KAPSAM)
        self.assertTrue(all(h["gecti"] for h in t["hazirlik"]))
        self.assertEqual(set(t["olasiliklar"]), {"MS_1", "MS_X", "MS_2"})       # kapsam dışı AU2.5 yok
        self.assertIn("AU2.5_ust", t["hesaplanamaz_pazarlar"])
        gercek, sha = K.kapsam_yukle()                                            # depodaki kayıt
        self.assertEqual(len(sha), 64)
        self.assertNotIn("xx.1", gercek["modeller"]["poisson_E"]["degerlendirme_ligleri"])

    def test_K9_e2_buzulme_yolu(self):
        k2 = ({"modeller": {"E2_aday": {"tanim": "t", "spec": {"ceza": 16.0, "w": 0.65, "b": 0.0},
                                        "degerlendirme_ligleri": ["xx.1"],
                                        "marketler": {"KG_var": {"kapsamda": True, "nedenler": []}}}}}, "1" * 64)
        mac = fikstur()["maclar"][0]
        t = K.bagimsiz_tahmin(mac, lig_verisi(), "xx.1", kapsam=k2)
        self.assertEqual(t["durum"], "hesaplandi", t.get("nedenler"))
        self.assertEqual(t["model_adi"], "E2_aday")
        self.assertIn("lig_ortalamasi_365", t)
        self.assertEqual(set(t["olasiliklar"]), {"KG_var"})

    def test_L1_ileri_puanlama(self):
        mac = fikstur()["maclar"][0]
        t = K.bagimsiz_tahmin(mac, lig_verisi(), "xx.1", kapsam=KAPSAM)
        z = K.dondur(mac, t, self.d, simdi=datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc))
        r = K.ileri_puanla(Path(z["yol"]), 2, 1, "test")
        self.assertEqual(r["puanlar"]["MS_1"]["y"], 1.0)
        self.assertAlmostEqual(r["puanlar"]["MS_1"]["brier"], (t["olasiliklar"]["MS_1"] - 1) ** 2)
        kayit = (self.d / "kayit.jsonl").read_text().strip().splitlines()
        self.assertEqual(len(kayit), 1)


if __name__ == "__main__":
    unittest.main()
