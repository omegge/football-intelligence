"""İnternete açık çalıştırma (bulut kipi) için güvenlik: giriş, oturum, CSRF, istek sınırı, güvenlik başlıkları.

Yalnızca standart kütüphane. Bulut kipi FI_ORTAM=bulut ile açılır ve zorunlu ayarlar eksikse sunucu BAŞLAMAZ
(kapalı başarısızlık). Yerel kip (varsayılan) 127.0.0.1'de girişsiz çalışır.

Ortam değişkenleri (değerleri koda, depoya ya da loga yazılmaz):
  FI_ORTAM            "bulut" → giriş zorunlu, yalnızca FI_IZINLI_HOST, HTTPS yönlendirmesi, HSTS
  FI_KULLANICI        giriş adı
  FI_PAROLA_OZETI     `python3 -m uygulama parola-ozeti` çıktısı (pbkdf2_sha256$tur$tuz$ozet); düz parola saklanmaz
  FI_OTURUM_ANAHTARI  oturum çerezini imzalayan rastgele gizli değer (≥ 32 karakter)
  FI_IZINLI_HOST      virgülle ayrılmış genel ana makine adları; verilmezse Render'ın RENDER_EXTERNAL_HOSTNAME değeri
  FD_TOKEN            football-data.org anahtarı (yalnızca bulutta; X-Auth-Token başlığına uygulama ekler)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import defaultdict, deque

OTURUM_SURESI_SN = 14 * 24 * 3600
CEREZ = "fi_oturum"
PBKDF2_TUR = 310_000


class AyarHatasi(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------ ayarlar
def bulut_mu() -> bool:
    return os.environ.get("FI_ORTAM", "").strip().lower() == "bulut"


def ayarlar() -> dict:
    """Bulut kipinde zorunlu ayarları denetler; eksikse AyarHatasi (sunucu açılmaz)."""
    a = {"bulut": bulut_mu(), "kullanici": os.environ.get("FI_KULLANICI", ""),
         "parola_ozeti": os.environ.get("FI_PAROLA_OZETI", ""), "anahtar": os.environ.get("FI_OTURUM_ANAHTARI", ""),
         "hostlar": [h.strip().lower() for h in (os.environ.get("FI_IZINLI_HOST")
                                                  or os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")).split(",") if h.strip()]}
    if a["bulut"]:
        eksik = [ad for ad, kosul in (("FI_KULLANICI", bool(a["kullanici"])),
                                      ("FI_PAROLA_OZETI", a["parola_ozeti"].startswith("pbkdf2_sha256$")),
                                      ("FI_OTURUM_ANAHTARI", len(a["anahtar"]) >= 32),
                                      ("FI_IZINLI_HOST/RENDER_EXTERNAL_HOSTNAME", bool(a["hostlar"]))) if not kosul]
        if eksik:
            raise AyarHatasi("bulut kipinde eksik ya da geçersiz ayar: " + ", ".join(eksik))
    return a


# ------------------------------------------------------------------------------------------------ parola
def parola_ozeti(parola: str, tur: int = PBKDF2_TUR, tuz: bytes | None = None) -> str:
    if len(parola) < 12:
        raise ValueError("parola en az 12 karakter olmalı")
    tuz = tuz or secrets.token_bytes(16)
    oz = hashlib.pbkdf2_hmac("sha256", parola.encode("utf-8"), tuz, tur)
    return f"pbkdf2_sha256${tur}${base64.b64encode(tuz).decode()}${base64.b64encode(oz).decode()}"


def parola_dogru(parola: str, kayit: str) -> bool:
    try:
        ad, tur, tuz, oz = kayit.split("$")
        if ad != "pbkdf2_sha256":
            return False
        hesap = hashlib.pbkdf2_hmac("sha256", parola.encode("utf-8"), base64.b64decode(tuz), int(tur))
        return hmac.compare_digest(hesap, base64.b64decode(oz))
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------------------------------------ oturum ve CSRF
def _imza(anahtar: str, govde: str) -> str:
    return hmac.new(anahtar.encode(), govde.encode(), hashlib.sha256).hexdigest()


def oturum_olustur(anahtar: str, kullanici: str, simdi: float | None = None) -> str:
    bitis = int((simdi or time.time()) + OTURUM_SURESI_SN)
    govde = f"{base64.urlsafe_b64encode(kullanici.encode()).decode()}.{bitis}.{secrets.token_hex(8)}"
    return f"{govde}.{_imza(anahtar, govde)}"


def oturum_dogrula(anahtar: str, deger: str | None, simdi: float | None = None) -> str | None:
    """Geçerli oturumun kullanıcı adı; aksi halde None."""
    if not deger or deger.count(".") != 3:
        return None
    govde, imza = deger.rsplit(".", 1)
    if not hmac.compare_digest(_imza(anahtar, govde), imza):
        return None
    k, bitis, _ = govde.split(".")
    if int(bitis) < (simdi or time.time()):
        return None
    try:
        return base64.urlsafe_b64decode(k.encode()).decode()
    except ValueError:
        return None


def csrf_jetonu(anahtar: str, oturum: str) -> str:
    return _imza(anahtar, "csrf:" + oturum)[:40]


def csrf_dogru(anahtar: str, oturum: str | None, jeton: str | None) -> bool:
    return bool(oturum and jeton) and hmac.compare_digest(csrf_jetonu(anahtar, oturum), jeton)


def cerez_oku(baslik: str | None, ad: str = CEREZ) -> str | None:
    for parca in (baslik or "").split(";"):
        k, _, v = parca.strip().partition("=")
        if k == ad:
            return v
    return None


def cerez_yaz(deger: str, bulut: bool, sil: bool = False) -> str:
    ozellik = ["Path=/", "HttpOnly", "SameSite=Strict"] + (["Secure"] if bulut else [])
    ozellik.append("Max-Age=0" if sil else f"Max-Age={OTURUM_SURESI_SN}")
    return f"{CEREZ}={'' if sil else deger}; " + "; ".join(ozellik)


# ------------------------------------------------------------------------------------------------ istek sınırı
class Sinirlayici:
    """Kayan pencere: anahtar başına `pencere_sn` içinde en fazla `adet` olay."""

    def __init__(self, adet: int, pencere_sn: float, saat=time.monotonic):
        self.adet, self.pencere, self.saat = adet, pencere_sn, saat
        self.olaylar: dict[str, deque] = defaultdict(deque)
        self.kilit = threading.Lock()

    def _temizle(self, q: deque, simdi: float):
        while q and simdi - q[0] > self.pencere:
            q.popleft()

    def izin(self, anahtar: str) -> tuple[bool, int]:
        """(izin var mı, izin yoksa kaç saniye sonra)"""
        with self.kilit:
            simdi = self.saat()
            q = self.olaylar[anahtar]
            self._temizle(q, simdi)
            if len(q) >= self.adet:
                return False, int(self.pencere - (simdi - q[0])) + 1
            q.append(simdi)
            return True, 0

    def kalan(self, anahtar: str) -> int:
        with self.kilit:
            q = self.olaylar[anahtar]
            self._temizle(q, self.saat())
            return self.adet - len(q)


# Giriş denemeleri: IP başına 15 dakikada 5; genel olarak saatte 30 (dağıtık denemelere karşı)
GIRIS_IP = Sinirlayici(5, 15 * 60)
GIRIS_GENEL = Sinirlayici(30, 3600)
# Dış kaynağa giden işlemler (Nesine, football-data.org) ve hesaplama
ISLEM_SINIRLARI = {
    "bulten": Sinirlayici(1, 10 * 60),     # Nesine: 10 dakikada en fazla 1 çekim
    "guncel": Sinirlayici(1, 10 * 60),     # football-data.org: 10 dakikada 1 (9 istek; ücretsiz plan 10/dk)
    "dondur": Sinirlayici(20, 3600),
    "fiyat": Sinirlayici(20, 3600),
    "ice_aktar": Sinirlayici(3, 3600),
}


def istemci_ip(baslik_xff: str | None, uzak: str) -> str:
    """Render vekil sunucusu X-Forwarded-For ekler; ilk değer istemcidir. Yerelde soket adresi."""
    if baslik_xff and bulut_mu():
        return baslik_xff.split(",")[0].strip()
    return uzak


# ------------------------------------------------------------------------------------------------ başlıklar
def guvenlik_basliklari(bulut: bool) -> dict:
    b = {"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin",
         "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; "
                                    "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
         "Permissions-Policy": "camera=(), microphone=(), geolocation=()", "Cache-Control": "no-store"}
    if bulut:
        b["Strict-Transport-Security"] = "max-age=31536000"
    return b
