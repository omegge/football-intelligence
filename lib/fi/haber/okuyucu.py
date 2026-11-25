"""Güvenli sayfa okuyucu.

- Yalnızca kaynak kaydında 'kullanilabilir' sınıfındaki hostlara istek atılır; diğerlerinde ağ çağrısı YAPILMADAN
  HostEngelli yükseltilir. Yönlendirme başka bir hosta giderse sonuç reddedilir.
- Dürüst User-Agent; çerez, oturum, JavaScript, tarayıcı taklidi yok.
- Host başına asgari bekleme; 429/503'te Retry-After'a uyularak EN FAZLA bir yeniden deneme; 401/403/406/451'de dur.
- Zaman aşımı ve bağlantı hataları istisna değil, sonuç kaydı olarak döner.
- Sayfa HTML'i saklanmaz: yalnızca SHA-256, başlık, zaman adayları, kenarı kesilmiş gövde metni (bellekte) döner.
"""

from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .. import USER_AGENT
from . import sayfa
from .kaynak import KaynakKaydi

DUR = {401, 403, 406, 451}
TEKRAR = {429, 503}


class HostEngelli(PermissionError):
    pass


@dataclass
class SayfaSonucu:
    url: str
    host: str
    erisim_utc: str
    http: int | None = None
    hata: str | None = None
    sayfa_sha256: str | None = None
    baslik: str | None = None
    zaman_adaylari: dict = field(default_factory=dict)
    gorunur_tarihler: list = field(default_factory=list)
    metin: str = ""
    kenar_kesildi: bool = False
    yalnizca_js: bool = False

    @property
    def basarili(self) -> bool:
        return self.hata is None and self.http == 200


def _varsayilan_acici(istek, zaman_asimi):
    return urllib.request.urlopen(istek, timeout=zaman_asimi)


class GuvenliOkuyucu:
    def __init__(self, kayit: KaynakKaydi, acici=_varsayilan_acici, saat=time.monotonic, uyku=time.sleep,
                 min_aralik_sn: float = 2.0, zaman_asimi: float = 25.0, azami_bayt: int = 3_000_000,
                 azami_bekleme_sn: float = 120.0):
        self.kayit, self.acici, self.saat, self.uyku = kayit, acici, saat, uyku
        self.min_aralik_sn, self.zaman_asimi, self.azami_bayt = min_aralik_sn, zaman_asimi, azami_bayt
        self.azami_bekleme_sn = azami_bekleme_sn
        self._son: dict[str, float] = {}
        self.istek_gunlugu: list[dict] = []

    def _bekle(self, host):
        if host in self._son:
            kalan = self.min_aralik_sn - (self.saat() - self._son[host])
            if kalan > 0:
                self.uyku(kalan)

    def oku(self, url: str) -> SayfaSonucu:
        host = (urllib.parse.urlparse(url).hostname or "").casefold()
        if urllib.parse.urlparse(url).scheme != "https":
            raise HostEngelli(f"yalnızca https: {url}")
        if not self.kayit.okunabilir_mi(host):
            k = self.kayit.get(host)
            raise HostEngelli(f"{host}: okunamaz (sınıf: {k.sinif if k else 'kayıtsız'}"
                              f"{'; ' + k.gerekce if k else ''})")
        sonuc = SayfaSonucu(url=url, host=host, erisim_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        for deneme in (1, 2):
            self._bekle(host)
            istek = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            self.istek_gunlugu.append({"url": url, "deneme": deneme})
            try:
                with self.acici(istek, self.zaman_asimi) as r:
                    son_url = r.geturl() if hasattr(r, "geturl") else url
                    son_host = (urllib.parse.urlparse(son_url).hostname or "").casefold()
                    if son_host != host and not self.kayit.okunabilir_mi(son_host):
                        sonuc.hata = f"yönlendirme izinsiz hosta: {son_host}"
                        return sonuc
                    govde = r.read(self.azami_bayt + 1)
                    sonuc.http = getattr(r, "status", 200)
                self._son[host] = self.saat()
                break
            except urllib.error.HTTPError as e:
                self._son[host] = self.saat()
                sonuc.http = e.code
                if e.code in TEKRAR and deneme == 1:
                    bekle = e.headers.get("Retry-After") if e.headers else None
                    try:
                        sn = float(bekle) if bekle else 30.0
                    except ValueError:
                        sn = 30.0
                    if sn > self.azami_bekleme_sn:
                        sonuc.hata = f"HTTP {e.code}; Retry-After {sn:.0f} sn sınırı aşıyor — durduruldu"
                        return sonuc
                    self.uyku(sn)
                    continue
                sonuc.hata = f"HTTP {e.code}" + (" — erişim engeli, aşılmaz" if e.code in DUR else "")
                return sonuc
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                self._son[host] = self.saat()
                sonuc.hata = f"bağlantı/zaman aşımı: {type(e).__name__}"
                return sonuc
        else:
            return sonuc
        if len(govde) > self.azami_bayt:
            sonuc.hata = "sayfa boyut sınırını aşıyor"
            return sonuc
        s = govde.decode("utf-8", "replace")
        metin, kesildi = sayfa.govde_metni(s)
        sonuc.sayfa_sha256 = hashlib.sha256(govde).hexdigest()
        sonuc.baslik = sayfa.baslik(s)
        sonuc.zaman_adaylari = sayfa.zaman_adaylari(s)
        sonuc.metin, sonuc.kenar_kesildi = metin, kesildi
        sonuc.gorunur_tarihler = sayfa.gorunur_tarihler(metin)
        sonuc.yalnizca_js = sayfa.yalnizca_js_mi(s, metin)
        return sonuc
