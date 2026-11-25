"""H1-H8: haber katmanı testleri — tamamen ağsız (urllib.request.urlopen test boyunca kilitli; okuyucuya sahte açıcı)."""
import io
import json
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "lib"))

from fi.kanit import Kanit, KanitHatasi                                     # noqa: E402
from fi.haber import kaynak, kimlik, sayfa, zaman                           # noqa: E402
from fi.haber.arastirma import AramaOturumu, ModHatasi                       # noqa: E402
from fi.haber.kanit_kaydi import DurumKaydi, HaberGirdisi, bagimsiz_mi, haber_kaniti, teyit_et  # noqa: E402
from fi.haber.kaynak import HostKaydi, KaynakHatasi, KaynakKaydi            # noqa: E402
from fi.haber.okuyucu import GuvenliOkuyucu, HostEngelli                    # noqa: E402


def _ag_yasak(*a, **k):
    raise AssertionError("Test sırasında gerçek ağ çağrısı yapıldı!")


def kayit_ornegi():
    return KaynakKaydi([
        HostKaydi("www.kulup-a.example", "resmi_kulup", "kullanilabilir", "test", "xx.1", "Kulüp A", "grupA",
                  ["wikipedia", "ana_sayfa_basligi"]),
        HostKaydi("www.gazete1.example", "yerel_basin", "kullanilabilir", "test", "xx.1", None, "MedyaGrubu"),
        HostKaydi("www.gazete2.example", "yerel_basin", "kullanilabilir", "test", "xx.1", None, "MedyaGrubu"),
        HostKaydi("www.gazete3.example", "ulusal_basin", "kullanilabilir", "test", "xx.1", None, "BaskaGrup"),
        HostKaydi("www.engelli.example", "resmi_kulup", "engelli", "robots AI engeli", "xx.1", "Kulüp B", None,
                  ["wikipedia", "ana_sayfa_basligi"], robots_ai_engeli=True),
        HostKaydi("www.belirsiz.example", "resmi_kulup", "belirsiz", "koşullar okunamadı", "xx.1", "Kulüp C"),
        HostKaydi("www.tekisaret.example", "resmi_kulup", "dogrulanmamis", "tek işaret", "xx.1", "Kulüp D", None,
                  ["ana_sayfa_basligi"]),
    ])


class Temel(unittest.TestCase):
    def setUp(self):
        self._eski = urllib.request.urlopen
        urllib.request.urlopen = _ag_yasak
        self.tmp = Path(tempfile.mkdtemp(prefix="fi_haber_"))

    def tearDown(self):
        urllib.request.urlopen = self._eski
        shutil.rmtree(self.tmp, ignore_errors=True)


class H1KaynakUyum(Temel):
    def test_robots_ai_engeli(self):
        self.assertTrue(kaynak.robots_ai_engeli("User-agent: ClaudeBot\nDisallow: /\n"))
        self.assertFalse(kaynak.robots_ai_engeli("User-agent: ClaudeBot\nAllow: /\n\nUser-agent: *\nDisallow: /admin\n"))
        # boş satır kurallardan önce: grup bitmez (St. Pauli tipi yazım)
        self.assertTrue(kaynak.robots_ai_engeli("User-agent: GPTBot\nUser-agent: anthropic-ai\nUser-agent: Applebot\n\nDisallow: /\n"))
        self.assertFalse(kaynak.robots_ai_engeli("User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nDisallow: /x\n"))

    def test_kosul_otomatik_yasak_dort_dil(self):
        for metin in ("Any automated programmes, applets, bots or similar technologies may not be used to access the content.",
                      "You agree not to use the site for extracting, scraping, crawling or collecting data.",
                      "Queda prohibido utilizar secuencias de comandos automatizados o screen scraping.",
                      "È vietato accedere ai Servizi mediante strumenti automatici."):
            self.assertTrue(kaynak.kosul_otomatik_yasak(metin), metin)
        self.assertEqual(kaynak.kosul_otomatik_yasak("Eine Vervielfältigung ist nur mit schriftlicher Genehmigung möglich."), [])

    def test_siniflandir_ve_kayit_kurallari(self):
        s = lambda **k: kaynak.siniflandir(**{"ana_http": 200, "robots_ai": False, "bot_isareti": False, "icerik_js": False,
                                              "kosul_okundu": True, "kosul_yasaklari": [], "kimlik_isaret_sayisi": 2,
                                              "tur": "resmi_kulup", **k})[0]
        self.assertEqual(s(), "kullanilabilir")
        self.assertEqual(s(ana_http=403), "engelli")
        self.assertEqual(s(robots_ai=True), "engelli")
        self.assertEqual(s(kosul_yasaklari=["no scraping"]), "engelli")
        self.assertEqual(s(icerik_js=True), "belirsiz")
        self.assertEqual(s(kosul_okundu=False), "belirsiz")
        self.assertEqual(s(kimlik_isaret_sayisi=1), "dogrulanmamis")
        with self.assertRaises(KaynakHatasi):      # resmî kulüp tek işaretle kullanılabilir olamaz
            HostKaydi("x.example", "resmi_kulup", "kullanilabilir", "g", kimlik_isaretleri=["wikipedia"]).dogrula()
        with self.assertRaises(KaynakHatasi):      # MK-1
            HostKaydi("bulten.nesine.com", "veri_kaynagi", "kullanilabilir", "g").dogrula()

    def test_depo_kaydi_40_host(self):
        k = KaynakKaydi.yukle()
        say = {s: len(v) for s, v in k.sinifa_gore().items()}
        self.assertEqual(sum(say.values()), 40)
        self.assertEqual(say, {"kullanilabilir": 14, "dogrulanmamis": 3, "engelli": 15, "belirsiz": 8})
        for h in ("www.bundesliga.com", "www.fcstpauli.com", "www.realmadrid.com", "www.kicker.de", "www.tsg-hoffenheim.de"):
            self.assertFalse(k.okunabilir_mi(h), h)
        self.assertTrue(k.okunabilir_mi("www.brentfordfc.com"))
        self.assertEqual(k.get("www.thestar.co.uk").yayinci_grubu, k.get("www.sussexexpress.co.uk").yayinci_grubu)


class H2Kimlik(Temel):
    def test_wikipedia_ve_baslik(self):
        self.assertEqual(kimlik.wikipedia_websitesi("{{Infobox football club\n| website = {{URL|https://www.sv98.de/|sv98.de}}\n}}\n"), "sv98.de")
        self.assertEqual(kimlik.wikipedia_websitesi("{{Infobox football club\n| website = {{Official URL}}\n}}\n"), "wikidata")
        self.assertEqual(kimlik.wikipedia_websitesi("{{Infobox\n| name = x\n}}\n==Links==\n{{Official website|https://store.x.com}}"), None)
        self.assertEqual(kimlik.kayitli_alan("https://www.thestar.co.uk/sport"), "thestar.co.uk")
        self.assertTrue(kimlik.baslik_kulubu_adlandiriyor_mu("SC Freiburg | Die offizielle Website", "SC Freiburg"))
        self.assertFalse(kimlik.baslik_kulubu_adlandiriyor_mu("Latest News | The Star", "Sheffield United FC"))

    def test_alan_adi_durumu(self):
        self.assertEqual(kimlik.alan_adi_durumu("www.sv98.de", "sv98.de", "SV Darmstadt 1898 e.V.", "SV Darmstadt 98")["durum"], "dogrulandi")
        self.assertEqual(kimlik.alan_adi_durumu("www.sslazio.it", "wikidata", "Home | S.S. Lazio", "SS Lazio")["durum"], "tek_isaret")
        self.assertEqual(kimlik.alan_adi_durumu("www.sahte-kulup.example", "gercek-kulup.com", "Gerçek Kulüp", "Gerçek Kulüp")["durum"],
                         "dogrulanamadi")     # Wikipedia başka alan adı gösteriyorsa başlık tek başına yetmez


class SahteYanit(io.BytesIO):
    def __init__(self, govde: bytes, url: str, status=200):
        super().__init__(govde)
        self._url, self.status = url, status

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


HTML = """<html><head><title>Kulüp A | Official Website</title>
<script type="application/ld+json">{"datePublished":"2024-03-09T13:00:00+00:00","dateModified":"2024-03-09T13:00:00+00:00"}</script>
</head><body><p>09.03.2024 Team news: Our captain is ruled out with a thigh injury and will miss Sunday's game.</p>
<p>The coach said rotation is possible. """ + "x " * 150 + """</p>
<div>Ähnliche Artikel 24.11.2026 Two players are back in the squad after long injuries for the next match.</div></body></html>"""


class H3Okuyucu(Temel):
    def okuyucu(self, acici, uykular=None):
        return GuvenliOkuyucu(kayit_ornegi(), acici=acici, saat=lambda: 0.0,
                              uyku=(uykular.append if uykular is not None else (lambda s: None)))

    def test_engelli_belirsiz_kayitsiz_hosta_istek_yok(self):
        cagri = []
        o = self.okuyucu(lambda istek, t: cagri.append(istek))
        for url in ("https://www.engelli.example/a", "https://www.belirsiz.example/a", "https://www.tekisaret.example/a",
                    "https://bilinmeyen.example/a", "http://www.kulup-a.example/a"):
            with self.assertRaises(HostEngelli):
                o.oku(url)
        self.assertEqual(cagri, [])

    def test_basarili_okuma_kenar_kesilir(self):
        basliklar = []
        def acici(istek, t):
            basliklar.append(istek.get_header("User-agent"))
            return SahteYanit(HTML.encode(), istek.full_url)
        o = self.okuyucu(acici)
        s = o.oku("https://www.kulup-a.example/news/1")
        self.assertTrue(basliklar[0].startswith("FootballIntelligence/"))     # dürüst UA, tarayıcı taklidi yok
        self.assertTrue(s.basarili)
        self.assertTrue(s.kenar_kesildi)
        self.assertNotIn("2026", s.metin)
        self.assertEqual(s.gorunur_tarihler, ["2024-03-09"])
        self.assertEqual(s.zaman_adaylari["yayin"][0], ("jsonld", "2024-03-09T13:00:00+00:00"))
        self.assertEqual(len(s.sayfa_sha256), 64)

    def test_retry_after_zaman_asimi_engel_yonlendirme(self):
        uykular, n = [], {"i": 0}
        def acici(istek, t):
            n["i"] += 1
            if n["i"] == 1:
                h = Message(); h["Retry-After"] = "7"
                raise urllib.error.HTTPError(istek.full_url, 429, "Too Many", h, None)
            return SahteYanit(HTML.encode(), istek.full_url)
        s = self.okuyucu(acici, uykular).oku("https://www.kulup-a.example/x")
        self.assertTrue(s.basarili)
        self.assertIn(7.0, uykular)
        self.assertEqual(n["i"], 2)
        def zaman_asimi(istek, t):
            raise TimeoutError()
        s = self.okuyucu(zaman_asimi).oku("https://www.kulup-a.example/y")
        self.assertIn("zaman aşımı", s.hata)
        n2 = {"i": 0}
        def yasak(istek, t):
            n2["i"] += 1
            raise urllib.error.HTTPError(istek.full_url, 403, "Forbidden", Message(), None)
        s = self.okuyucu(yasak).oku("https://www.kulup-a.example/z")
        self.assertIn("aşılmaz", s.hata)
        self.assertEqual(n2["i"], 1)                         # 403'te yeniden deneme yok
        s = self.okuyucu(lambda istek, t: SahteYanit(b"x", "https://www.engelli.example/q")).oku("https://www.kulup-a.example/r")
        self.assertIn("yönlendirme", s.hata)


class H4Zaman(Temel):
    def test_durumlar(self):
        B = "2024-03-10T16:30:00+00:00"
        Y = zaman.YayinZamani
        self.assertEqual(zaman.mac_oncesi_durumu(Y("2024-03-09T13:00:00+00:00", "jsonld", "saat"), B), "mac_oncesi_dogrulandi")
        self.assertEqual(zaman.mac_oncesi_durumu(Y("2024-03-10T18:00:00+00:00", "jsonld", "saat"), B), "mac_sonrasi")
        self.assertEqual(zaman.mac_oncesi_durumu(Y("2024-03-10", "gorunur_tarih", "gun"), B), "ayni_gun_saat_yok")
        self.assertEqual(zaman.mac_oncesi_durumu(Y("2024-03-09", "gorunur_tarih", "gun"), B), "mac_oncesi_dogrulandi")
        self.assertEqual(zaman.mac_oncesi_durumu(Y("2024-03-11", "gorunur_tarih", "gun"), B), "mac_sonrasi")
        self.assertEqual(zaman.mac_oncesi_durumu(Y(None, "yok", "yok"), B), "tarih_yok")
        self.assertEqual(zaman.mac_oncesi_durumu(Y("2024-03-09T13:00:00+00:00", "jsonld", "saat"), B,
                                                 Y("2024-03-10T19:00:00+00:00", "jsonld", "saat")), "guncelleme_mac_sonrasi")

    def test_coz_oncelik(self):
        y, g = zaman.coz({"yayin": [("jsonld", "2024-12-15"), ("meta", "2024-12-15T09:00:00+01:00")], "guncelleme": []}, [])
        self.assertEqual((y.kaynak, y.hassasiyet, y.deger), ("meta", "saat", "2024-12-15T08:00:00+00:00"))
        y, _ = zaman.coz({"yayin": [("jsonld", "2024-12-15")]}, [])
        self.assertEqual((y.hassasiyet, y.deger), ("gun", "2024-12-15"))
        y, _ = zaman.coz({"yayin": []}, ["2023-11-23"])
        self.assertEqual((y.kaynak, y.hassasiyet), ("gorunur_tarih", "gun"))
        y, _ = zaman.coz({"yayin": [("meta", "2024-12-15T09:00:00")]}, [])      # saat dilimsiz saat → yalnızca gün
        self.assertEqual(y.hassasiyet, "gun")

    def test_gorunur_tarih_bicimleri(self):
        self.assertEqual(sayfa.gorunur_tarihler("Primer Equipo 30 mar. 2025 Osasuna cita"), ["2025-03-30"])
        self.assertEqual(sayfa.gorunur_tarihler("Spielplan 23.11.2023 / Profis"), ["2023-11-23"])


def girdi(**k):
    d = dict(mac_id="t:1", mod="tarihsel", kesim_zamani="2024-03-10T16:30:00+00:00", baslama_utc="2024-03-10T16:30:00+00:00",
             kategori="sakatlik", takim="Kulüp A", takim_rolu="favori", iddia="Kaptan uyluk sakatlığı nedeniyle yok",
             url="https://www.kulup-a.example/news/1", yayin_zamani="2024-03-09T13:00:00+00:00", yayin_zamani_kaynagi="jsonld",
             zaman_durumu="mac_oncesi_dogrulandi", sayfa_sha256="a" * 64, etki={"etkilenen": ["1X2"], "yon": "favori aleyhine"})
    d.update(k)
    return HaberGirdisi(**d)


E = "2026-11-25T00:00:00+00:00"


class H5Kanit(Temel):
    def test_gecerli_kanit_resmi_ve_tek_kaynak(self):
        kk = kayit_ornegi()
        k = haber_kaniti(girdi(), kk, E)
        self.assertIsInstance(k, Kanit)
        self.assertEqual(k.dogrulama, "resmi")
        self.assertEqual(k.deger["etki"]["nicel"], "hesaplanamaz")
        k2 = haber_kaniti(girdi(takim="Rakip"), kk, E)          # kulübün sitesi başka takım hakkında → tek kaynak
        self.assertEqual(k2.dogrulama, "tek_kaynak")

    def test_reddedilen_durumlar(self):
        kk = kayit_ornegi()
        for zd in ("mac_sonrasi", "ayni_gun_saat_yok", "tarih_yok", "guncelleme_mac_sonrasi"):
            d = haber_kaniti(girdi(zaman_durumu=zd), kk, E)
            self.assertIsInstance(d, DurumKaydi)
            self.assertEqual(d.durum, zd)
        self.assertEqual(haber_kaniti(girdi(kaynak_turu_beyan="arama_ozeti"), kk, E).durum, "arama_ozeti_kanit_degil")
        self.assertEqual(haber_kaniti(girdi(url="https://www.engelli.example/a"), kk, E).durum, "erisim_engeli")
        self.assertEqual(haber_kaniti(girdi(url="https://www.tekisaret.example/a"), kk, E).durum, "erisim_engeli")
        with self.assertRaises(ValueError):
            haber_kaniti(girdi(etki={"olasilik_degisimi": -0.05}), kk, E)     # keyfî nicel etki yasak
        with self.assertRaises(ValueError):
            haber_kaniti(girdi(etki={"nicel": 0.1}), kk, E)

    def test_ayni_grup_tekrari_bagimsiz_teyit_degil(self):
        kk = kayit_ornegi()
        a = haber_kaniti(girdi(url="https://www.gazete1.example/a", takim="Kulüp A"), kk, E)
        b = haber_kaniti(girdi(url="https://www.gazete2.example/b", takim="Kulüp A"), kk, E)
        c = haber_kaniti(girdi(url="https://www.gazete3.example/c", takim="Kulüp A"), kk, E)
        self.assertFalse(bagimsiz_mi(a, b))
        self.assertEqual(teyit_et([a, b])["onerilen_seviye"], "tek_kaynak")
        self.assertTrue(bagimsiz_mi(a, c))
        self.assertEqual(teyit_et([a, b, c])["onerilen_seviye"], "cok_kaynak")

    def test_mk1_bahis_kaynagi(self):
        with self.assertRaises(KanitHatasi):
            Kanit("t:1", "haber", "x", 1, "nesine", "https://bulten.nesine.com/x", E, "tek_kaynak").dogrula()


class H6Modlar(Temel):
    def test_tarihsel_ve_guncel_ayri(self):
        t = AramaOturumu("tarihsel", "o1", kok=self.tmp)
        self.assertEqual(t.mac_ekle("t:1", "2024-03-10T16:30:00+00:00"), "2024-03-10T16:30:00+00:00")
        t.kanit_ekle(haber_kaniti(girdi(), kayit_ornegi(), E))
        t.durum_ekle(DurumKaydi("t:1", "taktik", "aranip_bulunamadi", "kaynakta yok"))
        self.assertIn("rotasyon", t.eksik_kategoriler("t:1"))
        self.assertNotIn("sakatlik", t.eksik_kategoriler("t:1"))
        oz = t.dondur()
        r = json.loads((self.tmp / "tarihsel" / "o1" / "oturum.json").read_text())
        self.assertIn("KÖR TEST DEĞİLDİR", r["etiket"])
        self.assertEqual(len(oz["kanitlar_sha256"]), 64)
        with self.assertRaises(ModHatasi):                      # güncel oturuma tarihsel kanıt girmez
            g = AramaOturumu("guncel", "o2", kok=self.tmp, tahmin_sha256="b" * 64, simdi="2024-03-10T10:00:00+00:00")
            g.mac_ekle("t:1", "2024-03-10T16:30:00+00:00")
            g.kanit_ekle(haber_kaniti(girdi(), kayit_ornegi(), E))
        self.assertTrue((self.tmp / "guncel" / "o2").exists() and (self.tmp / "tarihsel" / "o1").exists())

    def test_guncel_kurallari(self):
        with self.assertRaises(ModHatasi):                      # tahmin dondurulmadan güncel araştırma yok
            AramaOturumu("guncel", "o3", kok=self.tmp)
        g = AramaOturumu("guncel", "o4", kok=self.tmp, tahmin_sha256="c" * 64, simdi="2024-03-10T17:00:00+00:00")
        with self.assertRaises(ModHatasi):                      # başlamadan sonra güncel araştırma yok
            g.mac_ekle("t:1", "2024-03-10T16:30:00+00:00")
        g2 = AramaOturumu("guncel", "o5", kok=self.tmp, tahmin_sha256="c" * 64, simdi="2024-03-10T10:00:00+00:00")
        g2.mac_ekle("t:1", "2024-03-10T16:30:00+00:00")
        k = haber_kaniti(girdi(mod="guncel", kesim_zamani="2024-03-10T10:00:00+00:00",
                               yayin_zamani="2024-03-10T11:00:00+00:00"), kayit_ornegi(), E)
        with self.assertRaises(ModHatasi):                      # kesimden sonra yayımlanan kanıt reddedilir
            g2.kanit_ekle(k)


# Pilotta (output/arastirma/pilot_v1/kanitlar.jsonl) kullanılan iki kayıt — yeni kurallarla yeniden değerlendirme
PILOT_ORNEK = [
    {"mac_id": "pilot:de.1-B-K", "url": "https://www.bayer04.de/en-us/news/bundesliga/our-next-opponents-wolves-seeking-turnaround",
     "yayin": ("jsonld", "2024-03-09T13:00:00+00:00"), "baslama": "2024-03-10T16:30:00+00:00", "beklenen": "mac_oncesi_dogrulandi"},
    {"mac_id": "pilot:es.1-B-S", "url": "https://www.osasuna.es/news/read/36442/osasuna-cita-a-21-futbolistas-para-el-partido-de-san-mames",
     "yayin": None, "gorunur": ["2025-03-30"], "baslama": "2025-03-30T16:30:00+00:00", "beklenen": "ayni_gun_saat_yok"},
    {"mac_id": "pilot:es.1-A-S", "url": "https://www.fcbarcelona.com/en/news/4185659/preview-fc-barcelona-v-leganes",
     "yayin": ("jsonld", "2024-12-15"), "baslama": "2024-12-15T15:15:00+00:00", "beklenen": "ayni_gun_saat_yok"},
]


class H7PilotUyumu(Temel):
    def test_pilot_kayitlari_yeni_kurallarla(self):
        kk = KaynakKaydi.yukle()
        for p in PILOT_ORNEK:
            y, g = zaman.coz({"yayin": [p["yayin"]] if p["yayin"] else []}, p.get("gorunur", []))
            durum = zaman.mac_oncesi_durumu(y, p["baslama"], g)
            self.assertEqual(durum, p["beklenen"], p["mac_id"])
            sonuc = haber_kaniti(girdi(mac_id=p["mac_id"], url=p["url"], yayin_zamani=y.deger, zaman_durumu=durum,
                                       baslama_utc=p["baslama"], kesim_zamani=p["baslama"], takim="x"), kk, E)
            if durum == "mac_oncesi_dogrulandi":
                self.assertIsInstance(sonuc, Kanit)
            else:   # pilotta "saat doğrulanamadı" notuyla tutulan 2 kayıt yeni kurallarda doğrulanmış kanıt DEĞİL
                self.assertIsInstance(sonuc, DurumKaydi)

    @unittest.skipUnless((KOK / "output/arastirma/pilot_v1/kanitlar.jsonl").exists(), "pilot kanıt dosyası yok")
    def test_pilot_dosyasi_okunur_ve_hostlari_kayitta(self):
        kk = KaynakKaydi.yukle()
        satirlar = [json.loads(s) for s in (KOK / "output/arastirma/pilot_v1/kanitlar.jsonl").read_text().splitlines() if s]
        self.assertEqual(len(satirlar), 17)
        for s in satirlar:
            Kanit(**s).dogrula()
            host = s["kaynak_url"].split("/")[2]
            self.assertIsNotNone(kk.get(host), host)
            self.assertIn(kk.get(host).sinif, ("kullanilabilir",), host)


if __name__ == "__main__":
    unittest.main()
