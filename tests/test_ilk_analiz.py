"""İlk gerçek analiz (SOU–MID) için MK-1 sıra denetimi (IA1–IA4). Çıktılar git dışı; yoksa atlanır."""
import json
import unittest
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
DONMUS = KOK / "output" / "tahminler" / "nesine_3331002_20261126T181800Z.json"
BULTEN = KOK / "output" / "bulten_20261126_235932"


@unittest.skipUnless(DONMUS.exists() and (BULTEN / "fiyat_karsilastirma_3331002.json").exists(), "yerel çıktı yok")
class IA(unittest.TestCase):
    def setUp(self):
        from fi import is_akisi as K
        self.K = K
        self.d = K.donmus_oku(DONMUS)                       # SHA-256 doğrulaması burada
        self.k = json.loads((BULTEN / "fiyat_karsilastirma_3331002.json").read_text())

    def test_IA1_dondurma_bultenden_ve_mactan_once(self):
        donma = datetime.fromisoformat(self.d["dondurma_utc"])
        cekim = datetime.fromisoformat(json.loads((BULTEN / "kaynak.json").read_text())["kaynaklar"]["mac_oncesi"]["cekim_utc"])
        self.assertLess(donma, cekim)
        self.assertLess(donma, datetime.fromisoformat(self.d["baslama_tr"]))

    def test_IA2_yalniz_kapsamdaki_marketler(self):
        kap, _ = self.K.kapsam_yukle()
        kapsam = {a for a, r in kap["modeller"]["E2_aday"]["marketler"].items() if r["kapsamda"]}
        self.assertEqual(self.d["tahmin"]["model_adi"], "E2_aday")
        self.assertTrue(set(self.d["tahmin"]["olasiliklar"]) <= kapsam)
        self.assertNotIn("MS_1", self.d["tahmin"]["olasiliklar"])      # kalibre değil → yüzde yok

    def test_IA3_karsilastirma_ayni_donmus_kayda_dayanir(self):
        self.assertEqual(self.k["donmus_sha256"], self.d["sha256"])
        for s in self.k["satirlar"]:
            if isinstance(s.get("bagimsiz_olasilik"), float):
                self.assertAlmostEqual(s["bagimsiz_olasilik"], round(self.d["tahmin"]["olasiliklar"][s["model_marketi"]], 4))

    def test_IA4_donmus_kayitta_oran_yok(self):
        from fi.girdi import oransiz_mi
        oransiz_mi(self.d["tahmin"], "tahmin")
        from fi.haber.genis import model_girdisi_denetle
        model_girdisi_denetle(self.d["tahmin"], "tahmin")


if __name__ == "__main__":
    unittest.main()
