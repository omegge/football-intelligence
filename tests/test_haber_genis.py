"""J genişletme: açık internet araştırması (HG1–HG10)."""
import unittest
from datetime import datetime, timezone

from fi.haber import genis as G

BAS = "2026-11-27T20:00:00+00:00"
MAC = {"mac_id": "m1", "karsilasma": "A - B", "lig": "L", "baslama_utc": BAS, "baslama_tr": "2026-11-27T23:00:00+03:00"}


def idd(url, sinif="ulusal_basin", yol="sayfa_okundu", durum="yok", yayin="2026-11-27T10:00:00+00:00", ilk=None,
        tur="T-24s", konu="sakatlik", takim="ev", kisi="X Oyuncu", grup=None, ar="2026-11-26T19:00:00+00:00"):
    return G.Iddia("m1", konu, takim, kisi, durum, "kısa özet", url, sinif, yol, ar, yayin, tur, ilk, grup)


class HG(unittest.TestCase):
    def test_HG1_kopya_haberler_tek_zincir(self):
        a = idd("https://a.com/1", ilk="https://kulup.com/aciklama")
        b = idd("https://b.com/2", ilk="https://kulup.com/aciklama")
        r = G.iddia_degerlendir([a, b], BAS)[0]
        self.assertEqual(r["zincir_sayisi"], 1)
        self.assertEqual(r["kopya_sayisi"], 1)
        self.assertEqual(r["dogrulama"], "dogrulanmadi")

    def test_HG2_iki_bagimsiz_zincir(self):
        r = G.iddia_degerlendir([idd("https://a.com/1"), idd("https://b.com/2", sinif="yerel_basin")], BAS)[0]
        self.assertEqual((r["zincir_sayisi"], r["dogrulama"]), (2, "iki_bagimsiz"))

    def test_HG3_resmi_tek_kaynak_yeterli(self):
        r = G.iddia_degerlendir([idd("https://kulup.com/x", sinif="resmi_kulup")], BAS)[0]
        self.assertEqual(r["dogrulama"], "resmi")

    def test_HG4_arama_ozeti_dogrulamaz(self):
        a = idd("https://kulup.com/x", sinif="resmi_kulup", yol="arama_ozeti")
        b = idd("https://forum.com/y", sinif="forum_topluluk", yol="arama_ozeti")
        r = G.iddia_degerlendir([a, b], BAS)[0]
        self.assertEqual(a.katman, "E")
        self.assertEqual(r["dogrulama"], "dogrulanmadi")

    def test_HG5_celiski_gosterilir(self):
        r = G.iddia_degerlendir([idd("https://a.com/1", durum="yok"),
                                 idd("https://b.com/2", durum="oynar", sinif="yerel_basin")], BAS)[0]
        self.assertEqual(r["dogrulama"], "celiskili")

    def test_HG6_mac_sonrasi_ve_saatsiz_dislanir(self):
        r = G.iddia_degerlendir([idd("https://a.com/1", yayin="2026-11-27T21:00:00+00:00"),
                                 idd("https://b.com/2", yayin="2026-11-27")], BAS)[0]
        self.assertEqual(r["dogrulama"], "mac_oncesi_kanit_yok")
        self.assertEqual({d["neden"] for d in r["dislanan"]}, {"mac_sonrasi", "ayni_gun_saat_yok"})

    def test_HG7_dis_gorus_karantinada(self):
        g = G.DisGorus("m1", "Site", "https://onizleme.com/a", "onizleme_tahmin_sitesi", "arama_ozeti",
                       "2026-11-26T19:00:00+00:00", None, "beraberlik", "iki takım da savunmacı",
                       karantina_sayilar={"tahmin_yuzdesi": {"X": 34}})
        with self.assertRaises(G.GenisHata):
            G.model_girdisi_denetle({"girdiler": [g]})
        with self.assertRaises(G.GenisHata):
            G.model_girdisi_denetle({"site_tahmini": 0.4})
        with self.assertRaises(G.GenisHata):
            G.DisGorus("m1", "S", "https://x.com", "bagimsiz_analist", "arama_ozeti", "2026", None, "1", "g",
                       model_girdisi=True)
        G.model_girdisi_denetle({"MS_1": 0.5, "veri_kesimi": "2026-11-25"})   # temiz girdi geçer

    def test_HG8_kurallar_uzun_metin_bahis_sitesi_nicel_etki(self):
        with self.assertRaises(G.GenisHata):
            G.Iddia("m1", "sakatlik", "ev", None, "yok", "x" * 301, "https://a.com", "ulusal_basin", "sayfa_okundu",
                    "2026", None)
        with self.assertRaises(G.GenisHata):
            idd("https://www.nesine.com/haber")
        with self.assertRaises(G.GenisHata):
            G.Iddia("m1", "sakatlik", "ev", None, "yok", "o", "https://a.com", "ulusal_basin", "sayfa_okundu",
                    "2026", None, nicel_etki="-0,05")

    def test_HG9_turlar_ve_degisim(self):
        self.assertEqual(G.arastirma_turu(BAS, datetime(2026, 11, 26, 21, tzinfo=timezone.utc)), "T-24s")
        self.assertEqual(G.arastirma_turu(BAS, datetime(2026, 11, 27, 15, tzinfo=timezone.utc)), "T-6s")
        self.assertEqual(G.arastirma_turu(BAS, datetime(2026, 11, 27, 18, 45, tzinfo=timezone.utc)), "T-90dk")
        with self.assertRaises(G.GenisHata):
            G.arastirma_turu(BAS, datetime(2026, 11, 27, 20, 1, tzinfo=timezone.utc))
        d = G.tur_karsilastir([idd("https://a.com/1", durum="yok", tur="T-24s"),
                               idd("https://a.com/2", durum="oynar", tur="T-90dk")], BAS)
        self.assertEqual(d[0]["degisim"], "durum_degisti")

    def test_HG10_rapor_on_bolum_ve_favori_orandan_belirlenmez(self):
        g = G.DisGorus("m1", "Site", "https://onizleme.com/a", "onizleme_tahmin_sitesi", "arama_ozeti",
                       "2026-11-26T19:00:00+00:00", None, "ev kazanır", "ev formda", surpriz_bekliyor=False)
        r = G.mac_raporu(MAC, [idd("https://kulup.com/x", sinif="resmi_kulup")], [g],
                         {"durum": "hesaplanamaz", "nedenler": ["lig eşlemesi yok"]})
        zorunlu = [k for k in r if k.split("_")[0] in {str(i) for i in range(1, 11)}]
        self.assertEqual(len(zorunlu), 10)                                   # madde 8'in 10 bölümü
        self.assertIn("11_sportif_cikarimlar_yorum", r)                       # yorum ayrı bölümde
        self.assertIsNone(r["8_en_onemli_surpriz_sinyali"]["favori"])
        self.assertIn("oranlarla belirlenmez", r["8_en_onemli_surpriz_sinyali"]["favori_kaynagi"])
        self.assertEqual(r["9_fiyat_karsilastirmasi"]["durum"], "yapılmadı")
        md = G.rapor_md(r)
        for i in range(1, 11):
            self.assertIn(f"## {i}.", md)
        # model hesapladıysa: favori modelden, ev aleyhine resmi sakatlık → sürpriz sinyali
        model = {"durum": "hesaplandi", "olasiliklar": {"MS_1": 0.6, "MS_X": 0.25, "MS_2": 0.15}}
        r2 = G.mac_raporu(MAC, [idd("https://kulup.com/x", sinif="resmi_kulup")], [], model)
        self.assertEqual(r2["8_en_onemli_surpriz_sinyali"]["favori"], "ev")
        self.assertIsNotNone(r2["8_en_onemli_surpriz_sinyali"]["sinyal"])

    def test_HG12_bos_arama_da_raporlanir(self):
        a = [{"sorgu": "q", "utc": "2026-11-26T19:00:00+00:00", "tur": "diger", "sonuc": "güncel kayıt yok"}]
        r = G.mac_raporu(MAC, [], [], None, aramalar=a)
        self.assertEqual(r["10_son_arastirma_ve_kaynaklar"]["son_arastirma_utc"], "2026-11-26T19:00:00+00:00")
        self.assertIn("güncel kayıt yok", G.rapor_md(r))
        self.assertEqual(r["1_dogrulanmis_son_dakika"], [])          # uydurma yok

    def test_HG13_guncel_arastirmada_bilinebilirlik(self):
        # yayın saati yok; araştırma maçtan önce ve metin bu maçı anıyor → maç öncesi bilinebilir
        a = idd("https://a.com/1", yayin=None)
        a.ilgili_mac_dogrulandi = True
        self.assertEqual(a.mac_oncesi(BAS), "mac_oncesi")
        b = idd("https://a.com/2", yayin=None)                           # maçla ilgisi doğrulanmadı
        self.assertEqual(b.mac_oncesi(BAS), "tarih_yok")
        c = idd("https://a.com/3", yayin=None, ar="2026-11-27T21:00:00+00:00")
        c.ilgili_mac_dogrulandi = True                                    # maçtan sonra bulundu
        self.assertEqual(c.mac_oncesi(BAS), "tarih_yok")

    def test_HG14_veriyle_celisen_iddia_celiskili(self):
        a = idd("https://a.com/1", konu="sonuc_form", durum=None)
        a.veri_dogrulamasi = "celisiyor"
        b = idd("https://b.com/1", konu="sonuc_form", durum=None, sinif="yerel_basin")
        r = G.iddia_degerlendir([a, b], BAS)[0]
        self.assertEqual(r["dogrulama"], "celiskili")
        self.assertEqual(r["veri_dogrulamasi"], ["celisiyor"])

    def test_HG15_suphe_ile_hazir_celisir_suphe_ile_yok_celismez(self):
        r = G.iddia_degerlendir([idd("https://a.com/1", durum="suphe"), idd("https://b.com/1", durum="hazir")], BAS)[0]
        self.assertEqual(r["dogrulama"], "celiskili")
        r = G.iddia_degerlendir([idd("https://a.com/1", durum="suphe"), idd("https://b.com/1", durum="yok")], BAS)[0]
        self.assertNotEqual(r["dogrulama"], "celiskili")

    def test_HG11_okuma_izni_varsayilan_kapali(self):
        ok, neden = G.sayfa_acilabilir_mi("https://www.reddit.com/r/soccer/x")
        self.assertFalse(ok)
        self.assertIn("arama özeti", neden)
        self.assertEqual(G.kaynak_sinifi("https://www.reddit.com/r/x"), "forum_topluluk")
        self.assertEqual(G.kaynak_sinifi("https://bilinmeyen-site.example/x"), "bilinmeyen")


if __name__ == "__main__":
    unittest.main()
