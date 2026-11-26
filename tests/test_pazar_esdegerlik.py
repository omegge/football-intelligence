"""B aşaması: market eşdeğerliği ve fiyat tutarlılığı (PE1–PE12). Olasılık üretilmediği de denetlenir."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude/skills/football-bulletin-fetch/scripts"))
import bulten_dogrulama as bd  # noqa: E402

from fi.pazar import esdegerlik as E


def sec(no, ad, oran, oyn="oynanabilir"):
    return {"secenek_no": no, "secenek_adi": ad, "oran": oran, "oynanabilirlik": oyn}


def mk(kod, ad, secenekler, cizgi=0.0, ms=1, adsiz=False, handikap=None):
    return {"market_kodu": kod, "market_adi": ad, "cizgi": cizgi, "market_durumu_MS": ms, "adsiz": adsiz,
            "handikap": handikap, "secenekler": secenekler}


def mac(marketler):
    return {"mac_kodu": 1, "karsilasma": "A - B", "turnuva": "T", "baslama_tr": "x", "marketler": marketler}


SIFIR_SIFIR = [
    mk(777, "Maç Skoru", [sec(1, "1:0", 8.0), sec(13, "0:0", 9.9), sec(14, "1:1", 5.3), sec(29, "diğer", 4.0)]),
    mk(207, "0,5 Gol Alt/Üst", [sec(1, "Alt", 10.25), sec(2, "Üst", 1.04)], cizgi=0.5),
    mk(342, "Maç Sonucu ve 1,5 Alt/Üst", [sec(i + 1, n, o) for i, (n, o) in enumerate(
        [("MS1 & Alt", 10.0), ("MSX & Alt", 11.7), ("MS2 & Alt", 9.0), ("MS1 & Üst", 2.0), ("MSX & Üst", 3.9),
         ("MS2 & Üst", 3.0)])], cizgi=1.5),
    mk(414, "Maç Sonucu ve Karşılıklı Gol", [sec(i + 1, n, o) for i, (n, o) in enumerate(
        [("MS1 & Var", 5), ("MS1 & Yok", 4), ("MSX & Var", 3.9), ("MSX & Yok", 11.75), ("MS2 & Var", 6),
         ("MS2 & Yok", 5)])]),
    mk(291, "İlk Golü Hangi Takım Atar?", [sec(1, "1", 2.0), sec(2, "Olmaz", 12.05), sec(3, "2", 1.9)]),
    mk(446, "2,5 Alt/Üst ve Karşılıklı Gol", [sec(1, "Alt & Var", 6.23), sec(2, "Üst & Var", 2.5),
                                              sec(3, "Alt & Yok", 2.6), sec(4, "Üst & Yok", 6.0)], cizgi=2.5),
]


def grup(sonuc, secenek_adi, market_kodu):
    for g in sonuc["esdegerlik_gruplari"]:
        for u in g["uyeler"]:
            if u["secenek_adi"] == secenek_adi and u["market_kodu"] == market_kodu:
                return g
    return None


class PE(unittest.TestCase):
    def test_PE1_sifir_sifir_esdegerligi(self):
        s = E.mac_denetimi(mac(SIFIR_SIFIR))
        g = grup(s, "0:0", 777)
        kodlar = {(u["market_kodu"], u["secenek_adi"]) for u in g["uyeler"]}
        self.assertEqual(kodlar, {(777, "0:0"), (207, "Alt"), (342, "MSX & Alt"), (414, "MSX & Yok"),
                                  (291, "Olmaz")})
        self.assertIn("{0-0}", g["olay"])
        # 291 'Olmaz' kontrol gerekli: kesin en yüksek fiyat listesine girmez
        self.assertEqual(g["en_yuksek_fiyat"]["oran"], 11.75)
        self.assertEqual(g["kontrol_gerekli_uyelerde_daha_yuksek_fiyat"], [12.05])
        self.assertTrue(g["olay_esdegerligi"].startswith("kesin (kesin üyeler arasında)"))

    def test_PE2_bir_bir_esdegerligi(self):
        s = E.mac_denetimi(mac(SIFIR_SIFIR))
        g = grup(s, "1:1", 777)
        self.assertEqual({(u["market_kodu"], u["secenek_adi"]) for u in g["uyeler"]},
                         {(777, "1:1"), (446, "Alt & Var")})
        self.assertEqual(g["olay_esdegerligi"], "kesin")
        self.assertAlmostEqual(g["en_yuksek_fiyat"]["basabas_esigi"], 1 / 6.23, places=6)
        self.assertIn("olasılık değildir", g["en_yuksek_fiyat"]["not"])

    def test_PE3_oynanabilir_olmayan_en_yuksek_secilmez(self):
        m = [mk(207, "0,5 Gol Alt/Üst", [sec(1, "Alt", 50.0, "durumu_dogrulanmamis"), sec(2, "Üst", 1.01)],
                cizgi=0.5, ms=0),
             mk(777, "Maç Skoru", [sec(13, "0:0", 9.0)])]
        g = grup(E.mac_denetimi(mac(m)), "0:0", 777)
        self.assertEqual(g["en_yuksek_fiyat"]["oran"], 9.0)
        self.assertEqual(g["oynanabilir_olmayan_uye_sayisi"], 1)

    def test_PE4_uzatma_dahil_eslenmez(self):
        s = E.market_olaylari(mk(709, "Oyuncu Kart Görür (Uzt. Dahil)", [sec(1, "X Y", 3.0)]), 1)
        self.assertIsNone(s[0].olay)
        self.assertIn("uzatma", s[0].eslenmeme_nedeni)

    def test_PE5_tam_cizgi_eslenmez(self):
        s = E.market_olaylari(mk(12, "2 Gol Alt/Üst", [sec(1, "Alt", 2.0), sec(2, "Üst", 1.8)], cizgi=2.0), 1)
        self.assertTrue(all(x.olay is None for x in s))
        self.assertIn("iade", s[0].eslenmeme_nedeni)

    def test_PE6_handikap_yonu(self):
        h = {"ad_baslangici": "0:1", "avantajli_takim": "deplasman", "cizgi": -1.0, "cizgi_isaretiyle_tutarli": True}
        m = [mk(268, "Handikaplı Maç Sonucu (0:1)", [sec(1, "HMS 1", 3.0), sec(2, "HMS X", 4.13), sec(3, "HMS 2", 1.24)],
                cizgi=-1.0, handikap=h),
             mk(588, "Hangi Takım Kaç Farkla Kazanır?", [sec(3, "Ev. 1", 3.5), sec(2, "Ev. 2", 6.0)])]
        s = E.mac_denetimi(mac(m))
        self.assertIsNotNone(grup(s, "HMS X", 268))
        self.assertEqual(grup(s, "HMS X", 268)["en_yuksek_fiyat"]["oran"], 4.13)
        # yön doğrulanmamışsa eşleme yapılmaz
        h2 = dict(h, cizgi_isaretiyle_tutarli=False)
        x = E.market_olaylari(mk(268, "Handikaplı Maç Sonucu (0:1)", [sec(2, "HMS X", 4.0)], -1.0, handikap=h2), 1)
        self.assertIsNone(x[0].olay)

    def test_PE7_beklenmeyen_secenek_adi(self):
        s = E.market_olaylari(mk(38, "Karşılıklı Gol", [sec(1, "Evet", 1.8), sec(2, "Yok", 2.0)]), 1)
        self.assertIsNone(s[0].olay)
        self.assertIn("uyuşmuyor", s[0].eslenmeme_nedeni)
        self.assertIsNotNone(s[1].olay)

    def test_PE8_bolumleme_ve_cifte_sans(self):
        m = [mk(1, "Maç Sonucu", [sec(1, "MS 1", 2.0), sec(2, "MS X", 3.0), sec(3, "MS 2", 4.0)]),
             mk(3, "Çifte Şans", [sec(1, "ÇŞ 1-X", 1.2), sec(2, "ÇŞ 1-2", 1.3), sec(3, "ÇŞ X-2", 1.6)])]
        b = {x["market_kodu"]: x for x in E.bolumleme_denetimi(
            [s for mm in m for s in E.market_olaylari(mm, 1)])}
        self.assertTrue(b[1]["ayrik"] and b[1]["kapsayici"])
        self.assertAlmostEqual(b[1]["ters_oran_toplami"], 1 / 2 + 1 / 3 + 1 / 4, places=6)
        self.assertFalse(b[3]["ayrik"])
        self.assertNotIn("ters_oran_toplami", b[3])

    def test_PE9_alt_kume_tutarsizligi(self):
        m = [mk(1, "Maç Sonucu", [sec(1, "MS 1", 2.0), sec(2, "MS X", 6.07), sec(3, "MS 2", 1.5)]),
             mk(272, "Maç Sonucu ve 4,5 Alt/Üst", [sec(2, "MSX & Alt", 6.05)], cizgi=4.5)]
        t = E.alt_kume_tutarsizliklari([s for mm in m for s in E.market_olaylari(mm, 1)])
        self.assertEqual(len(t), 1)
        self.assertEqual((t[0]["alt_kume"]["secenek_adi"], t[0]["ust_kume"]["secenek_adi"]), ("MSX & Alt", "MS X"))
        self.assertIn("Arbitraj ya da +EV olarak nitelendirilmez", t[0]["yorum_siniri"])

    def test_PE10_diger_tumleyen_ve_kontrol_gerekli(self):
        s = E.market_olaylari(SIFIR_SIFIR[0], 1)
        d = [x for x in s if x.secenek_adi == "diğer"][0]
        self.assertEqual(d.olay.kesinlik, "kontrol_gerekli")
        listelenen = [x.olay.maske for x in s if x.secenek_adi != "diğer"]
        for m in listelenen:
            self.assertFalse((m & d.olay.maske).any())
        self.assertTrue((d.olay.maske | listelenen[0] | listelenen[1] | listelenen[2]).all())

    def test_PE11_aday_kod_329_kesin_degil(self):
        s = E.market_olaylari(mk(329, "market 329 (3.5)", [sec(1, "seçenek 1", 1.2), sec(2, "seçenek 2", 4.0)],
                                 cizgi=3.5, adsiz=True), 1)
        self.assertTrue(all(x.olay.kesinlik == "kontrol_gerekli" for x in s))
        self.assertIn("aday", s[0].olay.neden)
        # aday, kesin bir 'Deplasman 3,5 Alt' ile aynı gruba girer ama en yüksek fiyatı belirlemez
        m = [mk(329, "market 329 (3.5)", [sec(1, "seçenek 1", 1.2)], 3.5, adsiz=True),
             mk(328, "Deplasman 3,5 Gol Alt/Üst", [sec(1, "Alt", 1.1)], 3.5)]
        g = E.mac_denetimi(mac(m))["esdegerlik_gruplari"][0]
        self.assertEqual(g["en_yuksek_fiyat"]["oran"], 1.1)
        self.assertEqual(g["olay_esdegerligi"], "kontrol gerekli")

    def test_PE12_olasilik_ve_ev_yok(self):
        sonuc = E.denetle({"cekim": {}, "maclar": [mac(SIFIR_SIFIR)]})
        metin = json.dumps(sonuc, ensure_ascii=False)
        for yasak in ('"olasilik"', '"beklenen_deger"', '"ev"', '"arbitraj"', '"deger_bahsi"'):
            self.assertNotIn(yasak, metin)
        rapor = E.rapor_md(sonuc)
        self.assertIn("olasılık içermez", rapor)
        self.assertNotIn("arbitraj fırsatı", rapor.lower())

    def test_PE13_devre_marketleri_ve_izgara(self):
        m = [mk(209, "1. Yarı 0,5 Gol Alt/Üst", [sec(1, "Alt", 2.77)], 0.5),
             mk(779, "1. Yarı Skoru", [sec(1, "0:0", 2.75)]),
             mk(416, "1. Yarı Sonucu ve 1. Yarı Karşılıklı Gol", [sec(4, "1.Y X & Yok", 2.73)]),
             mk(801, "1. Yarı / 2. Yarı Karşılıklı Gol", [sec(3, "Evet/Evet", 9.0)]),
             mk(777, "Maç Skoru", [sec(1, "15:0", 500.0)])]
        s = E.mac_denetimi(mac(m))
        g = grup(s, "0:0", 779)
        self.assertEqual(len(g["uyeler"]), 3)
        self.assertIn("devre", g["olay"])
        sk = E.market_olaylari(m[-1], 1)[0]
        self.assertIsNone(sk.olay)
        # 1Y KG × 2Y KG: tek olay, iki devre koşulu birlikte (çarpım değil, küme kesişimi)
        kk = E.market_olaylari(m[3], 1)[0].olay.maske
        self.assertTrue(((E.H1 > 0) & (E.A1 > 0) & (E.H2 > 0) & (E.A2 > 0) == kk).all())


class MarketAlanlari(unittest.TestCase):
    """PE14–PE15: dışa aktarımda periyot ve doğrulama seviyesi alanları."""

    def test_PE14_periyot(self):
        self.assertEqual(bd.periyot("Maç Sonucu"), "mac")
        self.assertEqual(bd.periyot("1. Yarı 1,5 Gol Alt/Üst"), "ilk_yari")
        self.assertEqual(bd.periyot("Deplasman 1.Y 0,5 Gol Alt/Üst"), "ilk_yari")
        self.assertEqual(bd.periyot("2. Yarı Karşılıklı Gol"), "ikinci_yari")
        self.assertEqual(bd.periyot("1. Yarı / 2. Yarı Karşılıklı Gol"), "coklu_periyot")
        self.assertEqual(bd.periyot("İlk Yarı/Maç Sonucu"), "coklu_periyot")
        self.assertEqual(bd.periyot("Ev Sahibi İki Yarıda da Gol"), "coklu_periyot")
        self.assertEqual(bd.periyot("Oyuncu Kart Görür (Uzt. Dahil)"), "uzatma_dahil")
        self.assertEqual(bd.periyot("market 329 (3.5)", adsiz=True), "bilinmiyor")

    def test_PE15_dogrulama_seviyesi(self):
        d = {"12": {"cizgiler": [2.5]}}
        self.assertEqual(bd.dogrulama_seviyesi(12, 2.5, "sozluk", None, d), "arayuz_referansi")
        self.assertEqual(bd.dogrulama_seviyesi(12, 3.5, "sozluk", None, d), "arayuz_kodu_farkli_cizgi")
        self.assertEqual(bd.dogrulama_seviyesi(11, 1.5, "sozluk", None, d), "sozluk")
        self.assertEqual(bd.dogrulama_seviyesi(99, 0, "json", None, d), "bulten_adi")
        self.assertEqual(bd.dogrulama_seviyesi(329, 3.5, "yok", {"durum": "aday"}, d), "aday")
        self.assertEqual(bd.dogrulama_seviyesi(327, 3.5, "yok", None, d), "adsiz")
        # gerçek kayıt dosyası: aday 329 ve tanımsız kodlar arayüz doğrulamasında yer almaz
        kayit = bd.arayuz_dogrulamalari()
        for kod in ("161", "327", "329", "461", "703", "704", "706", "707", "708", "710", "743", "774", "802", "804", "890"):
            self.assertNotIn(kod, kayit)


if __name__ == "__main__":
    unittest.main()
