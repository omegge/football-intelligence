"""V1 arayüzü: veri katmanı ve MK-1 kilitleri (oran yalnızca doğrulanmış donmuş tahminden sonra)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi import is_akisi as I  # noqa: E402
from uygulama import sunucu as S  # noqa: E402
from uygulama import veri as V  # noqa: E402
from fi.girdi import OranSizintisi  # noqa: E402


def bulten_satiri(kod=1, baslama="2026-12-01T21:00:00+03:00"):
    return {"kod": kod, "lig": "Test Ligi", "lig_kodu": 9, "lig_ulke": "XX", "ev": "A", "deplasman": "B",
            "karsilasma": "A - B", "baslama_tr": baslama, "marketler": [{"market_adi": "Maç Sonucu",
                                                                           "secenekler": [{"oran": 2.1}]}]}


def donmus_yaz(kok: Path, kod=1, simdi="2026-11-30T10:00:00+00:00"):
    from datetime import datetime
    mac = {"mac_id": f"nesine:{kod}", "karsilasma": "A - B", "lig": "Test Ligi", "baslama_tr": "2026-12-01T21:00:00+03:00"}
    tahmin = {"durum": "hesaplandi", "veri_kesimi": "2026-11-29", "olasiliklar": {"MS_X": 0.25}}
    return I.dondur(mac, tahmin, kok=kok, simdi=datetime.fromisoformat(simdi))


class VeriKatmani(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_v1_oransiz_mac(self):
        o = V.oransiz_mac(bulten_satiri())
        self.assertNotIn("marketler", o)
        self.assertEqual(o["market_sayisi"], 1)
        self.assertNotIn("2.1", json.dumps(o))

    def test_v1_gun_filtresi_tr(self):
        b = self.tmp / "bulten_20261130_100000"
        b.mkdir()
        (b / "mac_oncesi.json").write_text(json.dumps({"kaynak": {}, "futbol": [
            bulten_satiri(1, "2026-12-01T23:59:00+03:00"), bulten_satiri(2, "2026-12-02T00:30:00+03:00")]}))
        self.assertEqual([m["kod"] for m in V.gunun_maclari(b, "2026-12-01")], [1])
        self.assertEqual(V.bulten_gunleri(b), ["2026-12-01", "2026-12-02"])

    def test_v2_fiyat_kilidi(self):
        self.assertEqual(V.fiyat_karsilastirmasi(1, None, self.tmp)["durum"], "kilitli")
        self.assertEqual(V.fiyat_karsilastirmasi(1, {"hata": "bozuk"}, self.tmp)["durum"], "kilitli")

    def test_v2_fiyat_yalniz_eslesen_ve_sonraki(self):
        tk = self.tmp / "tahmin"
        donmus_yaz(tk)
        d = V.donmus_bul(1, tk)
        b = self.tmp / "bulten_20261130_120000"
        b.mkdir()
        (b / "mac_oncesi.json").write_text(json.dumps({"kaynak": {}, "futbol": []}))
        yol = b / "fiyat_karsilastirma_1.json"
        yol.write_text(json.dumps({"donmus_sha256": "baska", "dondurma_utc": d["dondurma_utc"],
                                   "karsilastirma_utc": "2026-11-30T12:00:00+00:00", "satirlar": []}))
        self.assertEqual(V.fiyat_karsilastirmasi(1, d, self.tmp)["durum"], "yok")
        yol.write_text(json.dumps({"donmus_sha256": d["sha256"], "dondurma_utc": d["dondurma_utc"],
                                   "karsilastirma_utc": "2026-11-30T09:00:00+00:00", "satirlar": []}))
        self.assertEqual(V.fiyat_karsilastirmasi(1, d, self.tmp)["durum"], "yok")
        yol.write_text(json.dumps({"donmus_sha256": d["sha256"], "dondurma_utc": d["dondurma_utc"],
                                   "karsilastirma_utc": "2026-11-30T12:00:00+00:00", "satirlar": []}))
        self.assertEqual(V.fiyat_karsilastirmasi(1, d, self.tmp)["durum"], "var")

    def test_v3_en_yuksek_fiyat(self):
        fk = {"esdegerlik": {"esdegerlik_gruplari": [{"olay": "x", "kapsam": "normal_sure", "uyeler": [
            {"market_adi": "a", "secenek_adi": "1", "oran": 2.0, "oynanabilirlik": "oynanabilir", "kesinlik": "kesin"},
            {"market_adi": "b", "secenek_adi": "1", "oran": 2.4, "oynanabilirlik": "oynanabilir", "kesinlik": "kesin"},
            {"market_adi": "c", "secenek_adi": "1", "oran": 9.0, "oynanabilirlik": "oynanabilir", "kesinlik": "kontrol_gerekli"},
            {"market_adi": "d", "secenek_adi": "1", "oran": 5.0, "oynanabilirlik": "durumu_dogrulanmamis", "kesinlik": "kesin"}]}]}}
        g = V.en_yuksek_fiyatlar(fk)[0]
        self.assertEqual((g["en_yuksek"]["market_adi"], g["kesin_oynanabilir"], g["kontrol_gerekli"], g["fark"]), ("b", 2, 1, 0.4))

    def test_v4_son_maclar(self):
        k = self.tmp / "guncel" / "20261130T000000Z"
        k.mkdir(parents=True)
        def m(t, ev, dep, a, b):
            return {"durum": "FINISHED", "ev": ev, "dep": dep, "ms_ev": a, "ms_dep": b, "iy_ev": 0, "iy_dep": 0,
                    "utc_baslama": t + "T19:00:00Z", "tr_baslama": t + "T22:00:00+03:00", "hafta": 1}
        (k / "ELC.json").write_text(json.dumps([m("2026-11-01", "X", "Y", 2, 1), m("2026-11-08", "Z", "X", 1, 1),
                                                m("2026-11-15", "X", "W", 0, 3), m("2026-11-16", "Y", "Z", 4, 0)]))
        s = V.son_maclar("en.2", "X", 10, self.tmp / "guncel")
        self.assertEqual(s["mac"], 3)
        self.assertEqual({k: s["ozet"][k] for k in ("G", "B", "M", "atilan", "yenilen", "kg")},
                         {"G": 1, "B": 1, "M": 1, "atilan": 3, "yenilen": 5, "kg": 2})
        self.assertEqual(s["satirlar"][0]["rakip"], "W")

    def test_v5_arsiv_bozulma(self):
        tk = self.tmp / "tahmin"
        r = donmus_yaz(tk)
        self.assertEqual(V.arsiv(tk)[0]["butunluk"], "SHA-256 doğrulandı")
        y = Path(r["yol"])
        j = json.loads(y.read_text())
        j["tahmin"]["olasiliklar"]["MS_X"] = 0.9
        y.write_text(json.dumps(j))
        self.assertTrue(V.arsiv(tk)[0]["butunluk"].startswith("HATA"))
        self.assertIn("hata", V.donmus_bul(1, tk))

    def test_v6_oran_donmus_tahmine_giremez(self):
        mac = {"mac_id": "nesine:1", "baslama_tr": "2026-12-01T21:00:00+03:00"}
        with self.assertRaises(OranSizintisi):
            I.dondur(mac, {"durum": "hesaplandi", "oran": 2.0}, kok=self.tmp)


class Islemler(unittest.TestCase):
    def setUp(self):
        from uygulama import islemler
        self.IS = islemler
        self.tmp = Path(tempfile.mkdtemp())

    def test_i1_dondurulmus_mac_yeniden_dondurulmez(self):
        tk = self.tmp / "tahmin"
        donmus_yaz(tk, kod=3331002)
        with self.assertRaises(self.IS.IslemHatasi):
            self.IS.dondur_mac(3331002, lig_maclari=[], kok=tk)

    def test_i2_fiyat_dondurmadan_sonraki_bulten_ister(self):
        tk = self.tmp / "tahmin"
        with self.assertRaises(self.IS.IslemHatasi):          # donmuş tahmin yok
            self.IS.fiyat_karsilastir_mac(1, kok=self.tmp, tahmin_kok=tk)
        donmus_yaz(tk, kod=1, simdi="2026-11-30T10:00:00+00:00")
        b = self.tmp / "bulten_20261130_090000"
        b.mkdir()
        (b / "mac_oncesi.json").write_text(json.dumps({"kaynak": {"cekim_utc": "2026-11-30T09:00:00+00:00"},
                                                       "futbol": [bulten_satiri(1)]}))
        from unittest import mock
        with mock.patch.object(self.IS, "datetime", wraps=self.IS.datetime) as dt:
            dt.now.return_value = I.datetime.fromisoformat("2026-11-30T11:00:00+00:00")
            with self.assertRaisesRegex(self.IS.IslemHatasi, "dondurmadan sonra"):
                self.IS.fiyat_karsilastir_mac(1, kok=self.tmp, tahmin_kok=tk)

    def test_i3_kilit(self):
        self.assertTrue(self.IS.KILIT.acquire(blocking=False))
        try:
            with self.assertRaisesRegex(self.IS.IslemHatasi, "başka bir işlem"):
                self.IS.guncel_veri_cek()
        finally:
            self.IS.KILIT.release()


class Sayfalar(unittest.TestCase):
    def test_s1_md_kacis(self):
        h = S.md("# Başlık\n<script>x</script> **kalın**\n| a | b |\n|---|---|\n| 1 | <i>2</i> |")
        self.assertNotIn("<script>", h)
        self.assertIn("<b>kalın</b>", h)
        self.assertIn("&lt;i&gt;", h)

    def test_s2_skor_p(self):
        self.assertEqual(S._skor_p("Southampton 2-1", {"skor_2_1": 0.094}), "%9,4")
        self.assertEqual(S._skor_p("3-3", {"skor_2_1": 0.1}), "hesaplanamaz")
        self.assertEqual(S._skor_p("dengeli", {"skor_2_1": 0.1}), "—")

    @unittest.skipUnless(V.bultenler(), "yerel bülten çıktısı yok")
    def test_s3_dondurulmamis_macta_fiyat_yok(self):
        donmus = {k["mac_id"] for k in V.donmus_tahminler()}
        mac = next(m for m in V.bulten_maclari(V.bultenler()[0]) if m["mac_id"] not in donmus)
        h = S.mac_sayfasi(mac["kod"])
        self.assertIn("kilitli", h)
        self.assertNotIn("Başabaş", h)
        self.assertNotIn("<th class='s'>Oran</th>", h)


if __name__ == "__main__":
    unittest.main()
