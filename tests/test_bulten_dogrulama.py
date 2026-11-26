"""B-D1..D4: bülten doğrulama aracı (dışa aktarım yardımcıları ve referans karşılaştırması) — ağsız."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / ".claude/skills/football-bulletin-fetch/scripts"))

import bulten_dogrulama as bd  # noqa: E402


def cekim_ornegi():
    def sec(no, ad, oran, durum="aktif", oyuncu=None):
        s = {"secenek_no": no, "secenek_adi": ad, "oran": oran, "durum": durum}
        if oyuncu:
            s["oyuncu"] = oyuncu
        return s
    return {"cekim": {"cekim_utc": "2026-11-26T00:02:49+00:00"},
            "maclar": [{"mac_kodu": 1, "karsilasma": "Olympiakos - AC Milan", "marketler": [
                {"market_kodu": 1, "market_adi": "Maç Sonucu", "cizgi": 0.0,
                 "secenekler": [sec(1, "1", 3.37), sec(2, "X", 3.5), sec(3, "2", 2.1)]},
                {"market_kodu": 268, "market_adi": "Handikaplı Maç Sonucu (1:0)", "cizgi": 1.0,
                 "secenekler": [sec(1, "HMS 1", 1.5), sec(2, "HMS X", 1, "kapali"), sec(3, "HMS 2", 4.2)]},
                {"market_kodu": 268, "market_adi": "Handikaplı Maç Sonucu (2:0)", "cizgi": 2.0,
                 "secenekler": [sec(1, "HMS 1", 1.1)]},
                {"market_kodu": 714, "market_adi": "Oyuncu Kaleyi Bulan Şut Çeker (Uzt. Dahil)", "cizgi": 0.0,
                 "secenekler": [sec(1, "Bailey, Leon 1+", 1.31, oyuncu={"ad": "Leon Bailey", "esik": 1}),
                                sec(2, "Bailey, Leon 2+", 3, oyuncu={"ad": "Leon Bailey", "esik": 2})]}]}]}


class BD1Yardimcilar(unittest.TestCase):
    def test_oyuncu_ve_esik(self):
        self.assertEqual(bd.oyuncu_ayir("Bailey, Leon 2+"), ("Leon Bailey", 2))
        self.assertEqual(bd.oyuncu_ayir("Leon Bailey"), ("Leon Bailey", None))
        self.assertEqual(bd.oyuncu_ayir("Camarda, Francesco 1+")[1], 1)

    def test_handikap_takimi_ve_isaret(self):
        self.assertEqual(bd.handikap_bilgisi("Handikaplı Maç Sonucu (0:1)", -1.0)["avantajli_takim"], "deplasman")
        self.assertEqual(bd.handikap_bilgisi("Korner Handikap (2,5:0)", 2.5)["avantajli_takim"], "ev")
        self.assertTrue(bd.handikap_bilgisi("Korner Handikap (0:0,5)", -0.5)["cizgi_isaretiyle_tutarli"])
        self.assertFalse(bd.handikap_bilgisi("Handikaplı Maç Sonucu (1:0)", -1.0)["cizgi_isaretiyle_tutarli"])
        self.assertIsNone(bd.handikap_bilgisi("Maç Sonucu", 0.0))


class BD2Karsilastirma(unittest.TestCase):
    def setUp(self):
        self.c = cekim_ornegi()

    def ref(self, **k):
        r = {"mac": "Olympiakos - AC Milan", "market_adi": "Maç Sonucu", "market_kodu": "1", "cizgi": "", "secenek": "1",
             "oran": "3.37", "cekim_zamani": "2026-11-26T00:10:00+00:00"}
        r.update(k)
        return r

    def test_eslesen_veri_hatasiz(self):
        r = bd.karsilastir(self.c, [self.ref(), self.ref(secenek="X", oran="3.5"),
                                    self.ref(market_adi="Handikaplı Maç Sonucu (1:0)", market_kodu="268", cizgi="1",
                                             secenek="HMS X", oran="-")])
        self.assertEqual(sum(r["ozet"].values()), 0, r["hatalar"])
        self.assertEqual(r["zaman"]["en_buyuk_fark_dk"], 7.2)

    def test_yedi_hata_turu_ayri(self):
        ref = [
            self.ref(market_adi="Toplam Korner", market_kodu="999", secenek="Alt", oran="1.8"),          # 1 eksik market
            self.ref(secenek="12", oran="1.2"),                                                         # 2 eksik seçenek
            self.ref(secenek="2", oran="2.15"),                                                         # 3 yanlış oran
            self.ref(market_adi="Oyuncu Kaleyi Bulan Şut Çeker (Uzt. Dahil)", market_kodu="714",
                     secenek="Bayley, Leon 2+", oran="3"),                                              # 4 yanlış oyuncu
            self.ref(market_kodu="2", secenek="X", oran="3.5"),                                         # 5 yanlış kod
            self.ref(market_adi="Handikaplı Maç Sonucu (1:0)", market_kodu="268", cizgi="1",
                     secenek="HMS X", oran="3.9"),                                                      # 6 durum hatası
            self.ref(), self.ref(),                                                                     # 7 tekrar (referans)
        ]
        o = bd.karsilastir(self.c, ref)["ozet"]
        for k in ("1_eksik_market", "2_eksik_secenek", "3_yanlis_oran", "4_yanlis_oyuncu",
                  "5_yanlis_market_kodu_eslesmesi", "6_durum_hatasi", "7_tekrar_eden_secenek"):
            self.assertGreaterEqual(o[k], 1, k)

    def test_ayni_ad_farkli_cizgi_birlesmez_ve_oran_yuvarlanmaz(self):
        r = bd.karsilastir(self.c, [self.ref(market_adi="Handikaplı Maç Sonucu (2:0)", market_kodu="268", cizgi="2",
                                             secenek="HMS 1", oran="1.10")])
        self.assertEqual(sum(r["ozet"].values()), 0)
        r = bd.karsilastir(self.c, [self.ref(market_adi="Handikaplı Maç Sonucu (2:0)", market_kodu="268", cizgi="2",
                                             secenek="HMS 1", oran="1.1000001")])
        self.assertEqual(r["ozet"]["3_yanlis_oran"], 1)          # tolerans yok, yuvarlama yok
        r = bd.karsilastir(self.c, [self.ref(market_adi="Handikaplı Maç Sonucu (3:0)", market_kodu="268", cizgi="3",
                                             secenek="HMS 1", oran="1.05")])
        self.assertEqual(r["ozet"]["1_eksik_market"], 1)         # 268|3 yok — 268|1 ya da 268|2 ile birleştirilmez

    def test_cekimde_tekrar_ve_zaman_bilinmiyor(self):
        c = cekim_ornegi()
        c["maclar"][0]["marketler"][0]["secenekler"].append({"secenek_no": 9, "secenek_adi": "1", "oran": 3.37, "durum": "aktif"})
        r = bd.karsilastir(c, [{"mac": "Olympiakos - AC Milan", "market_adi": "Maç Sonucu", "secenek": "1", "oran": "3.37"}])
        self.assertEqual(r["ozet"]["7_tekrar_eden_secenek"], 1)
        self.assertIn("bilinmiyor", r["zaman"]["en_buyuk_fark_dk"])


class BD3ReferansOkuma(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fi_bd_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_csv_noktali_virgul_ve_json(self):
        (self.tmp / "r.csv").write_text("Mac;Market_Adi;Secenek;Oran\nOlympiakos - AC Milan;Maç Sonucu;1;3,37\n", encoding="utf-8")
        rs = bd.referans_oku(self.tmp / "r.csv")
        self.assertEqual(rs[0]["oran"], "3,37")
        self.assertEqual(bd.karsilastir(cekim_ornegi(), rs)["ozet"]["3_yanlis_oran"], 0)
        (self.tmp / "r.json").write_text(json.dumps([{"mac_kodu": 1, "market_adi": "Maç Sonucu", "secenek": "2", "oran": 2.1}]))
        self.assertEqual(sum(bd.karsilastir(cekim_ornegi(), bd.referans_oku(self.tmp / "r.json"))["ozet"].values()), 0)


ARAYUZ = """Olympiakos - AC Milan
MAÇ SONUCU
1
Maç Sonucu
MS 1
2.52
MS X
3.06
MS 2
2.16
1
Hangi Takım Kaç Farkla Kazanır?
Ev. 1
3.50
0
2.44
GOL
1
İlk Golü Hangi Takım Atar?
1
1.89
Olmaz
12.05
2
1.74
1
YENİ
Ev Sahibi İki Yarıda da Gol
Atar
3.58
Atamaz
-
OYUNCU
1
Oyuncu Kaleyi Bulan Şut Çeker (Uzt. Dahil)
Bailey, Leon 1+
1.31
Bailey, Leon 3+
8.57
"""


class BD5ArayuzMetni(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fi_bd_"))
        (self.tmp / "r.txt").write_text(ARAYUZ, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ayrisma(self):
        r = bd.arayuz_metni_oku(self.tmp / "r.txt")
        self.assertEqual(r["sorunlar"], [])
        m = {(x["market_adi"], x["secenek"]): x for x in r["satirlar"]}
        self.assertEqual(len(r["satirlar"]), 12)
        self.assertEqual(m[("İlk Golü Hangi Takım Atar?", "1")]["oran"], "1.89")       # '1' seçenek, MBS değil
        self.assertEqual(m[("Hangi Takım Kaç Farkla Kazanır?", "0")]["oran"], "2.44")
        self.assertTrue(m[("Ev Sahibi İki Yarıda da Gol", "Atamaz")]["yeni_etiketi"])
        self.assertEqual(m[("Ev Sahibi İki Yarıda da Gol", "Atamaz")]["oran"], "-")     # kapalı korunur
        self.assertEqual(m[("Maç Sonucu", "MS 1")]["grup"], "MAÇ SONUCU")

    def test_yanlis_esik_ve_eksik_market_dogruluga_girer(self):
        rows = bd.arayuz_metni_oku(self.tmp / "r.txt")["satirlar"]
        r = bd.karsilastir(cekim_ornegi(), rows)
        self.assertEqual(r["ozet"]["8_yanlis_esik"], 1)                 # Bailey 3+ çekimde yok, 1+ ve 2+ var
        st = r["mac_istatistikleri"][1]
        self.assertEqual(st["referans_toplam_secenek"], 12)
        self.assertLess(st["dogruluk_orani(tam_dogru/referans_toplam)"], 1.0)

    def test_referans_tekrari(self):
        rows = bd.arayuz_metni_oku(self.tmp / "r.txt")["satirlar"]
        self.assertEqual(len(bd.referans_kalitesi(rows + rows[:1])["tekrar"]), 1)


@unittest.skipUnless((KOK / "output/bulten_20261126_030249/ham/mac_oncesi.json").exists(), "yerel bülten çekimi yok")
class BD4GercekCekim(unittest.TestCase):
    def test_disa_aktarim_ham_ile_tutarli(self):
        d = bd.disa_aktar(KOK / "output/bulten_20261126_030249", [3326567, 3326548])
        for m in d["maclar"]:
            self.assertEqual(m["denetim"].get("oran_ham_uyusmazligi", []), [])
            self.assertEqual(m["denetim"].get("tekrar_eden_secenek"), [])
            ham_say = sum(len(s["secenekler"]) for s in m["marketler"])
            self.assertEqual(ham_say, m["sayilar"]["toplam_secenek"])
            self.assertTrue(all(s["oran"] == s["ham"]["O"] for x in m["marketler"] for s in x["secenekler"]))




def cekim_adsiz():
    c = cekim_ornegi()
    c["maclar"][0]["marketler"].append({"market_kodu": 329, "market_adi": "market 329 (3.5)", "cizgi": 3.5, "adsiz": True,
                                        "secenekler": [{"secenek_no": 1, "secenek_adi": "seçenek 1", "oran": 1.15, "durum": "aktif"},
                                                       {"secenek_no": 2, "secenek_adi": "seçenek 2", "oran": 3.12, "durum": "aktif"}]})
    return c


class BD6AdsizAdayVeSayimlar(unittest.TestCase):
    def ref(self, sec, oran, ad="Deplasman 3,5 Gol Alt/Üst"):
        return {"mac": "Olympiakos - AC Milan", "market_adi": ad, "secenek": sec, "oran": oran}

    def test_adsiz_market_oran_dizisiyle_aday_olur_ad_verilmez(self):
        r = bd.karsilastir(cekim_adsiz(), [self.ref("Alt", "1.15"), self.ref("Üst", "3.12")])
        self.assertEqual(r["ozet"]["1_eksik_market"], 0)
        a = r["bilgi"]["adsiz_eslesme_adaylari"][0]
        self.assertEqual(a["cekim_market"][0], 329)
        self.assertIn("kesin", a["not"])
        st = r["mac_istatistikleri"][1]
        self.assertEqual((st["referans_toplam_secenek"], st["adla_eslesen_secenek"], st["adsiz_eslesme_adayi_secenek"],
                          st["gercek_eksik_secenek"]), (2, 0, 2, 0))

    def test_oran_farkliysa_aday_degil_gercek_eksik(self):
        r = bd.karsilastir(cekim_adsiz(), [self.ref("Alt", "1.16"), self.ref("Üst", "3.12")])
        self.assertEqual(r["ozet"]["1_eksik_market"], 1)
        self.assertEqual(r["mac_istatistikleri"][1]["gercek_eksik_secenek"], 2)

    def test_sayimlar_toplanir(self):
        refs = [self.ref("Alt", "1.15"), self.ref("Üst", "3.12"),
                {"mac": "Olympiakos - AC Milan", "market_adi": "Maç Sonucu", "secenek": "1", "oran": "3.37"},
                {"mac": "Olympiakos - AC Milan", "market_adi": "Maç Sonucu", "secenek": "12", "oran": "1.2"},
                {"mac": "Olympiakos - AC Milan", "market_adi": "Yok Böyle Market", "secenek": "A", "oran": "2"}]
        st = bd.karsilastir(cekim_adsiz(), refs)["mac_istatistikleri"][1]
        self.assertEqual(st["referans_toplam_secenek"], 5)
        self.assertEqual(st["adla_eslesen_secenek"] + st["adsiz_eslesme_adayi_secenek"] + st["gercek_eksik_secenek"], 5)
        self.assertEqual((st["adla_eslesen_secenek"], st["adsiz_eslesme_adayi_secenek"], st["gercek_eksik_secenek"]), (1, 2, 2))


class BD7OyuncuAdi(unittest.TestCase):
    def test_karsilastirma_adi_ham_adi_degistirmez(self):
        self.assertEqual(bd.karsilastirma_adi("İlhan Fakılı"), bd.karsilastirma_adi("Ilhan Fakili"))
        ham = "İlhan Fakılı"
        bd.karsilastirma_adi(ham)
        self.assertEqual(ham, "İlhan Fakılı")
        self.assertEqual(bd.oyuncu_ayir("Fakili, Ilhan 5+"), ("Ilhan Fakili", 5))


B = KOK / "output/bulten_20261126_030249"


@unittest.skipUnless((B / "ham/mac_oncesi.json").exists() and (B / "referans/referans_inter_escaldes_kopenhag.txt").exists(),
                     "yerel bülten / referans yok")
class BD8YeniKodlarGercekVeri(unittest.TestCase):
    """Her sözlük dışı kod için: adı uydurulmadı, tanımsız raporda; 329 yalnızca aday; MS=0 güvenli davranış korunuyor."""
    KODLAR = ("161", "327", "329", "461", "703", "704", "706", "707", "708", "710", "743", "774", "802", "804", "890")

    @classmethod
    def setUpClass(cls):
        cls.t = bd.tanimsiz_market_raporu(B)
        cls.d = bd.disa_aktar(B, [3326548, 3326567, 3326581])

    def test_her_tanimsiz_kod_raporda_ve_adi_uydurulmadi(self):
        for k in self.KODLAR:
            with self.subTest(kod=k):
                self.assertIn(k, self.t["kodlar"])
                for o in self.t["kodlar"][k]["ornekler"]:
                    self.assertTrue(o["islenmis_ad"].startswith(f"market {k}"), o["islenmis_ad"])

    def test_329_yalnizca_aday_ve_tek_dogrulama(self):
        a = bd.aday_eslemeleri()["329"]
        self.assertEqual(a["durum"], "aday")
        self.assertLess(len(a["kanitlar"]), a["gereken_dogrulama_sayisi"])
        m = next(x for x in self.d["maclar"] if x["mac_kodu"] == 3326548)
        t = next(x for x in m["tanimsiz_marketler"] if x["market_kodu"] == 329)
        self.assertEqual(t["market_adi"], "market 329 (3.5)")          # ad değiştirilmedi
        self.assertEqual(t["aday"]["aday_adi"], "Deplasman 3,5 Gol Alt/Üst")
        sozluk = json.loads((KOK / ".claude/skills/football-bulletin-fetch/data/market_sozlugu_v3.json").read_text())
        self.assertFalse(any(k.startswith("329|") for k in sozluk))    # sözlüğe eklenmedi

    def test_329_referansla_aday_eslesir(self):
        rows = []
        for f in ("referans_inter_escaldes_kopenhag.txt", "referans_olympiakos_milan.txt"):
            rows += bd.arayuz_metni_oku(B / "referans" / f)["satirlar"]
        r = bd.karsilastir(self.d, rows)
        st = r["mac_istatistikleri"][3326548]
        self.assertEqual((st["referans_toplam_secenek"], st["adla_eslesen_secenek"], st["adsiz_eslesme_adayi_secenek"],
                          st["gercek_eksik_secenek"]), (373, 371, 2, 0))
        self.assertEqual(r["mac_istatistikleri"][3326567]["adla_eslesen_secenek"], 830)
        self.assertEqual(sum(r["ozet"].values()), 0)

    def test_ms0_guvenli_davranis_ve_kesik_ad(self):
        m = next(x for x in self.d["maclar"] if x["mac_kodu"] == 3326548)
        pasif = [x for x in m["marketler"] if x["market_durumu_MS"] == 0]
        self.assertEqual(sorted(x["market_kodu"] for x in pasif), [224, 457])
        self.assertTrue(all(s["durum"] != "aktif" for x in pasif for s in x["secenekler"]))
        b = next(x for x in self.d["maclar"] if x["mac_kodu"] == 3326581)
        self.assertIn("vaclav cern", [k["ad"] for k in b["olasi_kesik_oyuncu_adlari"]])
        hamlar = {s["ham"].get("ON") for x in b["marketler"] for s in x["secenekler"]}
        self.assertIn("Vaclav Cern", hamlar)                           # ham ad korunur, düzeltilmez


if __name__ == "__main__":
    unittest.main()
