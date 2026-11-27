"""Araştırma hafızası ve bülten saklama politikası: kararlar, silmeden önce çıkarım, korunan klasörler, geri yükleme."""
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "lib"))
sys.path.insert(0, str(KOK))
from fi import is_akisi as I  # noqa: E402
from uygulama import hafiza as H  # noqa: E402

SIMDI = datetime.fromisoformat("2026-12-05T12:00:00+03:00")


def bulten(kok: Path, ad: str, basarisiz=False, kodlar=(1, 2), fiyat_kod=None):
    b = kok / ad
    b.mkdir(parents=True)
    (b / "ham").mkdir()
    (b / "ham" / "mac_oncesi.json").write_text("{}")
    maclar = [{"kod": k, "lig": "L", "ev": f"E{k}", "deplasman": f"D{k}", "baslama_tr": "2026-12-05T21:00:00+03:00",
               "marketler": [{"market_adi": "Maç Sonucu", "secenekler": [{"secenek_adi": "MS 1", "oran": 2.0}]}]} for k in kodlar]
    (b / "mac_oncesi.json").write_text(json.dumps({"kaynak": {"cekim_utc": "x", "sha256": "ab"}, "futbol": maclar}))
    (b / "dogrulama.json").write_text(json.dumps({"durum": "BASARISIZ" if basarisiz else "BASARILI", "kayitlar": []}))
    if fiyat_kod:
        (b / f"fiyat_karsilastirma_{fiyat_kod}.json").write_text(json.dumps({"donmus_sha256": "x"}))
    return b


class Saklama(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        bulten(self.kok, "bulten_20261201_200000")                       # süresi dolmuş
        bulten(self.kok, "bulten_20261205_010000")                       # aynı gün eski kopya (11 saat)
        bulten(self.kok, "bulten_20261205_090000", fiyat_kod=2)          # aynı gün, karşılaştırmada kullanıldı
        bulten(self.kok, "bulten_20261205_100000")                       # aynı gün eski ama < 6 saat
        bulten(self.kok, "bulten_20261205_110000")                       # günün en yenisi
        bulten(self.kok, "bulten_20261205_113000", basarisiz=True)       # başarısız
        bulten(self.kok, "bulten_20261204_230000")                       # dün, günün en yenisi
        for ad in ("tahminler", "arastirma", "model", "kaynak_veri"):
            (self.kok / ad).mkdir()
            (self.kok / ad / "x.json").write_text("{}")
        I.dondur({"mac_id": "nesine:1", "baslama_tr": "2026-12-05T21:00:00+03:00"}, {"durum": "hesaplandi"},
                 kok=self.kok / "tahminler", simdi=datetime.fromisoformat("2026-11-30T10:00:00+00:00"))

    def test_h1_plan_kararlari(self):
        k = {p["klasor"]: p["karar"] for p in H.plan(self.kok, SIMDI)}
        self.assertEqual(k, {"bulten_20261201_200000": "sil", "bulten_20261205_010000": "sil",
                             "bulten_20261205_090000": "tut", "bulten_20261205_100000": "tut",
                             "bulten_20261205_110000": "tut", "bulten_20261205_113000": "sil",
                             "bulten_20261204_230000": "tut"})

    def test_h2_hafiza_kumesi_ve_cikarim(self):
        self.assertEqual(sorted(H.hafiza_kodlari(self.kok)), [1, 2])     # donmuş tahmin + fiyat karşılaştırması
        r = H.cikar(self.kok / "bulten_20261205_090000", self.kok)
        self.assertTrue((self.kok / "hafiza" / "gunluk" / "bulten_20261205_090000.json").exists())
        snap = json.loads((self.kok / "hafiza" / "maclar" / "1" / "bulten_20261205_090000.json").read_text())
        self.assertEqual(snap["mac"]["marketler"][0]["secenekler"][0]["oran"], 2.0)     # zaman damgalı oran korunur
        self.assertIn("model girdisi değildir", snap["not"])
        self.assertTrue((self.kok / "hafiza" / "maclar" / "2" / "bulten_20261205_090000__fiyat_karsilastirma_2.json").exists())
        gunluk = json.loads((self.kok / "hafiza" / "gunluk" / "bulten_20261205_090000.json").read_text())
        self.assertNotIn("oran", json.dumps(gunluk))                      # günlük liste oransız
        self.assertEqual(H.cikar(self.kok / "bulten_20261205_090000", self.kok)["yazilan"], [])   # tekrar güvenli
        self.assertTrue(r["yazilan"])

    def test_h3_uygula_once_cikarim_sonra_silme_korunanlar_kalir(self):
        r = H.uygula(self.kok, SIMDI)
        self.assertEqual(sorted(x["klasor"] for x in r["silinen"]),
                         ["bulten_20261201_200000", "bulten_20261205_010000", "bulten_20261205_113000"])
        self.assertFalse((self.kok / "bulten_20261201_200000").exists())
        self.assertTrue((self.kok / "hafiza" / "maclar" / "1" / "bulten_20261201_200000.json").exists())
        self.assertTrue((self.kok / "hafiza" / "gunluk" / "bulten_20261201_200000.json").exists())
        for ad in ("tahminler", "arastirma", "model", "kaynak_veri"):
            self.assertTrue((self.kok / ad / "x.json").exists())
        self.assertTrue((self.kok / "bulten_20261205_110000").exists())
        self.assertTrue((self.kok / "hafiza" / "MANIFEST.sha256").exists())
        self.assertEqual(H.plan(self.kok, SIMDI) and [p["karar"] for p in H.plan(self.kok, SIMDI)].count("sil"), 0)

    def test_h4_dal_paketi_ve_geri_yukleme(self):
        H.guncelle(self.kok)
        paket = Path(tempfile.mkdtemp())
        r = H.dal_paketi(paket, self.kok)
        self.assertGreater(r["dosya"], 0)
        self.assertFalse(any("bulten_2026" in p.parts[-2] for p in paket.rglob("*") if p.is_file() and "hafiza" not in p.parts))
        self.assertFalse(list(paket.rglob("ham")))                         # ham bülten pakete girmez
        (self.kok / "arastirma" / "sayfalar").mkdir(parents=True)
        (self.kok / "arastirma" / "sayfalar" / "kulup.html").write_text('<script>"apiKey":"gizli"</script>')
        (self.kok / "arastirma" / "not.md").write_text("özet")
        p2 = Path(tempfile.mkdtemp())
        H.dal_paketi(p2, self.kok)
        self.assertFalse(list(p2.rglob("*.html")))                         # ham web sayfası (gömülü anahtar) girmez
        self.assertTrue((p2 / "output" / "arastirma" / "not.md").exists())
        hedef = Path(tempfile.mkdtemp())
        r1 = H.dal_geri_yukle(paket, hedef)
        r2 = H.dal_geri_yukle(paket, hedef)
        self.assertGreater(r1["yazilan"], 0)
        self.assertEqual((r2["yazilan"], r2["cakisma"]), (0, []))
        self.assertEqual(I.donmus_oku(next((hedef / "tahminler").glob("nesine_1_*.json")))["mac_id"], "nesine:1")
        (hedef / "arastirma" / "x.json").write_text('{"yerel": 1}')
        self.assertEqual(H.dal_geri_yukle(paket, hedef)["cakisma"], ["arastirma/x.json"])   # üzerine yazılmaz
        self.assertEqual((hedef / "arastirma" / "x.json").read_text(), '{"yerel": 1}')


if __name__ == "__main__":
    unittest.main()
