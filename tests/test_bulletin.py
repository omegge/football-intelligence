"""A1-A9: internetsiz testler. Ağ çağrısı test boyunca kilitli; bütün veriler elle kurulmuş örneklerdir.

Çalıştırma (proje kökünden):  python3 -m unittest discover -s tests -v
"""
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KOK = Path(__file__).resolve().parent.parent
MODUL = KOK / ".claude/skills/football-bulletin-fetch/scripts/nesine_bulletin.py"
spec = importlib.util.spec_from_file_location("nesine_bulletin", MODUL)
nb = importlib.util.module_from_spec(spec)
sys.modules["nesine_bulletin"] = nb
spec.loader.exec_module(nb)

TR = ZoneInfo("Europe/Istanbul")
CEKIM_TR = datetime(2026, 11, 24, 19, 0, tzinfo=TR)


def _ag_yasak(*a, **k):
    raise AssertionError("Test sırasında ağ çağrısı yapıldı!")


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def op(n, o, on=None):
    d = {"N": n, "O": o}
    if on is not None:
        d["ON"] = on
    return d


def mk(mtid=None, sov=0.0, oca=None, **ek):
    d = {"SOV": sov, "OCA": oca if oca is not None else [], **ek}
    if mtid is not None:
        d["MTID"] = mtid
    return d


def ev(C, HN="Ev", AN="Dep", typ=1, gt=None, bas=None, ma=None, **ek):
    d = {"C": C, "NID": C, "HN": HN, "AN": AN, "LN": "Test Ligi", **ek}
    if typ is not None:
        d["TYPE"] = typ
    if gt is not None:
        d["GT"] = gt
    if bas is not None:
        d["ESD"] = ms(bas)
        d["D"] = bas.strftime("%d.%m.%Y")
        d["T"] = bas.strftime("%H:%M")
    if ma is not None:
        d["MA"] = ma
    return d


def govde(etkinlikler, yapi="normal") -> bytes:
    veri = {"sg": {"EA": etkinlikler}} if yapi == "normal" else {"data": {"events": etkinlikler}}
    return json.dumps(veri, ensure_ascii=False).encode("utf-8")


def cekim(g: bytes, durum=200, tur="application/json", hata=None, akis="mac_oncesi"):
    return {"govde": g, "meta": {"url": nb.AKISLAR[akis]["url"], "cekim_utc": CEKIM_TR.astimezone(ZoneInfo("UTC")).isoformat(),
                                 "cekim_tr": CEKIM_TR.isoformat(), "user_agent": nb.USER_AGENT, "http_durumu": durum,
                                 "icerik_turu": tur, "bayt": len(g), "sha256": hashlib.sha256(g).hexdigest() if g else None,
                                 "hata": hata}}


def ms_market(c=0):
    return mk(1, 0.0, [op(1, 2.10 + c), op(2, 3.30), op(3, 3.60)])


class Temel(unittest.TestCase):
    def setUp(self):
        self._eski = urllib.request.urlopen
        urllib.request.urlopen = _ag_yasak
        self.tmp = Path(tempfile.mkdtemp(prefix="fi_test_"))
        self.sozluk = nb.Sozluk()

    def tearDown(self):
        urllib.request.urlopen = self._eski
        shutil.rmtree(self.tmp, ignore_errors=True)

    def isle(self, mac_oncesi=None, canli=None, pencere=None, ad="run"):
        c = {}
        if mac_oncesi is not None:
            c["mac_oncesi"] = mac_oncesi
        if canli is not None:
            c["canli"] = canli
        out = self.tmp / ad
        return nb.isle(c, out, pencere, self.sozluk), out

    def kodlar(self, ozet_klasor, akis):
        return {e["kod"] for e in json.loads((ozet_klasor / f"{akis}.json").read_text(encoding="utf-8"))["futbol"]}

    def kayit(self, ozet, kod):
        return [r for r in ozet["dogrulama"] if r["kod"] == kod]


class A1CanliSiniflandirma(Temel):
    def test_akisa_gore_siniflandirma(self):
        pre = [ev(100, bas=datetime(2026, 11, 24, 21, 0, tzinfo=TR), ma=[ms_market()]),
               ev(101, bas=datetime(2026, 11, 24, 18, 30, tzinfo=TR), ma=[ms_market()]),
               ev(300, typ=2, bas=datetime(2026, 11, 24, 21, 0, tzinfo=TR), ma=[ms_market()])]
        live = [ev(200, typ=None, gt=1, bas=datetime(2026, 11, 24, 18, 0, tzinfo=TR), ma=[ms_market()]),
                ev(101, typ=None, gt=1, bas=datetime(2026, 11, 24, 18, 30, tzinfo=TR), ma=[ms_market()]),
                ev(400, typ=None, gt=2, bas=datetime(2026, 11, 24, 18, 0, tzinfo=TR), ma=[ms_market()])]
        ozet, out = self.isle(cekim(govde(pre)), cekim(govde(live), akis="canli"))
        self.assertEqual(self.kodlar(out, "canli"), {200, 101})           # canlı = canlı akıştan gelen futbol
        self.assertEqual(self.kodlar(out, "mac_oncesi"), {100, 101})      # maç öncesi akıştan çıkarılmadı
        on = {e["kod"]: e for e in json.loads((out / "mac_oncesi.json").read_text())["futbol"]}
        cl = {e["kod"]: e for e in json.loads((out / "canli.json").read_text())["futbol"]}
        self.assertTrue(on[101]["diger_akista_da_var"] and cl[101]["diger_akista_da_var"])
        self.assertFalse(on[100]["diger_akista_da_var"])
        self.assertTrue(on[101]["baslama_saati_gecmis"])
        self.assertEqual(json.loads((out / "canli.json").read_text())["diger_spor_sayilari"], {"2": 1})
        self.assertTrue(self.kayit(ozet, "IKI_AKISTA"))

    def test_yoklukla_canli_cikarimi_yok(self):
        # Yalnızca maç öncesi çekildiyse hiçbir maç 'canlı' sayılmaz, canli.json oluşmaz
        pre = [ev(100, bas=datetime(2026, 11, 24, 21, 0, tzinfo=TR), ma=[ms_market()])]
        ozet, out = self.isle(cekim(govde(pre)))
        self.assertFalse((out / "canli.json").exists())
        self.assertNotIn("canli", ozet["akislar"])

    def test_delta_ucu_kullanilmiyor(self):
        self.assertEqual(set(nb.AKISLAR), {"mac_oncesi", "canli"})
        self.assertNotIn("delta", json.dumps(nb.AKISLAR))

    def test_baslamamis_canli_isaretlenir(self):
        live = [ev(200, typ=None, gt=1, bas=datetime(2026, 11, 24, 22, 0, tzinfo=TR), ma=[ms_market()])]
        ozet, out = self.isle(canli=cekim(govde(live), akis="canli"))
        self.assertTrue(self.kayit(ozet, "BASLAMAMIS_CANLI"))


class A2CanliMarketAdlari(Temel):
    def test_json_adlari_once_sozluk_sonra(self):
        live = [ev(200, "Galatasaray", "Fenerbahçe", typ=None, gt=1, bas=datetime(2026, 11, 24, 18, 0, tzinfo=TR),
                   SC="1-0", MIN=67, LS={"H": 1, "A": 0},
                   ma=[{"ID": 5, "NO": 10760, "MT": 3, "MN": "Maç Sonucu", "SOV": 0,
                        "OCA": [op(1, 2.1, "1"), op(2, 3.2, "X"), op(3, 3.9, "2")]},
                       ms_market(),
                       mk(1, 0.0, [op(1, 2.0), op(2, 3.0), op(3, 4.0)], MN="Toplam Gol")])]
        ozet, out = self.isle(canli=cekim(govde(live), akis="canli"))
        e = json.loads((out / "canli.json").read_text())["futbol"][0]
        m0, m1, m2 = e["marketler"]
        self.assertEqual((m0["market_adi"], m0["market_adi_kaynagi"]), ("Maç Sonucu", "json"))
        self.assertEqual([s["secenek_adi"] for s in m0["secenekler"]], ["1", "X", "2"])
        self.assertEqual((m1["market_adi"], m1["market_adi_kaynagi"]), ("Maç Sonucu", "sozluk"))
        self.assertEqual(m1["secenekler"][0]["secenek_adi"], "MS 1")
        self.assertEqual((m2["market_adi"], m2["market_adi_kaynagi"]), ("Toplam Gol", "json"))
        self.assertTrue(self.kayit(ozet, "SOZLUK_JSON_UYUMSUZ"))
        self.assertNotIn("market None", json.dumps(e, ensure_ascii=False))

    def test_canli_durum_alanlari_saklanir(self):
        live = [ev(200, typ=None, gt=1, bas=datetime(2026, 11, 24, 18, 0, tzinfo=TR), SC="1-0", MIN=67,
                   LS={"H": 1, "A": 0}, ma=[ms_market()])]
        ozet, out = self.isle(canli=cekim(govde(live), akis="canli"))
        c = json.loads((out / "canli.json").read_text())["futbol"][0]["canli"]
        self.assertFalse(c["harita_dogrulandi"])                       # doğrulanmadan resmî skor yazılmaz
        self.assertEqual(c["adaylar"]["skor_metin"], {"alan": "SC", "deger": "1-0"})
        self.assertEqual(c["adaylar"]["dakika"]["deger"], 67)
        self.assertEqual(c["alanlar"]["LS.H"], 1)
        from openpyxl import load_workbook
        wb = load_workbook(out / "canli.xlsx", read_only=True)
        basliklar = [x.value for x in next(wb["canli_durum"].iter_rows(max_row=1))]
        self.assertIn("alan.LS.H", basliklar)
        self.assertIn("son_dogrulama_tr", basliklar)
        wb.close()
        self.assertTrue(self.kayit(ozet, "CANLI_ALANLAR"))

    def test_dogrulanmis_harita_kullanilir(self):
        eski = dict(nb.CANLI_ALAN_HARITASI)
        try:
            nb.CANLI_ALAN_HARITASI.update({"skor_ev": "LS.H", "skor_dep": "LS.A", "dakika": "MIN"})
            c = nb.canli_durum(ev(1, LS={"H": 2, "A": 1}, MIN=80))
            self.assertEqual(c["resmi"], {"skor_ev": 2, "skor_dep": 1, "dakika": 80})
            self.assertTrue(c["harita_dogrulandi"])
        finally:
            nb.CANLI_ALAN_HARITASI.clear()
            nb.CANLI_ALAN_HARITASI.update(eski)


class A3MacaOzelEtiketler(Temel):
    def test_oyuncu_adlari_tasinmaz(self):
        bas = datetime(2026, 11, 24, 21, 0, tzinfo=TR)
        pre = [ev(999, "Ajax", "PSV", bas=bas, ma=[mk(702, 0.0, [op(4, 5.5), op(35, 7.0)]),
                                                   mk(805, 0.0, [op(1, 1.8), op(2, 2.2)])]),
               ev(3303421, "Ukrayna", "Gürcistan", bas=bas, ma=[mk(702, 0.0, [op(4, 5.5)])]),  # sözlüğün öğrenildiği maç kodu
               ev(1000, "Roma", "Lazio", bas=bas, ma=[mk(702, 0.0, [op(4, 6.0, "Paulo Dybala")])])]
        ozet, out = self.isle(cekim(govde(pre)))
        metin = (out / "mac_oncesi.json").read_text(encoding="utf-8")
        for oyuncu in ("Artem Dovbyk", "Vladyslav Vanat", "{ev}", "{dep}"):
            self.assertNotIn(oyuncu, metin)
        from openpyxl import load_workbook
        wb = load_workbook(out / "mac_oncesi.xlsx", read_only=True)
        excel = " ".join(str(c) for r in wb["tum_oranlar"].iter_rows(values_only=True) for c in r)
        wb.close()
        self.assertNotIn("Dovbyk", excel)
        es = {e["kod"]: e for e in json.loads(metin)["futbol"]}
        self.assertEqual(es[999]["marketler"][0]["secenekler"][0]["secenek_adi"], "seçenek 4 (maça özel, etiket yok)")
        self.assertEqual(es[999]["marketler"][0]["market_adi"], "Oyuncu İlk Golü Atar")     # market adı sözlükten korunur
        self.assertTrue(es[999]["marketler"][1]["maca_ozel"])                                # Takım Şut
        self.assertEqual(es[1000]["marketler"][0]["secenekler"][0]["secenek_adi"], "Paulo Dybala")

    def test_json_adindan_maca_ozel(self):
        e = nb.etkinlik_normallestir(ev(5, ma=[{"MN": "Oyuncu Gol Atar", "SOV": 0, "OCA": [op(1, 2.0)]}]),
                                     "canli", self.sozluk, CEKIM_TR)
        self.assertTrue(e["marketler"][0]["maca_ozel"])


class A4SporAyrimi(Temel):
    def test_futbol_disina_sozluk_uygulanmaz(self):
        e = nb.etkinlik_normallestir(ev(7, typ=2, ma=[ms_market()]), "mac_oncesi", self.sozluk, CEKIM_TR)
        self.assertFalse(e["futbol"])
        self.assertEqual((e["marketler"][0]["market_adi"], e["marketler"][0]["market_adi_kaynagi"]), ("market 1", "yok"))
        self.assertEqual(e["marketler"][0]["secenekler"][0]["secenek_adi"], "seçenek 1")

    def test_spor_kodu(self):
        self.assertEqual(nb.spor_kodu({"TYPE": 1}), 1)
        self.assertEqual(nb.spor_kodu({"GT": 1}), 1)
        self.assertIsNone(nb.spor_kodu({"TYPE": -1, "GT": -1}))

    def test_belirsiz_spor_korunur(self):
        pre = [ev(1, bas=datetime(2026, 11, 24, 21, 0, tzinfo=TR), ma=[ms_market()]),
               {"C": 2677952, "TYPE": -1, "GT": -1, "ENN": "MLS - Şampiyon Kim Olur?", "D": "18.12.2026", "T": "03:00",
                "ESD": 1797552000000, "MSA": [{"ID": 1, "NO": 10760, "MN": "Şampiyon Kim Olur?", "SOV": 0.0,
                                               "OCA": [op(1, 11, "Chicago Fire"), op(2, 1, "LA Galaxy")]}]}]
        pre.append({"C": 777, "HN": "Bilinmeyen", "AN": "Spor", "ESD": 1797552000000,     # TYPE/GT yok: gerçekten belirsiz
                    "MA": [{"MTID": 1, "SOV": 0, "OCA": [op(1, 2.0)]}]})
        ozet, out = self.isle(cekim(govde(pre)))
        d = json.loads((out / "mac_oncesi.json").read_text())
        # 0. aşama kararı: TYPE=-1 futbol uzun vadeli pazarı ayrı tutulur, diğer sporlarla karışmaz
        self.assertEqual(len(d["futbol_uzun_vadeli"]), 1)
        self.assertEqual(d["futbol_uzun_vadeli"][0]["marketler"][0]["secenekler"][1]["oran_durumu"], "kapali")
        self.assertEqual([e["kod"] for e in d["spor_belirsiz"]], [777])
        from openpyxl import load_workbook
        wb = load_workbook(out / "mac_oncesi.xlsx", read_only=True)
        self.assertIn("futbol_uzun_vadeli", wb.sheetnames)
        self.assertIn("spor_belirsiz", wb.sheetnames)
        wb.close()


class A5CizgiHandikap(Temel):
    def ad(self, mtid, sov):
        k, tam = self.sozluk.bul(mtid, sov)
        return nb.sozluk_market_adi(k, tam, sov) if k else None

    def test_adlar(self):
        self.assertEqual(self.ad(11, 2.5), "2,5 Gol Alt/Üst")
        self.assertEqual(self.ad(11, 3), "3 Gol Alt/Üst")
        self.assertEqual(self.ad(268, -1.0), "Handikaplı Maç Sonucu (0:1)")
        self.assertEqual(self.ad(268, 1.0), "Handikaplı Maç Sonucu (1:0)")
        self.assertEqual(self.ad(268, 1.5), "Handikaplı Maç Sonucu (1,5:0)")
        self.assertEqual(self.ad(798, -1.5), "Korner Handikap (0:1,5)")
        self.assertEqual(self.ad(1, 0), "Maç Sonucu")
        self.assertEqual(self.ad(1, None), "Maç Sonucu")
        self.assertIsNone(self.ad(99999, 2.5))

    def test_bilinmeyen_kod(self):
        e = nb.etkinlik_normallestir(ev(1, ma=[mk(99999, 2.5, [op(1, 1.9)])]), "mac_oncesi", self.sozluk, CEKIM_TR)
        self.assertEqual(e["marketler"][0]["market_adi"], "market 99999 (2.5)")

    def test_ev_dep_sablonu(self):
        k, _ = self.sozluk.bul(885, 0.0)
        self.assertTrue(k["maca_ozel"])                                   # kombo: sözlük etiketi kullanılmaz
        e = nb.etkinlik_normallestir(ev(1, "A", "B", ma=[mk(3, 0.0, [op(1, 1.2)])]), "mac_oncesi", self.sozluk, CEKIM_TR)
        self.assertEqual(e["marketler"][0]["secenekler"][0]["secenek_adi"], "ÇŞ 1-X")


class A6TarihFiltresi(Temel):
    def test_pencereler(self):
        b, s = nb.zaman_penceresi(datetime(2026, 11, 24, 2, 30, tzinfo=TR))
        self.assertEqual((b, s), (datetime(2026, 11, 23, tzinfo=TR), datetime(2026, 11, 24, 3, tzinfo=TR)))
        b, s = nb.zaman_penceresi(datetime(2026, 11, 24, 10, 0, tzinfo=TR))
        self.assertEqual((b, s), (datetime(2026, 11, 24, tzinfo=TR), datetime(2026, 11, 25, 3, tzinfo=TR)))
        self.assertEqual(nb.gun_penceresi(nb.tr_zaman("24.11.2026").date())[1], datetime(2026, 11, 25, 3, tzinfo=TR))
        self.assertEqual(nb.tr_zaman("2026-11-24 18:00"), datetime(2026, 11, 24, 18, tzinfo=TR))
        with self.assertRaises(ValueError):
            nb.tr_zaman("yarın")

    def test_esd_ve_dt(self):
        z, k, c = nb.mac_zamani({"D": "18.12.2026", "T": "03:00", "ESD": 1797552000000})   # not defterindeki gerçek örnek
        self.assertEqual((z, k, c), (datetime(2026, 12, 18, 3, 0, tzinfo=TR), "ESD", False))
        z, k, c = nb.mac_zamani({"D": "18.12.2026", "T": "05:00", "ESD": 1797552000000})
        self.assertTrue(c)
        z, k, _ = nb.mac_zamani({"D": "18.12.2026", "T": "21:45"})
        self.assertEqual((z.hour, z.minute, k), (21, 45, "D/T"))
        self.assertEqual(nb.mac_zamani({"ESD": 1797552000})[0], datetime(2026, 12, 18, 3, 0, tzinfo=TR))
        self.assertEqual(nb.mac_zamani({})[0], None)

    def test_filtre_ucu_ve_zamansiz(self):
        pre = [ev(1, bas=datetime(2026, 11, 24, 23, 59, tzinfo=TR), ma=[ms_market()]),
               ev(2, bas=datetime(2026, 11, 25, 3, 0, tzinfo=TR), ma=[ms_market()]),      # pencere sonu: dışarıda
               ev(3, bas=datetime(2026, 11, 25, 2, 59, tzinfo=TR), ma=[ms_market()]),
               {**ev(4, ma=[ms_market()])},                                              # zaman yok
               {**ev(5, bas=datetime(2026, 11, 24, 20, 0, tzinfo=TR), ma=[ms_market()]), "T": "23:00"}]   # çelişki
        live = [ev(9, typ=None, gt=1, bas=datetime(2026, 11, 20, 18, 0, tzinfo=TR), ma=[ms_market()])]
        ozet, out = self.isle(cekim(govde(pre)), cekim(govde(live), akis="canli"), pencere=nb.gun_penceresi(datetime(2026, 11, 24).date()))
        self.assertEqual(self.kodlar(out, "mac_oncesi"), {1, 3, 4, 5})
        self.assertEqual(self.kodlar(out, "canli"), {9})                           # canlı filtrelenmez
        d = json.loads((out / "mac_oncesi.json").read_text())
        self.assertEqual(d["filtre_disi_kodlar"], [2])
        self.assertTrue([e for e in d["futbol"] if e["kod"] == 4][0]["zaman_okunamadi"])
        self.assertTrue(self.kayit(ozet, "ZAMAN_CELISKISI"))
        self.assertTrue(self.kayit(ozet, "FILTRE_DISI"))


class A7Dogrulama(Temel):
    bas = datetime(2026, 11, 24, 21, 0, tzinfo=TR)

    def test_yapi_degisti_yedek(self):
        ozet, out = self.isle(cekim(govde([ev(1, bas=self.bas, ma=[ms_market()])], yapi="farkli")))
        self.assertTrue(self.kayit(ozet, "YAPI_DEGISTI"))
        self.assertEqual(self.kodlar(out, "mac_oncesi"), {1})

    def test_etkinlik_yok(self):
        ozet, _ = self.isle(cekim(b'{"foo": 1}'))
        self.assertEqual(self.kayit(ozet, "ETKINLIK_YOK")[0]["seviye"], "KRITIK")
        self.assertEqual(ozet["durum"], "BASARISIZ")

    def test_eksik_alanlar_gecersiz_oran_tekrar(self):
        pre = [ev(1, bas=self.bas),                                                 # MA yok
               ev(2, bas=self.bas, ma=[mk(1, 0.0, [op(1, "abc"), op(2, 3.1), op(3, None)])]),
               ev(2, bas=self.bas, ma=[ms_market()]),
               ev(3, bas=self.bas, ma=[mk(11, 2.5, [])])]
        ozet, out = self.isle(cekim(govde(pre)))
        kodlar = {r["kod"] for r in ozet["dogrulama"]}
        self.assertTrue({"EKSIK_ALAN", "GECERSIZ_ORAN", "TEKRAR_KOD", "SECENEKSIZ_MARKET"} <= kodlar)
        d = json.loads((out / "mac_oncesi.json").read_text())
        self.assertEqual(len([e for e in d["futbol"] if e["kod"] == 2]), 2)        # tekrarlar korunur
        s = [e for e in d["futbol"] if e["kod"] == 2][0]["marketler"][0]["secenekler"]
        self.assertEqual([(x["oran_durumu"], x["oran_ham"]) for x in s], [("gecersiz", "abc"), ("acik", 3.1), ("yok", None)])
        self.assertEqual(ozet["durum"], "UYARILI")

    def test_bos_html_engel_baglanti(self):
        for c, beklenen in ((cekim(b""), "BOS_YANIT"),
                            (cekim(b"<!DOCTYPE html><title>Just a moment</title>", tur="text/html"), "ERISIM_ENGELI"),
                            (cekim(b"forbidden", durum=403, hata="HTTP 403"), "ERISIM_ENGELI"),
                            (cekim(b"", durum=None, hata="Bağlantı hatası: Tunnel connection failed: 403"), "BAGLANTI"),
                            (cekim(b"{bozuk"), "JSON_HATASI")):
            ozet, _ = self.isle(c, ad=beklenen + str(id(c)))
            self.assertEqual(self.kayit(ozet, beklenen)[0]["seviye"], "KRITIK", beklenen)
            self.assertEqual(ozet["durum"], "BASARISIZ")

    def test_izinsiz_host_reddedilir(self):
        with self.assertRaises(ValueError):
            nb.cek("https://www.nesine.com/iddaa")

    def test_tek_akis_basarisiz_digeri_calisir(self):
        ozet, out = self.isle(cekim(govde([ev(1, bas=self.bas, ma=[ms_market()])])),
                              cekim(b"", durum=403, hata="HTTP 403", akis="canli"))
        self.assertTrue((out / "mac_oncesi.xlsx").exists())
        self.assertIn("hata", ozet["akislar"]["canli"])

    def test_onceki_cekimle_karsilastirma(self):
        ozet1, out1 = self.isle(cekim(govde([ev(i, bas=self.bas, ma=[ms_market()], EX=1) for i in range(10)])), ad="bulten_1")
        ozet2 = nb.isle({"mac_oncesi": cekim(govde([ev(i, bas=self.bas, ma=[ms_market()]) for i in range(2)]))},
                        self.tmp / "bulten_2", None, self.sozluk, onceki=out1)
        kodlar = {r["kod"] for r in ozet2["dogrulama"]}
        self.assertIn("ALAN_KAYBOLDU", kodlar)
        self.assertIn("SAYI_DEGISIMI", kodlar)


class A8Sozluk(Temel):
    def test_sozluk_birebir_korundu(self):
        notebook = json.loads((KOK / "kaynak/nesine_gunluk_3.ipynb").read_text(encoding="utf-8"))
        hucre = "".join(notebook["cells"][3]["source"])
        gomulu = re.search(r"HAZIR_SOZLUK = json.loads\(r'''(.*?)'''\)", hucre, re.S).group(1)
        self.assertEqual(nb.SOZLUK_DOSYASI.read_text(encoding="utf-8"), gomulu)
        self.assertEqual(self.sozluk.kod_sayisi, 104)
        self.assertEqual(self.sozluk.veri["1|0.0"]["ad"], "Maç Sonucu")
        self.assertEqual(self.sozluk.veri["268|-1.0"]["ad"], "Handikaplı Maç Sonucu (0:1)")

    def test_islem_sozlugu_degistirmez(self):
        once = nb.SOZLUK_DOSYASI.read_bytes()
        self.isle(cekim(govde([ev(1, bas=datetime(2026, 11, 24, 21, 0, tzinfo=TR), ma=[ms_market(), mk(702, 0.0, [op(4, 5.0, "X Y")])])])))
        self.assertEqual(nb.SOZLUK_DOSYASI.read_bytes(), once)


class A9Excel(Temel):
    def veri(self):
        bas = datetime(2026, 11, 24, 21, 0, tzinfo=TR)
        return [ev(1, "Beşiktaş", "Trabzonspor", bas=bas, ma=[
                    ms_market(),
                    {"MN": "Özel Bahis", "SOV": 0, "OCA": [op(1, 1.5, "Evet"), op(2, 2.5, "Hayır")]},
                    {"MN": "Özel Bahis", "SOV": 0, "OCA": [op(1, 1.7, "Evet"), op(2, 2.1, "Hayır")]},   # aynı ad: çakışma
                    mk(11, 2.5, [op(1, 1.0), op(2, 1.85)]),                                         # kapalı seçenek
                    mk(11, 3.5, [])]),                                                              # seçeneksiz market
                ev(2, "Göztepe", "Samsunspor", bas=bas, ma=[ms_market(0.4), mk(11, 2.5, [op(1, 1.9), op(2, 1.9)])])]

    def test_hicbir_secenek_kaybolmaz(self):
        from openpyxl import load_workbook
        ozet, out = self.isle(cekim(govde(self.veri())),
                              cekim(govde([ev(7, typ=None, gt=1, bas=datetime(2026, 11, 24, 18, 0, tzinfo=TR),
                                              ma=[ms_market()], SC="0-0")]), akis="canli"))
        beklenen = 3 + 2 + 2 + 2 + 1 + 3 + 2
        self.assertEqual(ozet["akislar"]["mac_oncesi"]["secenek_satiri"], beklenen)
        wb = load_workbook(out / "mac_oncesi.xlsx", read_only=True)
        self.assertEqual(set(wb.sheetnames), {"ozet", "tum_oranlar", "maclar_genis", "kaynak", "dogrulama"})
        self.assertEqual(wb["tum_oranlar"].max_row - 1, beklenen)
        satirlar = list(wb["maclar_genis"].iter_rows(values_only=True))
        baslik = satirlar[0]
        self.assertEqual(len(baslik), len(set(baslik)))                              # sütun adları benzersiz
        dolu = sum(1 for r in satirlar[1:] for v in r[6:] if v is not None)
        self.assertEqual(dolu, beklenen)                                             # her seçenek bir hücrede
        hucreler = [v for r in satirlar[1:] for v in r[6:]]
        self.assertIn("-", hucreler)
        self.assertIn("seçenek yok", hucreler)
        self.assertEqual(sum(1 for c in baslik if str(c).startswith("Özel Bahis | Evet")), 2)
        wb.close()
        wbc = load_workbook(out / "canli.xlsx", read_only=True)
        self.assertIn("canli_durum", wbc.sheetnames)
        self.assertNotIn("canli_durum", load_workbook(out / "mac_oncesi.xlsx", read_only=True).sheetnames)
        wbc.close()
        self.assertFalse([r for r in ozet["dogrulama"] if r["seviye"] == "KRITIK"])

    def test_ham_json_ve_kaynak_bilgisi(self):
        g = govde(self.veri())
        ozet, out = self.isle(cekim(g))
        self.assertEqual((out / "ham/mac_oncesi.json").read_bytes(), g)
        k = json.loads((out / "kaynak.json").read_text())["kaynaklar"]["mac_oncesi"]
        self.assertEqual(k["sha256"], hashlib.sha256(g).hexdigest())
        self.assertEqual(k["cekim_tr"], CEKIM_TR.isoformat())
        self.assertEqual(k["url"], nb.AKISLAR["mac_oncesi"]["url"])
        self.assertEqual(k["ham_dosya"], "ham/mac_oncesi.json")

    def test_satir_ve_sutun_siniri(self):
        from openpyxl import load_workbook
        eski = (nb.SATIR_SINIRI, nb.SUTUN_SINIRI)
        try:
            nb.SATIR_SINIRI, nb.SUTUN_SINIRI = 4, 5
            ozet, out = self.isle(cekim(govde(self.veri())))
            wb = load_workbook(out / "mac_oncesi.xlsx", read_only=True)
            parca = [s for s in wb.sheetnames if s.startswith("tum_oranlar")]
            self.assertGreater(len(parca), 1)
            self.assertEqual(sum(wb[s].max_row - 1 for s in parca), ozet["akislar"]["mac_oncesi"]["secenek_satiri"])
            self.assertNotIn("maclar_genis", wb.sheetnames)
            wb.close()
            self.assertTrue(self.kayit(ozet, "GENIS_TABLO_ATLANDI"))
            self.assertFalse([r for r in ozet["dogrulama"] if r["seviye"] == "KRITIK"])
        finally:
            nb.SATIR_SINIRI, nb.SUTUN_SINIRI = eski

    def test_uzun_hucre_kesilir_json_tam(self):
        import warnings
        uzun = "x" * 40000
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ozet, out = self.isle(cekim(govde([ev(1, bas=datetime(2026, 11, 24, 21, 0, tzinfo=TR),
                                                  ma=[{"MN": "Uzun", "SOV": 0, "OCA": [op(1, 2.0, uzun), op(2, 3.0, uzun + "y")]}])])))
        self.assertFalse([x for x in w if "truncated" in str(x.message)], "Excel bir değeri sessizce kesti")
        self.assertTrue(self.kayit(ozet, "KESILEN_HUCRE"))
        self.assertIn(uzun, (out / "mac_oncesi.json").read_text())
        from openpyxl import load_workbook
        wb = load_workbook(out / "mac_oncesi.xlsx", read_only=True)
        baslik = next(wb["maclar_genis"].iter_rows(max_row=1, values_only=True))
        wb.close()
        self.assertEqual(len(baslik), len(set(baslik)))                    # kısaltılmış iki başlık çakışmadı
        self.assertFalse([r for r in ozet["dogrulama"] if r["seviye"] == "KRITIK"])


class A10LigVeMarketsiz(Temel):
    def test_lig_adi_LA_listesinden(self):
        bas = datetime(2026, 11, 24, 21, 0, tzinfo=TR)
        e1 = ev(1, bas=bas, ma=[ms_market()], LC=46260)
        e1.pop("LN")
        e2 = ev(2, bas=bas, ma=[ms_market()], LC=99)
        e2.pop("LN")
        g = json.dumps({"sg": {"EA": [e1, e2], "LA": [{"LID": 46260, "N": "AFC Asya Şampiyonlar Ligi Batı",
                                                         "CC": "FUTBOL-GENEL", "SO": 1}]}}).encode()
        ozet, out = self.isle(cekim(g))
        es = {e["kod"]: e for e in json.loads((out / "mac_oncesi.json").read_text())["futbol"]}
        self.assertEqual((es[1]["lig"], es[1]["lig_ulke"], es[1]["lig_kaynagi"]),
                         ("AFC Asya Şampiyonlar Ligi Batı", "FUTBOL-GENEL", "LA"))
        self.assertIsNone(es[2]["lig"])
        self.assertEqual(self.kayit(ozet, "LIG_ADI_YOK")[0]["sayi"], 1)

    def test_marketsiz_maclar_kaybolmaz(self):
        bas = datetime(2026, 11, 24, 21, 0, tzinfo=TR)
        ewma = [{"C": 3414788, "TYPE": 1, "D": "24.11.2026", "ESD": ms(bas), "HN": "AD Ceuta", "AN": "Almeria",
                 "LC": "1_1951", "LN": "İspanya 2. Lig", "NID": 3318724},
                {"C": 5, "TYPE": 2, "HN": "X", "AN": "Y", "ESD": ms(bas)}]
        g = json.dumps({"sg": {"EA": [ev(1, bas=bas, ma=[ms_market()])], "EWMA": ewma}}).encode()
        ozet, out = self.isle(cekim(g))
        d = json.loads((out / "mac_oncesi.json").read_text())
        self.assertEqual([e["kod"] for e in d["marketsiz_futbol"]], [3414788])
        self.assertEqual(d["marketsiz_futbol"][0]["lig"], "İspanya 2. Lig")
        self.assertEqual(self.kayit(ozet, "MARKETSIZ_MAC")[0]["sayi"], 1)
        from openpyxl import load_workbook
        wb = load_workbook(out / "mac_oncesi.xlsx", read_only=True)
        self.assertEqual(wb["marketsiz_maclar"].max_row - 1, 1)
        wb.close()
        self.assertEqual(self.kodlar(out, "mac_oncesi"), {1})                       # analiz kümesine karışmaz


class A11VeriButunlugu(Temel):
    """0. aşama: EMBS, MS durumu, SOV2/SOV3, EWMA eşleştirme, futbol uzun vadeli, nsnBultenNames, ad çelişkileri."""
    bas = datetime(2026, 11, 24, 21, 0, tzinfo=TR)

    def excel(self, out, akis, sayfa):
        from openpyxl import load_workbook
        wb = load_workbook(out / f"{akis}.xlsx", read_only=True)
        it = wb[sayfa].iter_rows(values_only=True)
        bas = next(it)
        rows = [dict(zip(bas, r)) for r in it]
        wb.close()
        return rows

    def test_embs_mac_mbs(self):
        a = nb.etkinlik_normallestir(ev(1, ma=[ms_market()], EMBS=3), "mac_oncesi", self.sozluk, CEKIM_TR)
        b = nb.etkinlik_normallestir(ev(2, ma=[ms_market()], MBS=2), "mac_oncesi", self.sozluk, CEKIM_TR)
        c = nb.etkinlik_normallestir(ev(3, ma=[ms_market()]), "mac_oncesi", self.sozluk, CEKIM_TR)
        self.assertEqual((a["mac_mbs"], a["mac_mbs_kaynagi"]), (3, "EMBS"))
        self.assertEqual((b["mac_mbs"], b["mac_mbs_kaynagi"]), (2, "MBS"))
        self.assertEqual((c["mac_mbs"], c["mac_mbs_kaynagi"]), (None, None))
        ozet, out = self.isle(cekim(govde([ev(1, bas=self.bas, ma=[ms_market()], EMBS=3)])))
        self.assertEqual({r["mac_mbs"] for r in self.excel(out, "mac_oncesi", "tum_oranlar")}, {3})

    def test_ms_oynanabilirlik_ham_oran_korunur(self):
        pre = [ev(1, bas=self.bas, ma=[mk(1, 0.0, [op(1, 2.1), op(2, 1.0), op(3, 3.6)], MS=1),
                                       mk(11, 2.5, [op(1, 1.9), op(2, 1.85)], MS=0),
                                       mk(11, 3.5, [op(1, 1.5), op(2, 2.4)], MS=-2),
                                       mk(11, 1.5, [op(1, 3.1), op(2, 1.3)])])]                       # MS yok
        ozet, out = self.isle(cekim(govde(pre)))
        ms = {(m["market_tip_id"], m["ozel_deger"]): m for m in json.loads((out / "mac_oncesi.json").read_text())["futbol"][0]["marketler"]}
        self.assertEqual([s["oynanabilirlik"] for s in ms[(1, 0.0)]["secenekler"]], ["oynanabilir", "kapali", "oynanabilir"])
        for k, ms_beklenen in (((11, 2.5), 0), ((11, 3.5), -2), ((11, 1.5), None)):
            self.assertEqual(ms[k]["market_durumu"], ms_beklenen)
            self.assertEqual({s["oynanabilirlik"] for s in ms[k]["secenekler"]}, {"durumu_dogrulanmamis"})
            self.assertTrue(all(s["oran"] is not None and s["oran_ham"] is not None for s in ms[k]["secenekler"]))   # ham oran silinmedi
        uzun = self.excel(out, "mac_oncesi", "tum_oranlar")
        self.assertEqual(len(uzun), 9)
        self.assertEqual(sum(r["oynanabilirlik"] == "durumu_dogrulanmamis" for r in uzun), 6)
        genis = self.excel(out, "mac_oncesi", "maclar_genis")[0]
        self.assertEqual(genis["2,5 Gol Alt/Üst | Alt"], "? 1.9")                           # sayı gibi gösterilmez
        self.assertEqual(genis["Maç Sonucu | MS 1"], 2.1)
        oz = self.excel(out, "mac_oncesi", "ozet")[0]
        self.assertEqual((oz["oynanabilir_oran"], oz["durumu_dogrulanmamis_oran"]), (2, 6))
        self.assertEqual(self.kayit(ozet, "DURUMU_DOGRULANMAMIS_ORAN")[0]["sayi"], 6)
        self.assertEqual(self.kayit(ozet, "MARKET_DURUMU")[0]["sayi"], 4)

    def test_sov2_sov3_ve_market_anahtari(self):
        live = [ev(5, typ=None, gt=1, bas=datetime(2026, 11, 24, 18, 0, tzinfo=TR), ma=[
            {"ID": 1, "MTID": 561, "SOV": 0.0, "SOV2": 61.0, "SOV3": 70.0, "MS": 1, "MN": "61-70 dk. Korner", "OCA": [op(1, 2.0), op(2, 1.7)]},
            {"ID": 2, "MTID": 561, "SOV": 0.0, "SOV2": 71.0, "SOV3": 80.0, "MS": 1, "MN": "71-80 dk. Korner", "OCA": [op(1, 2.2), op(2, 1.6)]},
            {"ID": 3, "MTID": 56, "SOV": 0.0, "MS": 1, "MN": "Maçın Geri Kalanı 0:0", "OCA": [op(1, 3.0)]},
            {"ID": 4, "MTID": 56, "SOV": 0.0, "MS": 1, "MN": "Maçın Geri Kalanı 0:0", "OCA": [op(1, 3.5)]}])]   # yalnızca ID ayırıyor
        ozet, out = self.isle(canli=cekim(govde(live), akis="canli"))
        ms = json.loads((out / "canli.json").read_text())["futbol"][0]["marketler"]
        self.assertEqual([(m["ozel_deger2"], m["ozel_deger3"]) for m in ms[:2]], [(61.0, 70.0), (71.0, 80.0)])
        k = self.kayit(ozet, "MARKET_ANAHTARI")[0]
        self.assertEqual((k["sayi"], json.loads(k["ornek"])["sov2_sov3_ile_ayrisan"]), (2, 1))
        uzun = self.excel(out, "canli", "tum_oranlar")
        self.assertEqual(len(uzun), 6)
        self.assertEqual({r["ozel_deger2"] for r in uzun}, {61.0, 71.0, None})
        baslik = list(self.excel(out, "canli", "maclar_genis")[0].keys())
        self.assertEqual(len(baslik), len(set(baslik)))
        self.assertFalse([r for r in ozet["dogrulama"] if r["seviye"] == "KRITIK"])

    def test_takim_adi_karsilastir(self):
        k = nb.takim_adi_karsilastir
        self.assertEqual(k("AD Ceuta", "AD Ceuta"), "ayni")
        self.assertEqual(k("Chelmsford C.", "Chelmsford City"), "yazim_farki")
        self.assertEqual(k("Maidst. Utd", "Maidstone Utd"), "yazim_farki")
        self.assertEqual(k("C. Lecco", "Lecco"), "yazim_farki")
        self.assertEqual(k("CA Juventud De Las Piedras", "Juventud de Las Piedras"), "yazim_farki")
        self.assertEqual(k("Monterosi T.", "Guidonia"), "celiski")
        self.assertEqual(k(None, "X"), "bilinmiyor")

    def ewma_veri(self):
        b = self.bas
        ea = [ev(100, "Brentford", "Everton", bas=b, ma=[ms_market()]),
              ev(101, "Chelmsford C.", "Maidst. Utd", bas=b, ma=[ms_market()]),
              ev(102, "US Grosseto", "Monterosi T.", bas=b, ma=[ms_market()]),
              ev(103, "Nantes", "Grenoble", bas=b, ma=[ms_market()])]
        w = lambda c, nid, h, a, **k: {"C": c, "NID": nid, "TYPE": 1, "HN": h, "AN": a, "ESD": ms(b), "LN": "L", **k}
        ewma = [w(900, 100, "Brentford", "Everton"),                     # NID=C, aynı ad
                w(901, 101, "Chelmsford City", "Maidstone Utd"),         # NID=C, yazım farkı
                w(902, 102, "Grosseto", "Guidonia"),                     # NID=C, çelişki
                w(903, 555, "Nantes", "Grenoble"),                       # NID uymuyor, ad+saat
                w(904, 904, "Coleraine Gençler", "Larne Olympic Gençler"),  # gerçekten ayrı
                {"C": 905, "NID": 905, "TYPE": 137, "HN": "X", "AN": "Y", "ESD": ms(b)}]   # başka spor
        live = [ev(902, "Grosseto", "Guidonia", typ=None, gt=1, bas=b, ma=[ms_market()], NID=102)]
        live[0]["NID"] = 102
        return json.dumps({"sg": {"EA": ea, "EWMA": ewma}}).encode(), govde(live)

    def test_ewma_eslestirme_tekrar_yok(self):
        pre, live = self.ewma_veri()
        ozet, out = self.isle(cekim(pre), cekim(live, akis="canli"))
        d = json.loads((out / "mac_oncesi.json").read_text())
        es = {k["ewma_kod"]: k for k in d["ewma_eslesmeler"]}
        self.assertEqual({k: (v["durum"], v["yontem"], v["eslesen_kod"]) for k, v in es.items()}, {
            900: ("eslesti", "NID=C", 100), 901: ("eslesti", "NID=C", 101), 902: ("eslesti_belirsiz", "NID=C", 102),
            903: ("eslesti_belirsiz", "ad+saat", 103), 904: ("ayri_mac", None, None)})
        self.assertEqual(es[901]["ad_sonucu"], "yazim_farki")
        self.assertEqual(es[902]["ad_sonucu"], "celiski")
        self.assertTrue(es[902]["canli_akista"])
        self.assertEqual([e["kod"] for e in d["marketsiz_futbol"]], [904])            # yalnızca gerçekten ayrı olan
        f = {e["kod"]: e for e in d["futbol"]}
        self.assertEqual(f[100]["canli_kodu"], 900)
        self.assertTrue(f[102]["isim_celiskisi"] and f[102]["dogrulanmamis_eslesme"])
        self.assertTrue(f[103]["dogrulanmamis_eslesme"])
        self.assertFalse(f[101].get("dogrulanmamis_eslesme"))
        g = self.kayit(ozet, "GERCEK_MAC_SAYISI")[0]
        self.assertEqual(g["sayi"], 5)                                                # 4 oranlı + 1 ayrı; canlı ortak tek sayıldı
        self.assertEqual(json.loads(g["ornek"])["iki_akista_ortak"], 1)
        cel = self.kayit(ozet, "ISIM_CELISKISI")[0]
        self.assertEqual(cel["sayi"], 2)                                              # EWMA↔maç öncesi ve canlı↔maç öncesi
        self.assertTrue(self.kayit(ozet, "BELIRSIZ_ESLESME"))
        self.assertEqual(len(self.excel(out, "mac_oncesi", "ewma_eslesmeler")), 5)
        self.assertEqual(len(self.excel(out, "mac_oncesi", "marketsiz_maclar")), 1)
        cf = json.loads((out / "canli.json").read_text())["futbol"][0]
        self.assertTrue(cf["isim_celiskisi"] and cf["dogrulanmamis_eslesme"])

    def test_diger_uzun_vadeli_karismaz(self):
        pre = [ev(1, bas=self.bas, ma=[ms_market()]),
               {"C": 2, "TYPE": -1, "GT": -1, "ENN": "Süper Lig - Şampiyon Kim Olur?", "ESD": ms(self.bas),
                "MSA": [{"ID": 9, "MN": "Şampiyon Kim Olur?", "SOV": 0, "MS": 1, "OCA": [op(1, 2.5, "Galatasaray")]}]},
               {"C": 3, "TYPE": -2, "GT": -2, "ENN": "Euroleague - Şampiyon Kim Olur?", "ESD": ms(self.bas),
                "MSA": [{"ID": 8, "MN": "Şampiyon Kim Olur?", "SOV": 0, "OCA": [op(1, 4.0, "X")]}]}]
        ozet, out = self.isle(cekim(govde(pre)))
        d = json.loads((out / "mac_oncesi.json").read_text())
        self.assertEqual([e["kod"] for e in d["futbol_uzun_vadeli"]], [2])
        self.assertEqual(d["spor_belirsiz"], [])
        self.assertEqual(d["diger_uzun_vadeli_sayilari"], {"uzun_vadeli_2": 1})
        self.assertEqual(self.kodlar(out, "mac_oncesi"), {1})
        self.assertEqual(len(self.excel(out, "mac_oncesi", "futbol_uzun_vadeli")), 1)

    def test_nsn_adlari_etiket_uydurmaz(self):
        b = self.bas
        e1 = ev(10, "Galatasaray", "Fenerbahçe", bas=b, ma=[
            {"ID": 50, "MTID": 99999, "SOV": 0, "MS": 1, "OCA": [op(1, 2.0), op(2, 3.0, "Uzun Ad")]}])
        nsn = {"nsnBultenNames": [{"C": 3, "EID": 10, "MID": 50, "ON": 2, "N": "Kısa Ad", "NID": 10},
                                  {"C": 3, "EID": 10, "MID": 50, "ON": 1, "N": "Tahmin Edilemez", "NID": 10},
                                  {"C": 3, "EID": 10, "MID": 777, "ON": 1, "N": "Eşleşmez", "NID": 10},
                                  {"C": 1, "EID": 10, "HN": "G.Saray", "NID": 10},
                                  {"C": 4, "EID": 10, "AN": "F.Bahçe", "NID": 10}]}
        ozet, out = self.isle(cekim(json.dumps({"sg": {"EA": [e1]}, "nsn": nsn}).encode()))
        e = json.loads((out / "mac_oncesi.json").read_text())["futbol"][0]
        s1, s2 = e["marketler"][0]["secenekler"]
        self.assertEqual((s1["secenek_adi"], s1["secenek_adi_kaynagi"], s1["secenek_alternatif_adi"]),
                         ("seçenek 1", "yok", "Tahmin Edilemez"))                     # ana etiket DOLDURULMADI
        self.assertEqual((s2["secenek_adi"], s2["secenek_alternatif_adi"]), ("Uzun Ad", "Kısa Ad"))
        self.assertEqual(e["alternatif_adlar"], {"ev_kisa": "G.Saray", "dep_kisa": "F.Bahçe"})
        k = json.loads(self.kayit(ozet, "NSN_ADLAR")[0]["ornek"])
        self.assertEqual((k["uygulanan_secenek"], k["isimsiz_secenege_katki"], k["eslesmeyen_secenek_kaydi"]), (2, 1, 1))

    def test_excel_json_ham_tutarliligi(self):
        """Her ham seçenek (maç, blok, sıra, N) JSON'da ve Excel'de tam bir kez, aynı oran ve MS ile."""
        pre, live = self.ewma_veri()
        ozet, out = self.isle(cekim(pre), cekim(live, akis="canli"))
        for akis, g in (("mac_oncesi", pre), ("canli", live)):
            raw = json.loads(g)["sg"]["EA"]
            ham = {(e["C"], b, i, s["N"]): (s["O"], m.get("MS")) for e in raw if e.get("TYPE") == 1 or e.get("GT") == 1
                   for b in ("MA", "MSA") for i, m in enumerate(e.get(b) or []) for s in m.get("OCA") or []}
            ex = {(r["kod"], r["market_blok"], r["market_sira"], r["secenek_no"]): (r["oran_ham"], r["market_durumu"])
                  for r in self.excel(out, akis, "tum_oranlar")}
            self.assertEqual(ham, ex, akis)


if __name__ == "__main__":
    unittest.main(verbosity=2)
