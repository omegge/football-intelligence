"""C1-C6: football-data.org ücretsiz plan istemcisi (ağsız). Gerçek ağ çağrısı test boyunca kilitlidir."""
import io
import json
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "lib"))

from fi import girdi, kanit                       # noqa: E402
from fi.kaynaklar import footballdataorg as fd    # noqa: E402


def _ag_yasak(*a, **k):
    raise AssertionError("Test sırasında gerçek ağ çağrısı yapıldı!")


def basliklar(d: dict) -> Message:
    m = Message()
    for k, v in d.items():
        m[k] = str(v)
    return m


class Yanit(io.BytesIO):
    def __init__(self, govde, durum=200, bas=None):
        super().__init__(govde if isinstance(govde, bytes) else json.dumps(govde).encode())
        self.status = durum
        self.headers = basliklar(bas or {"X-Requests-Available-Minute": 9, "X-Requestcounter-Reset": 60,
                                         "X-Api-Version": "v4", "X-Authenticated-Client": "GIZLI_HESAP"})

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_hata(kod, bas=None):
    return urllib.error.HTTPError("https://api.football-data.org/v4/x", kod, "hata", basliklar(bas or {}), io.BytesIO(b"{}"))


class Acici:
    def __init__(self, *cevaplar):
        self.cevaplar, self.istekler = list(cevaplar), []

    def __call__(self, istek, zaman_asimi):
        self.istekler.append(istek)
        c = self.cevaplar.pop(0)
        if isinstance(c, Exception):
            raise c
        return c


class Saat:
    def __init__(self):
        self.t, self.uykular = 1000.0, []

    def saat(self):
        return self.t

    def uyku(self, s):
        self.uykular.append(round(s, 2))
        self.t += s


def ornek_mac(i=1, durum="FINISHED", sure="REGULAR", ft=(2, 1), ht=(1, 0), hakem=True, **ek):
    sc = {"winner": "HOME_TEAM", "duration": sure, "fullTime": {"home": ft[0], "away": ft[1]},
          "halfTime": {"home": ht[0], "away": ht[1]}}
    sc.update(ek.pop("skor_ek", {}))
    return {"id": 500000 + i, "utcDate": "2026-11-21T15:00:00Z", "status": durum, "matchday": 11, "stage": "REGULAR_SEASON",
            "group": None, "lastUpdated": "2026-11-23T00:20:26Z", "season": {"startDate": "2026-08-21"},
            "homeTeam": {"id": 61, "name": "Chelsea FC", "shortName": "Chelsea", "tla": "CHE"},
            "awayTeam": {"id": 341, "name": "Leeds United FC", "shortName": "Leeds", "tla": "LEE"},
            "score": sc, "odds": {"msg": "Activate Odds-Package in User-Panel to retrieve odds."},
            "referees": [{"id": 1, "name": "Thomas Bramall", "type": "REFEREE"}] if hakem else [], **ek}


def ornek_yanit(*maclar):
    return {"competition": {"code": "PL", "name": "Premier League"}, "filters": {"season": "2026"},
            "matches": list(maclar) or [ornek_mac()]}


class Temel(unittest.TestCase):
    def setUp(self):
        self._eski = urllib.request.urlopen
        urllib.request.urlopen = _ag_yasak
        self.tmp = Path(tempfile.mkdtemp(prefix="fi_fdorg_"))
        self.zaman = {"simdi": datetime(2026, 11, 24, 10, tzinfo=timezone.utc)}

    def tearDown(self):
        urllib.request.urlopen = self._eski
        shutil.rmtree(self.tmp, ignore_errors=True)

    def istemci(self, acici):
        s = Saat()
        self._n = getattr(self, "_n", 0) + 1                         # her istemciye ayrı önbellek
        self.onbellek = self.tmp / f"onbellek{self._n}"
        return fd.FdorgIstemcisi(self.onbellek, acici=acici, saat=s.saat, uyku=s.uyku,
                                 simdi=lambda: self.zaman["simdi"]), s

    def url(self):
        return fd.adres("maclar", "PL", dateFrom="2026-11-14", dateTo="2026-11-23", status="FINISHED")


class C1KapsamVeAdres(Temel):
    def test_yalnizca_ucretsiz_yarisma_ve_izinli_uc_nokta(self):
        self.assertEqual(len(fd.UCRETSIZ_YARISMALAR), 12)
        self.assertEqual(self.url(), "https://api.football-data.org/v4/competitions/PL/matches"
                                     "?dateFrom=2026-11-14&dateTo=2026-11-23&status=FINISHED")
        for hatali in (lambda: fd.adres("maclar", "SB"),               # Serie B: ücretli
                       lambda: fd.adres("maclar", "TSL"),
                       lambda: fd.adres("oranlar", "PL"),              # izinsiz uç nokta
                       lambda: fd.adres("maclar", "PL", odds="1"),     # izinsiz parametre
                       lambda: fd.adres("maclar", "PL", dateFrom="23.11.2026"),
                       lambda: fd.adres("maclar", "PL", status="LIVE")):
            with self.assertRaises(fd.FdorgHatasi):
                hatali()

    def test_izinsiz_adrese_istek_atilmaz(self):
        a = Acici()
        ist, _ = self.istemci(a)
        for u in ("http://api.football-data.org/v4/competitions/PL/matches", "https://evil.example/v4/x",
                  "https://api.football-data.org/v2/competitions"):
            with self.assertRaises(fd.FdorgHatasi):
                ist.getir(u)
        self.assertEqual(a.istekler, [])


class C2Guvenlik(Temel):
    def test_kimlik_basligi_kurulmaz_hesap_adi_saklanmaz(self):
        a = Acici(Yanit(ornek_yanit()))
        ist, _ = self.istemci(a)
        veri, meta = ist.getir(self.url())
        gonderilen = {k.lower() for k in a.istekler[0].header_items() for k in [k[0]]}
        self.assertFalse(gonderilen & fd.KIMLIK_BASLIKLARI)          # anahtarı proxy ekler, kod değil
        self.assertIn("FootballIntelligence", a.istekler[0].get_header("User-agent"))
        self.assertNotIn("GIZLI_HESAP", json.dumps(meta))
        onbellek_metni = "".join(p.read_text(encoding="utf-8") for p in self.onbellek.glob("*.meta.json"))
        self.assertTrue(onbellek_metni)
        self.assertNotIn("GIZLI_HESAP", onbellek_metni)
        self.assertNotIn("authenticated", onbellek_metni.lower())

    def test_kaynak_kodda_anahtar_yok(self):
        kaynak = (KOK / "lib/fi/kaynaklar/footballdataorg.py").read_text(encoding="utf-8")
        self.assertNotIn("os.environ.get(\"FOOTBALL", kaynak)
        self.assertNotRegex(kaynak, r"X-Auth-Token[\"']\s*:")       # başlık sözlüğünde anahtar alanı yok


class C3HizSiniri(Temel):
    def test_asgari_aralik_ve_kalan_hak(self):
        a = Acici(Yanit(ornek_yanit(), bas={"X-Requests-Available-Minute": 0, "X-Requestcounter-Reset": 30}),
                  Yanit(ornek_yanit()))
        ist, s = self.istemci(a)
        ist.getir(self.url())
        ist.getir(fd.adres("maclar", "PL", dateFrom="2026-11-01", dateTo="2026-11-07"))
        self.assertEqual(s.uykular, [31.0])                            # hak 0 -> sıfırlanmaya kadar (+1 sn)
        self.assertEqual(ist._kalan, 9)

    def test_429_bekler_ve_sinirli_dener(self):
        a = Acici(http_hata(429, {"Retry-After": 12}), Yanit(ornek_yanit()))
        ist, s = self.istemci(a)
        veri, meta = ist.getir(self.url())
        self.assertEqual((len(a.istekler), meta["http_durumu"]), (2, 200))
        self.assertIn(12.0, s.uykular)
        a = Acici(http_hata(429, {"X-Requestcounter-Reset": 20}), http_hata(429), http_hata(429), Yanit(ornek_yanit()))
        ist, s = self.istemci(a)
        with self.assertRaises(fd.FdorgHatasi) as c:
            ist.getir(self.url())
        self.assertTrue(c.exception.dur)
        self.assertEqual(len(a.istekler), 3)                           # 1 + 2 yeniden deneme

    def test_401_403_durur(self):
        for kod in (401, 403):
            a = Acici(http_hata(kod), Yanit(ornek_yanit()))
            ist, _ = self.istemci(a)
            with self.assertRaises(fd.FdorgHatasi) as c:
                ist.getir(self.url())
            self.assertTrue(c.exception.dur)
            self.assertEqual(len(a.istekler), 1)

    def test_gecici_hata_bir_kez_ve_html(self):
        a = Acici(http_hata(503), Yanit(ornek_yanit()))
        ist, _ = self.istemci(a)
        self.assertEqual(ist.getir(self.url())[1]["http_durumu"], 200)
        a = Acici(Yanit(b"<!DOCTYPE html><title>x</title>"))
        ist, _ = self.istemci(a)
        with self.assertRaises(fd.FdorgHatasi):
            ist.getir(self.url())


class C4Onbellek(Temel):
    def test_onbellek_ve_sure(self):
        a = Acici(Yanit(ornek_yanit()), Yanit(ornek_yanit()))
        ist, _ = self.istemci(a)
        ist.getir(self.url(), onbellek_sn=900)
        veri, meta = ist.getir(self.url(), onbellek_sn=900)
        self.assertTrue(meta["onbellekten"])
        self.assertEqual(len(a.istekler), 1)
        self.zaman["simdi"] += timedelta(minutes=16)
        self.assertFalse(ist.getir(self.url(), onbellek_sn=900)[1]["onbellekten"])
        self.assertEqual(len(a.istekler), 2)


class C5Ayristirma(Temel):
    def test_alanlar_ve_oran_atilir(self):
        r = fd.maclari_ayristir(ornek_yanit(ornek_mac(1), ornek_mac(2, hakem=False, ht=(None, None)),
                                            ornek_mac(3, durum="TIMED", ft=(None, None), ht=(None, None))))
        m = r[0]
        self.assertEqual((m["yarisma"], m["ev"], m["ms_ev"], m["ms_dep"], m["iy_ev"], m["hakem"], m["kazanan"]),
                         ("PL", "Chelsea FC", 2, 1, 1, "Thomas Bramall", "HOME_TEAM"))
        self.assertEqual(m["utc_baslama"], "2026-11-21T15:00:00+00:00")
        self.assertEqual(m["tr_baslama"], "2026-11-21T18:00:00+03:00")
        self.assertEqual(m["son_guncelleme"], "2026-11-23T00:20:26Z")
        self.assertEqual((m["normal_sure_ev"], m["normal_sure_dep"]), (2, 1))
        self.assertIsNone(r[1]["hakem"])
        self.assertIsNone(r[1]["iy_ev"])
        self.assertEqual(r[2]["durum"], "TIMED")
        metin = json.dumps(r)
        self.assertNotIn("odds", metin.lower())
        self.assertNotIn("Odds-Package", metin)
        girdi.oransiz_mi(r)

    def test_uzatma_normal_sure_ayrilir(self):
        m = fd.mac_ayristir(ornek_mac(9, sure="EXTRA_TIME", ft=(3, 2),
                                      skor_ek={"regularTime": {"home": 2, "away": 2}, "extraTime": {"home": 1, "away": 0}}), "CL")
        self.assertEqual((m["ms_ev"], m["normal_sure_ev"], m["normal_sure_dep"], m["sure_turu"]), (3, 2, 2, "EXTRA_TIME"))


class C6Kanit(Temel):
    def test_sonuc_kanitlari_kayitli(self):
        a = Acici(Yanit(ornek_yanit(ornek_mac(1), ornek_mac(3, durum="SCHEDULED", ft=(None, None), ht=(None, None)))))
        ist, _ = self.istemci(a)
        maclar, meta = fd.yarisma_maclari(ist, "PL", "2026-11-14", "2026-11-23", status=None, onbellek_sn=900)
        ks = fd.sonuc_kanitlari(maclar, meta)
        self.assertEqual(len(ks), 1)                                    # yalnızca bitmiş maç
        depo = kanit.KanitDeposu(self.tmp / "kanit.jsonl")
        depo.ekle(ks[0])
        k = depo.oku()[0]
        self.assertEqual((k.mac_id, k.konu, k.dogrulama, k.kaynak_adi), ("fdorg:500001", "sonuc", "veri_kaynagi", "football-data.org"))
        self.assertEqual((k.yayin_tarihi, k.olcum_baslangic), ("2026-11-23T00:20:26Z", "2026-11-21"))
        self.assertTrue(k.kaynak_url.startswith("https://api.football-data.org/v4/competitions/PL/matches"))
        self.assertEqual(k.notlar, fd.ATIF)
        self.assertEqual(k.ham_sha256, meta["sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
