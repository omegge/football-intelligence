"""Bulut kipi güvenliği: giriş, oturum, CSRF, Host/HTTPS denetimi, istek sınırı, yedek içe aktarma güvenliği."""
import gzip
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "lib"))
sys.path.insert(0, str(KOK))
from fi import is_akisi as I  # noqa: E402
from uygulama import guvenlik as G  # noqa: E402

PAROLA = "dogru-parola-uzun-123"
HOST = "fi-test.example"


class Birim(unittest.TestCase):
    def test_g1_parola(self):
        oz = G.parola_ozeti(PAROLA, tur=1000)
        self.assertTrue(G.parola_dogru(PAROLA, oz))
        self.assertFalse(G.parola_dogru(PAROLA + "x", oz))
        self.assertFalse(G.parola_dogru(PAROLA, "bozuk"))
        self.assertNotIn(PAROLA, oz)
        with self.assertRaises(ValueError):
            G.parola_ozeti("kisa")

    def test_g2_oturum_imza_ve_sure(self):
        a = "k" * 40
        o = G.oturum_olustur(a, "omer", simdi=1000)
        self.assertEqual(G.oturum_dogrula(a, o, simdi=1001), "omer")
        self.assertIsNone(G.oturum_dogrula("baska" * 10, o, simdi=1001))           # başka anahtar
        self.assertIsNone(G.oturum_dogrula(a, o[:-1] + ("0" if o[-1] != "0" else "1"), simdi=1001))
        self.assertIsNone(G.oturum_dogrula(a, o, simdi=1000 + G.OTURUM_SURESI_SN + 1))
        self.assertIsNone(G.oturum_dogrula(a, None))
        self.assertIsNone(G.oturum_dogrula(a, "a.b"))

    def test_g3_csrf(self):
        a = "k" * 40
        o = G.oturum_olustur(a, "omer")
        self.assertTrue(G.csrf_dogru(a, o, G.csrf_jetonu(a, o)))
        self.assertFalse(G.csrf_dogru(a, o, "yanlis"))
        self.assertFalse(G.csrf_dogru(a, None, G.csrf_jetonu(a, o)))

    def test_g4_sinirlayici(self):
        saat = [0.0]
        s = G.Sinirlayici(2, 60, saat=lambda: saat[0])
        self.assertEqual([s.izin("x")[0], s.izin("x")[0], s.izin("x")[0]], [True, True, False])
        saat[0] = 61
        self.assertTrue(s.izin("x")[0])
        self.assertEqual(G.ISLEM_SINIRLARI["bulten"].adet, 1)

    def test_g5_bulut_kipi_kapali_basarisizlik(self):
        with mock.patch.dict(os.environ, {"FI_ORTAM": "bulut"}, clear=False):
            for k in ("FI_KULLANICI", "FI_PAROLA_OZETI", "FI_OTURUM_ANAHTARI", "FI_IZINLI_HOST"):
                os.environ.pop(k, None)
            with self.assertRaises(G.AyarHatasi):
                G.ayarlar()
        from uygulama import sunucu as S
        with mock.patch.dict(os.environ, {"FI_ORTAM": ""}):
            with self.assertRaises(G.AyarHatasi):               # girişsiz kip internete açılamaz
                S.calistir(0, "0.0.0.0")

    def test_g6_bulutta_teknik_ayrinti_gizli(self):
        from uygulama import sunucu as S
        with mock.patch.dict(os.environ, {"FI_ORTAM": "bulut"}):
            try:
                raise RuntimeError("/gizli/yol")
            except RuntimeError as e:
                h = S.hata_sayfasi(e, "/")
        self.assertNotIn("Traceback", h)
        self.assertNotIn("/gizli/yol", h)

    def test_g7_guvenli_sonraki(self):
        from uygulama import sunucu as S
        for kotu in ("//kotu.example", "https://kotu.example", "\\\\kotu", "javascript:alert(1)"):
            self.assertEqual(S._guvenli_sonraki(kotu), "/")
        self.assertEqual(S._guvenli_sonraki("/mac/1"), "/mac/1")

    def test_g8_fd_anahtari_yalnizca_basliga(self):
        from uygulama import islemler as IS
        from fi.kaynaklar import footballdataorg as F
        with mock.patch.dict(os.environ, {"FD_TOKEN": "gizli-deger"}):
            ist = IS.fd_istemcisi()
        istek = urllib.request.Request("https://api.football-data.org/v4/x")
        with mock.patch.object(F, "_varsayilan_acici", return_value="ok") as ac:     # ağ isteği yapılmaz
            self.assertEqual(ist.acici(istek, 5), "ok")
        self.assertEqual(istek.get_header("X-auth-token"), "gizli-deger")
        ac.assert_called_once()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FD_TOKEN", None)
            self.assertIs(IS.fd_istemcisi().acici, F._varsayilan_acici)             # anahtarsız: başlık eklenmez


def _tar(dosyalar: dict, manifest: dict | None = None) -> bytes:
    tampon = io.BytesIO()
    with tarfile.open(fileobj=tampon, mode="w:gz") as t:
        satir = []
        for ad, veri in dosyalar.items():
            satir.append(f"{hashlib.sha256(veri).hexdigest()}  {ad}")
            b = tarfile.TarInfo(ad)
            b.size = len(veri)
            t.addfile(b, io.BytesIO(veri))
        man = (manifest if manifest is not None else "\n".join(satir) + "\n")
        man = man.encode() if isinstance(man, str) else man
        b = tarfile.TarInfo("output/yedek/MANIFEST_x.sha256")
        b.size = len(man)
        t.addfile(b, io.BytesIO(man))
    return tampon.getvalue()


class YedekGuvenligi(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        from uygulama import yedek as Y
        self.Y = Y

    def test_y1_gidis_donus_ve_ustune_yazmama(self):
        (self.kok / "raporlar").mkdir()
        (self.kok / "raporlar" / "a.md").write_text("bir")
        veri, _ = self.Y.yedek_olustur(self.kok)
        hedef = Path(tempfile.mkdtemp())
        r = self.Y.ice_aktar(veri, hedef)
        self.assertEqual(r["yazilan"], 1)
        self.assertEqual((hedef / "raporlar" / "a.md").read_text(), "bir")
        (hedef / "raporlar" / "a.md").write_text("degisti")
        r = self.Y.ice_aktar(veri, hedef)
        self.assertEqual(r["cakisma"], ["output/raporlar/a.md"])
        self.assertEqual((hedef / "raporlar" / "a.md").read_text(), "degisti")

    def test_y2_yol_saldirisi_reddedilir(self):
        r = self.Y.ice_aktar(_tar({"output/../../etc/x": b"k", "output/gizli/x": b"k", "output/raporlar/ok.md": b"ok"}), self.kok)
        self.assertEqual(r["yazilan"], 1)
        self.assertEqual(len(r["reddedilen"]), 2)
        self.assertFalse((self.kok.parent / "etc" / "x").exists())

    def test_y3_bozuk_sha_hicbir_sey_yazmaz(self):
        man = f"{'0' * 64}  output/raporlar/a.md\n{hashlib.sha256(b'b').hexdigest()}  output/raporlar/b.md\n"
        with self.assertRaises(self.Y.YedekHatasi):
            self.Y.ice_aktar(_tar({"output/raporlar/b.md": b"b", "output/raporlar/a.md": b"a"}, man), self.kok)
        self.assertFalse((self.kok / "raporlar").exists())

    def test_y4_donmus_tahmin_ve_kayit_birlesimi(self):
        mac = {"mac_id": "nesine:5", "baslama_tr": "2026-12-01T21:00:00+03:00"}
        r = I.dondur(mac, {"durum": "hesaplandi", "olasiliklar": {"MS_X": 0.3}}, kok=self.kok / "tahminler",
                     simdi=datetime.fromisoformat("2026-11-30T10:00:00+00:00"))
        veri, _ = self.Y.yedek_olustur(self.kok)
        hedef = Path(tempfile.mkdtemp())
        r1 = self.Y.ice_aktar(veri, hedef)
        r2 = self.Y.ice_aktar(veri, hedef)
        self.assertEqual((r1["kayit_satiri_eklenen"], r2["kayit_satiri_eklenen"]), (1, 0))
        self.assertEqual(r1["donmus_bozuk"], [])
        self.assertEqual(I.donmus_oku(hedef / "tahminler" / Path(r["yol"]).name)["sha256"], r["sha256"])


def _bos_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class _Yonlendirmesiz(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class BulutKipi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kok = Path(tempfile.mkdtemp())
        I.dondur({"mac_id": "nesine:1", "karsilasma": "A - B", "baslama_tr": "2026-12-01T21:00:00+03:00"},
                 {"durum": "hesaplandi", "olasiliklar": {"MS_X": 0.3}}, kok=cls.kok / "tahminler",
                 simdi=datetime.fromisoformat("2026-11-30T10:00:00+00:00"))
        cls.port = _bos_port()
        env = {**os.environ, "FI_OUTPUT": str(cls.kok), "PYTHONPATH": str(KOK / "lib") + os.pathsep + str(KOK),
               "FI_ORTAM": "bulut", "FI_KULLANICI": "omer", "FI_PAROLA_OZETI": G.parola_ozeti(PAROLA, tur=2000),
               "FI_OTURUM_ANAHTARI": "t" * 48, "FI_IZINLI_HOST": HOST}
        cls.surec = subprocess.Popen([sys.executable, "-m", "uygulama", "--host", "127.0.0.1", "--port", str(cls.port)],
                                     cwd=KOK, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cls.acici = urllib.request.build_opener(_Yonlendirmesiz)
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{cls.port}/saglik", timeout=1)
                break
            except Exception:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.surec.terminate()
        cls.surec.wait(5)
        cls.cikti = cls.surec.stdout.read().decode()
        cls.surec.stdout.close()

    def iste(self, yol, veri=None, basliklar=None, host=HOST, proto="https"):
        h = {"Host": host, "X-Forwarded-Proto": proto, "X-Forwarded-For": "203.0.113.9", **(basliklar or {})}
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{yol}", data=veri, headers=h,
                                     method="POST" if veri is not None else "GET")
        try:
            r = self.acici.open(req, timeout=15)
            return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def giris(self, ip="203.0.113.50"):
        k, h, _ = self.iste("/giris", f"kullanici=omer&parola={PAROLA}&sonraki=/arsiv".encode(),
                            {"Origin": f"https://{HOST}", "X-Forwarded-For": ip})
        self.assertEqual(k, 303)
        self.assertEqual(h["Location"], "/arsiv")
        c = h["Set-Cookie"]
        for b in ("HttpOnly", "Secure", "SameSite=Strict"):
            self.assertIn(b, c)
        return c.split(";")[0]

    def test_b1_saglik_ve_giris_zorunlu(self):
        self.assertEqual(self.iste("/saglik")[0], 200)
        for yol in ("/", "/mac/1", "/arsiv", "/yonetim", "/yonetim/yedek.tar.gz", "/arastirma/surpriz"):
            k, h, _ = self.iste(yol)
            self.assertEqual(k, 303, yol)
            self.assertTrue(h["Location"].startswith("/giris"), yol)
        k, _, g = self.iste("/islem/dondur/1", b"")
        self.assertEqual(k, 401)

    def test_b2_host_ve_https(self):
        self.assertEqual(self.iste("/", host="kotu.example")[0], 421)
        k, h, _ = self.iste("/arsiv", proto="http")
        self.assertEqual((k, h["Location"]), (301, f"https://{HOST}/arsiv"))

    def test_b3_oturum_csrf_koken(self):
        c = self.giris()
        k, h, g = self.iste("/arsiv", basliklar={"Cookie": c})
        self.assertEqual(k, 200)
        self.assertIn("max-age", h["Strict-Transport-Security"])
        self.assertIn("frame-ancestors 'none'", h["Content-Security-Policy"])
        k, _, g = self.iste("/mac/1", basliklar={"Cookie": c})
        jeton = re.search(r"name='csrf' value='([0-9a-f]+)'", g.decode()).group(1)
        self.assertEqual(self.iste("/islem/dondur/1", b"", {"Cookie": c})[0], 403)                   # jeton yok
        self.assertEqual(self.iste("/islem/dondur/1", b"csrf=yanlis", {"Cookie": c})[0], 403)
        k, _, g = self.iste("/islem/dondur/1", f"csrf={jeton}".encode(), {"Cookie": c})
        self.assertEqual(k, 409)                                                                      # jeton doğru → iş kuralı
        self.assertIn("İşlem yapılmadı", g.decode())
        self.assertEqual(self.iste("/islem/dondur/1", f"csrf={jeton}".encode(),
                                   {"Cookie": c, "Origin": "https://kotu.example"})[0], 403)        # yabancı köken
        self.assertEqual(self.iste("/islem/dondur/1", f"csrf={jeton}".encode(),
                                   {"Cookie": c, "Origin": "null"})[0], 403)                        # gizlenmiş köken
        bozuk = c[:-2] + ("aa" if not c.endswith("aa") else "bb")
        self.assertEqual(self.iste("/arsiv", basliklar={"Cookie": bozuk})[0], 303)                  # değiştirilmiş çerez

    def test_b4_giris_sinir_ve_acik_yonlendirme(self):
        ip = "198.51.100.7"
        kodlar = [self.iste("/giris", b"kullanici=omer&parola=yanlis-parola-xx", {"X-Forwarded-For": ip})[0]
                  for _ in range(6)]
        self.assertEqual(kodlar, [401] * 5 + [429])
        k, h, _ = self.iste("/giris", f"kullanici=omer&parola={PAROLA}&sonraki=//kotu.example".encode(),
                            {"X-Forwarded-For": "198.51.100.8"})
        self.assertEqual((k, h["Location"]), (303, "/"))

    def test_b5_yedek_indir_yukle(self):
        c = self.giris("203.0.113.60")
        k, h, veri = self.iste("/yonetim/yedek.tar.gz", basliklar={"Cookie": c})
        self.assertEqual((k, h["Content-Type"]), (200, "application/gzip"))
        self.assertTrue(gzip.decompress(veri))
        _, _, g = self.iste("/yonetim", basliklar={"Cookie": c})
        jeton = re.search(r"data-csrf='([0-9a-f]+)'", g.decode()).group(1)
        self.assertEqual(self.iste("/yonetim/ice-aktar", veri, {"Cookie": c})[0], 403)
        k, _, g = self.iste("/yonetim/ice-aktar", veri, {"Cookie": c, "X-CSRF": jeton})
        self.assertEqual(k, 200)
        r = json.loads(g)
        self.assertEqual((r["yazilan"], r["cakisma"], r["donmus_bozuk"]), (0, [], []))
        k, _, g = self.iste("/yonetim/ice-aktar", b"tar degil", {"Cookie": c, "X-CSRF": jeton})
        self.assertEqual(k, 409)

    def test_b6_gunlukte_gizli_bilgi_yok(self):
        self.giris("203.0.113.70")
        self.iste("/giris", b"kullanici=omer&parola=yanlis-parola-yy", {"X-Forwarded-For": "203.0.113.71"})
        # günlük süreç kapanınca okunur; burada yalnızca sunucunun ayakta olduğunu doğrula
        self.assertIsNone(self.surec.poll())

    @classmethod
    def _gunluk_denetimi(cls):
        return cls.cikti


class GunlukDenetimi(unittest.TestCase):
    def test_b9_gunluk(self):
        cikti = getattr(BulutKipi, "cikti", "")
        if not cikti:
            self.skipTest("bulut kipi testleri çalışmadı")
        for gizli in (PAROLA, "yanlis-parola", "t" * 48, "203.0.113", "fi_oturum="):
            self.assertNotIn(gizli, cikti)


if __name__ == "__main__":
    unittest.main()
