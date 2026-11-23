"""B1-B6: araştırma altyapısı testleri (ağsız). Gerçek ağ çağrısı test boyunca kilitlidir.

Çalıştırma (proje kökünden):  python3 -m unittest discover -s tests -v
"""
import io
import json
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "lib"))

from fi import girdi, http, kanit, takim_adlari  # noqa: E402
from fi.kaynaklar import clubelo, footballdata   # noqa: E402

SIMDI = "2026-11-24T10:00:00+00:00"


def _ag_yasak(*a, **k):
    raise AssertionError("Test sırasında gerçek ağ çağrısı yapıldı!")


class Temel(unittest.TestCase):
    def setUp(self):
        self._eski = urllib.request.urlopen
        urllib.request.urlopen = _ag_yasak
        self.tmp = Path(tempfile.mkdtemp(prefix="fi_altyapi_"))

    def tearDown(self):
        urllib.request.urlopen = self._eski
        shutil.rmtree(self.tmp, ignore_errors=True)


def kanit_ornegi(**ek):
    d = dict(mac_id="nesine:1", konu="elo", iddia="X ClubElo 1650", deger={"elo": 1650.0}, kaynak_adi="ClubElo",
             kaynak_url="http://api.clubelo.com/2026-11-24", erisim_zamani=SIMDI, dogrulama="veri_kaynagi",
             olcum_baslangic="2026-11-20", olcum_bitis="2026-11-27")
    d.update(ek)
    return kanit.Kanit(**d)


class B1Kanit(Temel):
    def test_gecerli_kanit_ve_depo(self):
        depo = kanit.KanitDeposu(self.tmp / "kanit.jsonl")
        k1 = depo.ekle(kanit_ornegi())
        self.assertEqual(depo.ekle(kanit_ornegi()), k1)                         # aynı kanıt iki kez yazılmaz
        self.assertEqual(len(depo.oku()), 1)
        k2 = depo.ekle(kanit_ornegi(konu="haber", iddia="Teknik direktör açıklaması", deger="…", kaynak_adi="Kulüp",
                                    kaynak_url="https://kulup.example/haber", dogrulama="resmi",
                                    yayin_tarihi="2026-11-23T18:00:00+03:00", olcum_baslangic=None, olcum_bitis=None))
        h = depo.ekle(kanit_ornegi(konu="guc_farki", iddia="Elo farkı 50", deger=50.0, kaynak_adi="hesap", kaynak_url=None,
                                   dogrulama="hesaplandi", turetildigi=[k1]))
        self.assertEqual(len(depo.oku()), 3)
        self.assertEqual({k.kimlik for k in depo.filtrele(en_az="veri_kaynagi")}, {k1, k2})
        self.assertEqual(depo.ozet()["dogrulama"], {"veri_kaynagi": 1, "resmi": 1, "hesaplandi": 1})
        self.assertTrue(h)

    def test_kurallar(self):
        hatali = [
            dict(kaynak_url=None),                                                   # kaynaksız sayı
            dict(dogrulama="emin"),                                                  # geçersiz seviye
            dict(dogrulama="dogrulanamadi"),                                         # doğrulanamadı + değer
            dict(deger=None),                                                        # değersiz kanıt
            dict(konu="oran"),                                                       # oran kanıt olamaz
            dict(kaynak_url="https://cdnbulten.nesine.com/api/bulten/getprebultenfull"),
            dict(deger={"ev": {"oran": 2.1}}),                                       # iç içe oran alanı
            dict(yayin_tarihi="2026-11-25"),                                         # yayın erişimden sonra
            dict(olcum_baslangic="2026-11-28"),                                      # ölçüm dönemi ters
            dict(erisim_zamani="dün"),
            dict(kaynak_url="ftp://x/y"),
            dict(dogrulama="hesaplandi", kaynak_url=None),                          # türetildiği yok
        ]
        for ek in hatali:
            with self.assertRaises(kanit.KanitHatasi, msg=str(ek)):
                kanit_ornegi(**ek).dogrula()
        kanit_ornegi(dogrulama="dogrulanamadi", deger=None, iddia="Kesin 11 bulunamadı").dogrula()

    def test_turetildigi_depoda_olmali(self):
        depo = kanit.KanitDeposu(self.tmp / "k.jsonl")
        with self.assertRaises(kanit.KanitHatasi):
            depo.ekle(kanit_ornegi(dogrulama="hesaplandi", kaynak_url=None, turetildigi=["yok123"]))


class B2TakimAdlari(Temel):
    def eslestirici(self, kayitlar=None):
        p = self.tmp / "eslemeler.json"
        p.write_text(json.dumps(kayitlar or []), encoding="utf-8")
        return takim_adlari.TakimEslestirici(p)

    def test_normallestirme(self):
        n = takim_adlari.normallestir
        self.assertEqual(n("Fenerbahçe SK"), "fenerbahce")
        self.assertEqual(n("İstanbul Başakşehir FK"), "istanbul basaksehir")
        self.assertEqual(n("Man Utd"), "man united")
        self.assertEqual(n("AC Monza"), "monza")

    def test_kesin_yalnizca_birebir_ve_tek(self):
        e = self.eslestirici()
        r = e.eslestir("Fenerbahçe", "clubelo", ["Fenerbahce", "Galatasaray", "Besiktas"])
        self.assertEqual((r.durum, r.kaynak_adi, r.kullanilabilir), ("kesin", "Fenerbahce", True))
        r = e.eslestir("Man. Utd", "clubelo", ["Man United", "Man City"])         # belgelenmiş kısaltma: utd -> united
        self.assertEqual((r.durum, r.kaynak_adi), ("kesin", "Man United"))
        r = e.eslestir("Man. Utd", "clubelo", ["Manchester United", "Man City"])  # benzer ama birebir değil
        self.assertEqual(r.durum, "belirsiz")
        self.assertFalse(r.kullanilabilir)
        self.assertEqual(r.alternatifler[0]["ad"], "Manchester United")
        r = e.eslestir("Nantes", "x", ["FC Nantes", "Nantes"])                    # iki aday aynı ada normalleşiyor
        self.assertEqual(r.durum, "belirsiz")
        r = e.eslestir("Galatasaray U19", "x", ["Galatasaray"])                     # gençler ≠ A takım
        self.assertNotEqual(r.durum, "kesin")
        r = e.eslestir("Grosseto", "x", ["Guidonia", "Monterosi"])
        self.assertEqual(r.durum, "yok")

    def test_onayli_eslesme(self):
        e = self.eslestirici()
        e.onay_ekle("Chelmsford C.", "footballdata", "Chelmsford City", ulke="ENG")
        e2 = takim_adlari.TakimEslestirici(e.dosya)                                 # dosyaya kaydedildi
        r = e2.eslestir("Chelmsford C.", "footballdata", ["Chelmsford City", "Maidstone"], ulke="ENG")
        self.assertEqual((r.durum, r.kaynak_adi), ("onayli", "Chelmsford City"))
        r = e2.eslestir("Chelmsford C.", "footballdata", ["Başka Takım"], ulke="ENG")
        self.assertEqual(r.durum, "belirsiz")                                      # onaylı ad listede yok
        with self.assertRaises(ValueError):
            e2.onay_ekle("Chelmsford C.", "footballdata", "X", ulke="ENG")

    def test_proje_esleme_dosyasi_gecerli(self):
        self.assertIsInstance(json.loads(takim_adlari.ESLEME_DOSYASI.read_text(encoding="utf-8")), list)


def bulten_klasoru(tmp: Path) -> Path:
    k = tmp / "bulten_x"
    k.mkdir()
    futbol = [{"kod": 1, "nid": 1, "akis": "mac_oncesi", "lig": "Süper Lig", "lig_ulke": "TR", "ev": "Galatasaray",
               "deplasman": "Fenerbahçe", "karsilasma": "Galatasaray - Fenerbahçe", "baslama_tr": "2026-11-24T20:00:00+03:00",
               "mac_mbs": 1, "canli_kodu": 900, "dogrulanmamis_eslesme": False,
               "marketler": [{"market_adi": "Maç Sonucu", "secenekler": [{"oran": 2.1, "oran_ham": 2.1}]}]},
              {"kod": 2, "nid": 2, "ev": "US Grosseto", "deplasman": "Monterosi T.", "karsilasma": "US Grosseto - Monterosi T.",
               "baslama_tr": "2026-11-24T22:30:00+03:00", "dogrulanmamis_eslesme": True, "isim_celiskisi": True,
               "marketler": [{"secenekler": [{"oran": 3.0}]}]}]
    (k / "mac_oncesi.json").write_text(json.dumps({"kaynak": {"cekim_tr": "2026-11-24T10:00:00+03:00"}, "futbol": futbol,
                                                   "marketsiz_futbol": [{"kod": 3, "nid": 3, "ev": "A Gençler", "deplasman": "B Gençler",
                                                                         "karsilasma": "A Gençler - B Gençler", "marketler": []}]}),
                                       encoding="utf-8")
    (k / "canli.json").write_text(json.dumps({"kaynak": {}, "futbol": [{"kod": 7, "ev": "X", "deplasman": "Y",
                                                                       "karsilasma": "X - Y", "marketler": [{"secenekler": [{"oran": 1.5}]}]}]}),
                                  encoding="utf-8")
    return k


class B3OransizGirdi(Temel):
    def test_fikstur_oran_icermez(self):
        k = bulten_klasoru(self.tmp)
        yol = girdi.fikstur_yaz(k)
        metin = yol.read_text(encoding="utf-8")
        for yasak in ('"oran"', '"oran_ham"', "marketler", "secenek", "mac_mbs", "2.1"):
            self.assertNotIn(yasak, metin)
        f = girdi.fikstur_oku(yol)
        self.assertEqual([m["mac_id"] for m in f["maclar"]], ["nesine:1", "nesine:2", "nesine:3", "nesine:7"])
        self.assertEqual([m["ewma_kaydi"] for m in f["maclar"]], [False, False, True, False])
        self.assertIn("sha256", f["kaynaklar"]["mac_oncesi"])

    def test_sizinti_yakalanir(self):
        with self.assertRaises(girdi.OranSizintisi):
            girdi.oransiz_mi({"maclar": [{"ev": "A", "MS 1 oran": 2.0}]})
        with self.assertRaises(girdi.OranSizintisi):
            girdi.oransiz_mi([{"x": {"market_adi": "Maç Sonucu"}}])
        k = bulten_klasoru(self.tmp)
        with self.assertRaises(girdi.OranSizintisi):                               # bülten dosyası doğrudan okunamaz
            girdi.fikstur_oku(k / "mac_oncesi.json")

    def test_mac_bul_ve_arastirma_klasoru(self):
        f = girdi.fikstur_olustur(bulten_klasoru(self.tmp))
        self.assertEqual([m["kod"] for m in girdi.mac_bul(f, "nesine:1")], [1])
        self.assertEqual([m["kod"] for m in girdi.mac_bul(f, "900")], [1])          # canlı kodu ile
        self.assertEqual([m["kod"] for m in girdi.mac_bul(f, "fenerbahçe")], [1])
        d = girdi.arastirma_klasoru_hazirla(f, girdi.mac_bul(f, "2")[0], self.tmp / "analiz")
        g = json.loads((d / "girdi.json").read_text(encoding="utf-8"))
        self.assertIn("kupona alınmamalı", g["uyari"])
        self.assertTrue((d / "kanit.jsonl").exists())
        girdi.oransiz_mi(g)


class SahteYanit(io.BytesIO):
    def __init__(self, govde, durum=200, tur="text/csv"):
        super().__init__(govde)
        self.status = durum
        self.headers = {"Content-Type": tur}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class SahteAcici:
    def __init__(self, *cevaplar):
        self.cevaplar = list(cevaplar)
        self.istekler = []

    def __call__(self, istek, zaman_asimi):
        self.istekler.append(istek)
        c = self.cevaplar.pop(0)
        if isinstance(c, Exception):
            raise c
        return c


class SahteSaat:
    def __init__(self):
        self.t = 100.0
        self.uykular = []

    def saat(self):
        return self.t

    def uyku(self, s):
        self.uykular.append(round(s, 2))
        self.t += s


class B4Http(Temel):
    def istemci(self, acici, simdi=datetime(2026, 11, 24, 10, tzinfo=timezone.utc)):
        s = SahteSaat()
        self.zaman = {"simdi": simdi}
        return http.VeriIstemcisi(self.tmp / "onbellek", acici=acici, saat=s.saat, uyku=s.uyku,
                                  simdi=lambda: self.zaman["simdi"]), s

    def test_izinsiz_host_istek_atmaz(self):
        a = SahteAcici()
        ist, _ = self.istemci(a)
        for kaynak, url in (("clubelo", "https://cdnbulten.nesine.com/api/bulten/getprebultenfull"),
                            ("footballdata", "http://api.clubelo.com/2026-11-24"), ("yok", "http://x.com/"),
                            ("clubelo", "file:///etc/passwd")):
            with self.assertRaises(http.ErisimHatasi):
                ist.getir(kaynak, url)
        self.assertEqual(a.istekler, [])

    def test_basari_meta_onbellek_ve_hiz_siniri(self):
        a = SahteAcici(SahteYanit(b"Rank,Club\n1,X\n"), SahteYanit(b"Rank,Club\n2,Y\n"))
        ist, s = self.istemci(a)
        y = ist.getir("clubelo", "http://api.clubelo.com/2026-11-24")
        self.assertEqual((y.meta["http_durumu"], y.meta["bayt"], y.meta["onbellekten"]), (200, 14, False))
        self.assertEqual(len(y.meta["sha256"]), 64)
        self.assertTrue(y.meta["erisim_tr"].endswith("+03:00"))
        self.assertIn("FootballIntelligence", a.istekler[0].get_header("User-agent"))
        y2 = ist.getir("clubelo", "http://api.clubelo.com/2026-11-24")              # önbellekten, istek yok
        self.assertTrue(y2.meta["onbellekten"])
        self.assertEqual(len(a.istekler), 1)
        ist.getir("clubelo", "http://api.clubelo.com/2026-11-25")                   # aynı host: 2 sn bekleme
        self.assertEqual(s.uykular, [2.0])
        self.zaman["simdi"] += timedelta(hours=13)                                  # önbellek süresi doldu
        a.cevaplar.append(SahteYanit(b"Rank,Club\n3,Z\n"))
        self.assertFalse(ist.getir("clubelo", "http://api.clubelo.com/2026-11-24").meta["onbellekten"])

    def test_engel_yeniden_denenmez(self):
        for hata in (urllib.error.HTTPError("u", 403, "Forbidden", {}, None),
                     urllib.error.HTTPError("u", 429, "Too Many", {}, None),
                     urllib.error.URLError("Tunnel connection failed: 403 Forbidden")):
            a = SahteAcici(hata, SahteYanit(b"x"))
            ist, _ = self.istemci(a)
            with self.assertRaises(http.ErisimHatasi) as c:
                ist.getir("footballdata", "https://www.football-data.co.uk/mmz4281/2526/T1.csv")
            self.assertTrue(c.exception.engel)
            self.assertEqual(len(a.istekler), 1)

    def test_html_engel_sayilir(self):
        a = SahteAcici(SahteYanit(b"<!DOCTYPE html><title>Just a moment</title>", tur="text/html"))
        ist, _ = self.istemci(a)
        with self.assertRaises(http.ErisimHatasi) as c:
            ist.getir("footballdata", "https://www.football-data.co.uk/mmz4281/2526/T1.csv")
        self.assertTrue(c.exception.engel)

    def test_gecici_hata_bir_kez_denenir(self):
        a = SahteAcici(urllib.error.HTTPError("u", 503, "x", {}, None), SahteYanit(b"Div,Date\n"))
        ist, s = self.istemci(a)
        self.assertEqual(ist.getir("footballdata", "https://www.football-data.co.uk/mmz4281/2526/T1.csv").meta["deneme"], 2)
        a = SahteAcici(TimeoutError("zaman aşımı"), TimeoutError("zaman aşımı"))
        ist, _ = self.istemci(a)
        with self.assertRaises(http.ErisimHatasi) as c:
            ist.getir("clubelo", "http://api.clubelo.com/x")
        self.assertFalse(c.exception.engel)
        self.assertEqual(len(a.istekler), 2)


CLUBELO_CSV = """Rank,Club,Country,Level,Elo,From,To
1,Liverpool,ENG,1,2010.5,2026-11-20,2026-11-27
None,Fenerbahce,TUR,1,1650.25,2026-11-18,2026-11-24
None,Fenerbahce,TUR,1,1660.00,2026-11-25,2026-11-30
"""

FD_ANA = ("Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HTR,HS,AS,HST,AST,HF,AF,HC,AC,HY,AY,HR,AR,"
          "B365H,B365D,B365A,PSH,MaxH,AvgH,B365>2.5,B365<2.5,AHh,B365AHH,PSCH,AvgC<2.5\n"
          "T1,08/08/2026,19:00,Galatasaray,Fenerbahce,2,1,H,1,0,H,15,9,6,3,10,12,7,4,2,3,0,0,1.9,3.5,4.2,1.95,2,1.9,1.7,2.1,-0.5,1.9,1.9,2.0\n"
          "T1,15/08/2026,20:00,Fenerbahce,Besiktas,0,0,D,0,0,D,11,8,3,2,14,9,5,5,1,2,0,1,2.0,3.4,3.9,2.0,2.1,2.0,1.8,2.0,-0.25,1.9,2.0,1.9\n"
          ",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n")
FD_EK = ("Country,League,Season,Date,Time,Home,Away,HG,AG,Res,PSCH,PSCD,PSCA,MaxCH,AvgCH\n"
         "Brazil,Serie A,2026,01/11/2026,22:00,Flamengo,Palmeiras,1,1,D,2.1,3.2,3.6,2.2,2.1\n")


class B5Kaynaklar(Temel):
    def test_clubelo(self):
        s = clubelo.ayristir(CLUBELO_CSV)
        self.assertEqual(len(s), 3)
        self.assertEqual((s[1]["kulup"], s[1]["elo"], s[1]["sira"]), ("Fenerbahce", 1650.25, None))
        self.assertEqual([r["elo"] for r in clubelo.gune_gore(s, date(2026, 11, 24)) if r["kulup"] == "Fenerbahce"], [1650.25])
        meta = {"url": clubelo.gun_url(date(2026, 11, 24)), "erisim_utc": SIMDI, "sha256": "a" * 64}
        depo = kanit.KanitDeposu(self.tmp / "k.jsonl")
        depo.ekle(clubelo.elo_kaniti(s[1], "nesine:1", meta))
        k = depo.oku()[0]
        self.assertEqual((k.olcum_baslangic, k.olcum_bitis, k.dogrulama), ("2026-11-18", "2026-11-24", "veri_kaynagi"))
        with self.assertRaises(clubelo.BicimHatasi):
            clubelo.ayristir("a,b\n1,2\n")
        with self.assertRaises(clubelo.BicimHatasi):
            clubelo.ayristir("Rank,Club,Country,Level,Elo,From,To\n1,X,ENG,1,abc,2026-01-01,2026-01-02\n")

    def test_footballdata_oranlar_atilir(self):
        r = footballdata.ayristir(FD_ANA)
        self.assertEqual((r["bicim"], len(r["maclar"])), ("ana", 2))
        m = r["maclar"][0]
        self.assertEqual((m["tarih"], m["ev"], m["ev_gol"], m["iy_ev_gol"], m["ev_korner"], m["dep_sari"]),
                         ("2026-08-08", "Galatasaray", 2, 1, 7, 3))
        for mac in r["maclar"]:
            girdi.oransiz_mi(mac)
            self.assertFalse([k for k in mac if any(p in k for p in ("B365", "PS", "Max", "Avg", "AH"))])
        self.assertIn("B365H", r["atilan_sutunlar"])
        self.assertEqual(r["tanimsiz_atilan"], [])                                  # atılan her sütun oran deseni
        e = footballdata.ayristir(FD_EK)
        self.assertEqual((e["bicim"], e["maclar"][0]["ev"], e["maclar"][0]["dep_gol"]), ("ek", "Flamengo", 1))
        self.assertNotIn("PSCH", json.dumps(e["maclar"]))
        with self.assertRaises(footballdata.BicimHatasi):
            footballdata.ayristir("x,y\n1,2\n")

    def test_footballdata_takim_maclari_ve_url(self):
        r = footballdata.ayristir(FD_ANA)
        s = footballdata.takim_maclari(r["maclar"], "Fenerbahce")
        self.assertEqual([m["tarih"] for m in s], ["2026-08-15", "2026-08-08"])
        self.assertEqual(len(footballdata.takim_maclari(r["maclar"], "Fenerbahce", once="2026-08-15")), 1)
        self.assertEqual(footballdata.takim_adlari(r["maclar"]), ["Besiktas", "Fenerbahce", "Galatasaray"])
        self.assertEqual(footballdata.ana_url("2627", "T1"), "https://www.football-data.co.uk/mmz4281/2627/T1.csv")
        self.assertEqual(footballdata.ek_url("BRA"), "https://www.football-data.co.uk/new/BRA.csv")
        for bad in (lambda: footballdata.ana_url("26", "T1"), lambda: footballdata.ana_url("2627", "../x"),
                    lambda: footballdata.ek_url("br")):
            with self.assertRaises(ValueError):
                bad()


class B6Bagimsizlik(Temel):
    def test_altyapi_nesine_ve_bulteni_okumaz(self):
        kaynak = "".join(p.read_text(encoding="utf-8") for p in (KOK / "lib" / "fi").rglob("*.py"))
        self.assertNotIn("nesine_bulletin", kaynak)
        self.assertNotIn("getprebultenfull", kaynak)
        for k in http.KAYNAKLAR.values():
            self.assertFalse([h for h in k["hostlar"] if "nesine" in h])

    def test_footy_skills_kodu_kopyalanmadi(self):
        imzalar = ("advocate_check", "note_check", "football.oracle", "facts.py", "run_collection", "launch_browser")
        for p in list((KOK / "lib").rglob("*.py")) + list((KOK / ".claude").rglob("*.py")):
            metin = p.read_text(encoding="utf-8")
            for i in imzalar:
                self.assertNotIn(i, metin, f"{p.name}: {i}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
