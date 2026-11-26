"""Sohbet komutları (uygulama.sohbet): gün kuralı, MK-1 oran gizleme, oran tarafsızlığı, yeniden deneme, kilitler.
Ağ isteği yapılmaz; komutlar ayrı süreçte sahte çıktı kökünde (FI_OUTPUT) çalışır."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "lib"))
sys.path.insert(0, str(KOK))
from fi import is_akisi as I  # noqa: E402

IZ = 9.87


def _mac(kod, bas, lig="Test Ligi"):
    sec = [{"secenek_no": 1, "secenek_adi": "MS 1", "oran": 1.20, "oynanabilirlik": "oynanabilir"},
           {"secenek_no": 2, "secenek_adi": "MS X", "oran": 5.40, "oynanabilirlik": "oynanabilir"},
           {"secenek_no": 3, "secenek_adi": "MS 2", "oran": IZ, "oynanabilirlik": "oynanabilir"}]
    return {"kod": kod, "lig": lig, "lig_kodu": 9, "lig_ulke": "XX", "ev": f"Ev{kod}", "deplasman": f"Dep{kod}",
            "karsilasma": f"Ev{kod} - Dep{kod}", "baslama_tr": bas,
            "marketler": [{"market_adi": "Maç Sonucu", "ozel_deger": 0.0, "maca_ozel": False, "secenekler": sec},
                          {"market_adi": "Kırmızı Kart", "ozel_deger": 0.0, "maca_ozel": True,
                           "secenekler": [{"secenek_adi": "Var", "oran": 4.10, "oynanabilirlik": "oynanabilir"}]}]}


def kur(kok: Path):
    b = kok / "bulten_20261130_120000"
    b.mkdir(parents=True)
    (b / "mac_oncesi.json").write_text(json.dumps({
        "kaynak": {"cekim_utc": "2026-11-30T12:00:00+00:00", "cekim_tr": "2026-11-30T15:00:00+03:00", "sha256": "ab" * 32},
        "pencere_tr": ["2026-12-01T00:00:00+03:00", "2026-12-02T00:00:00+03:00"],
        "futbol": [_mac(1, "2026-12-01T23:59:00+03:00"), _mac(2, "2026-12-01T20:00:00+03:00"),
                   _mac(3, "2026-12-02T00:30:00+03:00")]}), encoding="utf-8")
    (b / "dogrulama.json").write_text(json.dumps({"durum": "BASARILI", "kayitlar": []}))
    I.dondur({"mac_id": "nesine:2", "karsilasma": "Ev2 - Dep2", "lig": "Test Ligi", "baslama_tr": "2026-12-01T20:00:00+03:00"},
             {"durum": "hesaplandi", "veri_kesimi": "2026-11-29", "model_adi": "test", "lambda_ev": 1.2, "lambda_dep": 1.0,
              "egitim_mac_sayisi": 10, "olasiliklar": {"MS_X": 0.25}, "hesaplanamaz_pazarlar": {}},
             kok=kok / "tahminler", simdi=datetime.fromisoformat("2026-11-30T10:00:00+00:00"))
    # başarısız bir çekim: listede görünmemeli
    f = kok / "bulten_20261130_130000"
    f.mkdir()
    (f / "mac_oncesi.json").write_text(json.dumps({"kaynak": {}, "futbol": []}))
    (f / "dogrulama.json").write_text(json.dumps({"durum": "BASARISIZ", "kayitlar": [{"seviye": "KRITIK", "kod": "BAGLANTI"}]}))


class Komutlar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kok = Path(tempfile.mkdtemp())
        kur(cls.kok)

    def calistir(self, *arg):
        env = {**os.environ, "FI_OUTPUT": str(self.kok), "PYTHONPATH": str(KOK / "lib") + os.pathsep + str(KOK)}
        p = subprocess.run([sys.executable, "-m", "uygulama.sohbet", *arg], cwd=KOK, env=env, capture_output=True,
                           text=True, timeout=60)
        return p.returncode, p.stdout + p.stderr

    def test_s1_gun_kurali_ve_oransiz_liste(self):
        k, c = self.calistir("maclar", "--gun", "2026-12-01")
        self.assertEqual(k, 0, c)
        self.assertIn("Ev1 - Dep1", c)
        self.assertIn("Ev2 - Dep2", c)
        self.assertNotIn("Ev3 - Dep3", c)           # ertesi gün 00:30
        self.assertNotIn(str(IZ), c)
        self.assertNotIn("bulten_20261130_130000", c)  # başarısız çekim seçilmez
        self.assertIn("donmuş tahmin var", c)

    def test_s2_marketler_model_yoksa_kesif_donmusse_acik(self):
        k, c = self.calistir("marketler", "1")              # Test Ligi: bağımsız model yok → keşif
        self.assertIn("yalnızca KEŞİF", c)
        self.assertIn("yüzde ve EV verilmez", c)
        with mock.patch("uygulama.veri.hazirlik_ozeti", return_value={"durum": "hazirlanabilir", "neden": "", "modeller": ["E3"],
                                                                       "kaynak_lig": "en.1"}):
            from uygulama import sohbet as S
            out = io.StringIO()
            with mock.patch.object(S.V, "OUTPUT", self.kok), mock.patch.object(S.V, "TAHMIN", self.kok / "tahminler"), \
                    mock.patch.object(S.V, "bultenler", return_value=[self.kok / "bulten_20261130_120000"]), \
                    mock.patch.object(S.V, "donmus_bul", return_value=None), redirect_stdout(out):
                S.marketler("1")
            self.assertIn("oranlar GÖSTERİLMİYOR", out.getvalue())   # model var ama donmamış → gizli
            self.assertNotIn(str(IZ), out.getvalue())
        k, c = self.calistir("marketler", "2")          # donmuş → oranlar açık
        self.assertIn(str(IZ), c)
        self.assertIn("Kırmızı Kart", c)

    def test_s3_tara_varsayilan_fiyat_suzgeci_yok(self):
        with mock.patch.dict(os.environ, {}):
            k, c = self.calistir("tara", "--gun", "2026-12-01")
        self.assertIn("fiyat süzgeci yok", c)
        self.assertIn("Oran tarafsızlığı", c)
        k, c = self.calistir("tara", "--gun", "2026-12-01", "--min-oran", "5", "--market", "Maç Sonucu")
        self.assertIn("MS X 5.40", c)
        self.assertIn(f"MS 2 {IZ:.2f}", c)
        self.assertNotIn("MS 1 1.20", c)
        k, c = self.calistir("tara", "--gun", "2026-12-01", "--maks-oran", "1.5", "--market", "Maç Sonucu")
        self.assertIn("MS 1 1.20", c)                   # düşük oran da aynı şekilde süzülebilir

    def test_s4_karsilastir_kilidi(self):
        k, c = self.calistir("karsilastir", "1")
        self.assertEqual(k, 1)
        self.assertIn("kilitli", c)

    def test_s5_dondur_hazir_olmayan(self):
        k, c = self.calistir("dondur", "1")
        self.assertEqual(k, 1)
        self.assertIn("Dondurulmadı", c)
        self.assertEqual(len((self.kok / "tahminler" / "kayit.jsonl").read_text().splitlines()), 1)

    def test_s6_surpriz_favori_orandan_belirlenmez(self):
        k, c = self.calistir("surpriz", "1")
        self.assertIn("favori oranla belirlenmez", c)
        self.assertNotIn(str(IZ), c)


class YenidenDeneme(unittest.TestCase):
    def setUp(self):
        from uygulama import islemler as IS, sohbet as S
        self.IS, self.S = IS, S

    def _calis(self, hatalar):
        sayac = {"n": 0}

        def sahte(gun):
            sayac["n"] += 1
            if hatalar:
                kod = hatalar.pop(0)
                raise self.IS.BultenHatasi("x", [kod], None)
            return {"klasor": "bulten_x", "gun": gun}
        out = io.StringIO()
        with mock.patch.object(self.S.IS, "bulten_cek", side_effect=sahte), \
                mock.patch.object(self.S, "_bulten_ozeti", return_value=0), \
                mock.patch.object(self.S, "_bulten_sec", return_value=None), \
                mock.patch.object(self.S, "YENIDEN_DENEME_BEKLEME", (0, 0)), redirect_stdout(out):
            k = self.S.bulten("2026-12-01")
        return k, sayac["n"], out.getvalue()

    def test_r1_baglanti_hatasinda_sinirli_deneme(self):
        k, n, _ = self._calis(["BAGLANTI", "BAGLANTI"])
        self.assertEqual((k, n), (0, 3))
        k, n, c = self._calis(["BAGLANTI", "BAGLANTI", "BAGLANTI"])
        self.assertEqual((k, n), (2, 3))
        self.assertIn("çekilemedi", c)

    def test_r2_engelde_hic_yeniden_deneme_yok(self):
        k, n, c = self._calis(["ERISIM_ENGELI"])
        self.assertEqual((k, n), (2, 1))
        self.assertIn("Engel aşılmaya çalışılmadı", c)


class Kapsam(unittest.TestCase):
    def test_k1_e3_kayitli_ve_digerleri_degismedi(self):
        k, _ = I.kapsam_yukle()
        self.assertIn("E3", k["modeller"])
        e3 = k["modeller"]["E3"]
        self.assertEqual(set(e3["degerlendirme_ligleri"]), {"en.1", "de.1", "it.1", "es.1", "en.3", "en.4", "fr.2", "it.2"})
        self.assertTrue(e3["marketler"]["MS_1"]["kapsamda"])
        self.assertFalse(e3["marketler"]["KG_var"]["kapsamda"])
        self.assertEqual(k["modeller"]["E2_aday"]["degerlendirme_ligleri"], ["at.1", "be.1", "en.2", "gr.1", "sco.1", "tr.1"])

    def test_k2_on_kayit_degismedi(self):
        from fi.model import e3
        self.assertTrue(e3.on_kayit_dogrula().startswith("d267e98b"))

    def test_k3_e3_duzeltme_kapaliyken_e2(self):
        import numpy as np
        from fi.model import e3
        lh, la = e3._donustur(np.array([1.4]), np.array([0.9]), 1.0, 0.0)
        self.assertAlmostEqual(float(lh[0]), 1.4)
        self.assertAlmostEqual(float(la[0]), 0.9)
        lh, la = e3._donustur(np.array([1.4]), np.array([0.9]), 1.3, 0.1)
        self.assertAlmostEqual(float(lh[0] + la[0]), 2.3)          # toplam korunur


if __name__ == "__main__":
    unittest.main()
