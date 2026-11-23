"""Araştırma veri kaynakları için HTTP erişimi.

- Yalnızca KAYNAKLAR listesindeki hostlara istek atılır (Nesine burada yoktur; bülten ayrı modüldedir).
- Dürüst User-Agent; tarayıcı taklidi, çerez, token yoktur.
- Disk önbelleği (URL başına; süre kaynağa göre) ve host başına asgari bekleme süresi.
- 401/403/407/429/451 ya da beklenmeyen HTML yanıtı = erişim engeli: yeniden denenmez, aşılmaya çalışılmaz.
- Geçici hatalarda (5xx, zaman aşımı) en fazla bir yeniden deneme.
- Her yanıtla kaynak bilgisi döner: URL, HTTP durumu, içerik türü, bayt, SHA-256, erişim zamanı (UTC/TR), önbellekten mi.
"""

from __future__ import annotations

import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import USER_AGENT

TR = ZoneInfo("Europe/Istanbul")
ONBELLEK = Path(__file__).resolve().parents[2] / "output" / "onbellek"
ENGEL = {401, 403, 407, 429, 451}

# Erişim koşulları ilk gerçek bağlantıda kontrol edilip docs/VERI_KAYNAKLARI.md'ye yazılır.
KAYNAKLAR = {
    "clubelo": {"hostlar": {"api.clubelo.com", "clubelo.com", "www.clubelo.com"}, "min_aralik_sn": 2.0,
                "onbellek_sn": 12 * 3600, "tur": "csv", "kosullar": "http://clubelo.com/API"},
    "footballdata": {"hostlar": {"www.football-data.co.uk", "football-data.co.uk"}, "min_aralik_sn": 2.0,
                     "onbellek_sn": 24 * 3600, "tur": "csv", "kosullar": "https://www.football-data.co.uk/data.php"},
}


class ErisimHatasi(RuntimeError):
    def __init__(self, mesaj: str, meta: dict | None = None, engel: bool = False):
        super().__init__(mesaj)
        self.meta = meta or {}
        self.engel = engel


@dataclass
class Yanit:
    govde: bytes
    meta: dict

    def metin(self) -> str:
        for kod in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return self.govde.decode(kod)
            except UnicodeDecodeError:
                continue
        return self.govde.decode("utf-8", "replace")


def _varsayilan_acici(istek, zaman_asimi):
    baglam = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)
    return urllib.request.urlopen(istek, timeout=zaman_asimi, context=baglam)


class VeriIstemcisi:
    def __init__(self, onbellek: Path = ONBELLEK, acici=_varsayilan_acici, saat=time.monotonic, uyku=time.sleep,
                 simdi=lambda: datetime.now(timezone.utc), zaman_asimi: float = 30.0):
        self.onbellek = Path(onbellek)
        self.acici, self.saat, self.uyku, self.simdi = acici, saat, uyku, simdi
        self.zaman_asimi = zaman_asimi
        self._son_istek: dict[str, float] = {}
        self.istek_sayisi = 0

    def _kaynak(self, kaynak: str, url: str) -> dict:
        if kaynak not in KAYNAKLAR:
            raise ErisimHatasi(f"tanımsız kaynak: {kaynak}")
        u = urllib.parse.urlparse(url)
        if u.scheme not in ("http", "https") or u.hostname not in KAYNAKLAR[kaynak]["hostlar"]:
            raise ErisimHatasi(f"{kaynak} için izinsiz adres: {url}")
        return KAYNAKLAR[kaynak]

    def _onbellek_yolu(self, url: str) -> Path:
        return self.onbellek / hashlib.sha256(url.encode()).hexdigest()[:32]

    def _onbellekten(self, url: str, sure: float):
        p = self._onbellek_yolu(url)
        if not (p.with_suffix(".bin").exists() and p.with_suffix(".json").exists()):
            return None
        meta = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
        yas = (self.simdi() - datetime.fromisoformat(meta["erisim_utc"])).total_seconds()
        if yas > sure:
            return None
        govde = p.with_suffix(".bin").read_bytes()
        if hashlib.sha256(govde).hexdigest() != meta["sha256"]:
            return None
        return Yanit(govde, {**meta, "onbellekten": True, "onbellek_yasi_sn": int(yas)})

    def _bekle(self, host: str, aralik: float):
        son = self._son_istek.get(host)
        if son is not None:
            kalan = aralik - (self.saat() - son)
            if kalan > 0:
                self.uyku(kalan)
        self._son_istek[host] = self.saat()

    def getir(self, kaynak: str, url: str, onbellek_kullan: bool = True) -> Yanit:
        k = self._kaynak(kaynak, url)
        if onbellek_kullan:
            y = self._onbellekten(url, k["onbellek_sn"])
            if y:
                return y
        host = urllib.parse.urlparse(url).hostname
        son_hata = None
        for deneme in (1, 2):
            self._bekle(host, k["min_aralik_sn"])
            t0 = self.saat()
            simdi = self.simdi()
            meta = {"kaynak": kaynak, "url": url, "erisim_utc": simdi.isoformat(timespec="seconds"),
                    "erisim_tr": simdi.astimezone(TR).isoformat(timespec="seconds"), "user_agent": USER_AGENT,
                    "http_durumu": None, "icerik_turu": None, "bayt": 0, "sha256": None, "onbellekten": False,
                    "deneme": deneme}
            istek = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv, application/json, */*"})
            self.istek_sayisi += 1
            try:
                with self.acici(istek, self.zaman_asimi) as r:
                    govde = r.read()
                    meta["http_durumu"] = getattr(r, "status", 200)
                    meta["icerik_turu"] = r.headers.get("Content-Type") if getattr(r, "headers", None) else None
            except urllib.error.HTTPError as h:
                meta["http_durumu"] = h.code
                if h.code in ENGEL:
                    raise ErisimHatasi(f"{kaynak}: HTTP {h.code} — erişim engeli; aşılmaya çalışılmadı", meta, engel=True)
                son_hata = ErisimHatasi(f"{kaynak}: HTTP {h.code}", meta)
                if h.code >= 500 and deneme == 1:
                    self.uyku(3.0)
                    continue
                raise son_hata
            except (urllib.error.URLError, TimeoutError, OSError) as h:
                neden = str(getattr(h, "reason", h))
                engel = "403" in neden and "unnel" in neden
                meta["hata"] = neden
                son_hata = ErisimHatasi(f"{kaynak}: bağlantı hatası: {neden}"
                                        + (" (bu ortamın ağ politikası hostu engelliyor)" if engel else ""), meta, engel)
                if engel or deneme == 2:
                    raise son_hata
                self.uyku(3.0)
                continue
            meta["sure_sn"] = round(self.saat() - t0, 2)
            meta["bayt"] = len(govde)
            meta["sha256"] = hashlib.sha256(govde).hexdigest()
            bas = govde[:300].lstrip().lower()
            if k["tur"] != "html" and (bas.startswith((b"<!doctype", b"<html")) or "html" in str(meta["icerik_turu"]).lower()):
                raise ErisimHatasi(f"{kaynak}: {k['tur']} yerine HTML geldi (engel/doğrulama sayfası olabilir); "
                                   "aşılmaya çalışılmadı", meta, engel=True)
            if not govde:
                raise ErisimHatasi(f"{kaynak}: boş yanıt", meta)
            p = self._onbellek_yolu(url)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.with_suffix(".bin").write_bytes(govde)
            p.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            return Yanit(govde, meta)
        raise son_hata or ErisimHatasi(f"{kaynak}: bilinmeyen hata")
