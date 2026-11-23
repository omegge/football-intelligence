"""Takım adı eşleme: Nesine adlarını diğer kaynakların (ClubElo, football-data.co.uk …) adlarıyla eşler.

Kural: yalnızca iki durumda otomatik kabul vardır.
  'onayli' : kullanıcının daha önce onayladığı eşleme (veri/takim_eslemeleri.json)
  'kesin'  : normalleştirilmiş adlar BİREBİR aynı ve aday listesinde bu ada denk tek bir takım var
Diğer her şey 'belirsiz' ya da 'yok' döner ve kullanıcı onayı (onay_ekle) olmadan kullanılmaz.
Benzerlik skoru yalnızca aday önermek içindir; hiçbir zaman tek başına kabul sebebi değildir.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

ESLEME_DOSYASI = Path(__file__).resolve().parents[2] / "veri" / "takim_eslemeleri.json"

_TR = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
                     "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"})
# Ad içinde anlam taşımayan kulüp ekleri (her iki tarafta da atılır)
GENEL_EKLER = {"fc", "ac", "as", "us", "ca", "cf", "sc", "cd", "ud", "sd", "afc", "fk", "sk", "jk", "bk", "if",
               "club", "the", "calcio", "spor", "kulubu", "a.s", "sad"}
# Yalnızca yaygın ve belirsiz olmayan kısaltmalar
KISALTMALAR = {"utd": "united", "u": "united", "st": "saint", "mgladbach": "monchengladbach"}
# Ayırt edici ekler: biri varsa ve diğerinde yoksa asla 'kesin' sayılmaz
AYIRT_EDICI = {"u17", "u18", "u19", "u20", "u21", "u23", "ii", "b", "reserves", "res", "kadin", "kadinlar", "women",
               "w", "genc", "gencler", "youth", "olimpik"}


def normallestir(ad) -> str:
    s = str(ad or "").translate(_TR)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()
    s = s.replace("&", " and ")
    tokenler = [t for t in re.split(r"[^a-z0-9]+", s) if t]
    tokenler = [KISALTMALAR.get(t, t) for t in tokenler if t not in GENEL_EKLER]
    return " ".join(tokenler)


def ayirt_ediciler(ad) -> set:
    return set(normallestir(ad).split()) & AYIRT_EDICI


def benzerlik(a, b) -> float:
    """0..1. Sözcük örtüşmesi (önek eşleşmeleri dahil) ve karakter benzerliğinin ortalaması. Yalnızca öneri içindir."""
    na, nb = normallestir(a), normallestir(b)
    if not na or not nb:
        return 0.0
    ta, tb = set(na.split()), set(nb.split())
    eslesen = sum(1 for x in ta if any(y == x or (len(min(x, y, key=len)) >= 3 and (y.startswith(x) or x.startswith(y)))
                                       for y in tb))
    ortusme = eslesen / max(len(ta), len(tb))
    return round((ortusme + SequenceMatcher(None, na, nb).ratio()) / 2, 3)


@dataclass
class Eslesme:
    nesine_adi: str
    kaynak: str
    durum: str                       # 'onayli' | 'kesin' | 'belirsiz' | 'yok'
    kaynak_adi: str | None = None
    skor: float | None = None
    gerekce: str = ""
    alternatifler: list = field(default_factory=list)

    @property
    def kullanilabilir(self) -> bool:
        return self.durum in ("onayli", "kesin")


class TakimEslestirici:
    def __init__(self, dosya: Path = ESLEME_DOSYASI):
        self.dosya = Path(dosya)
        self.kayitlar: list[dict] = json.loads(self.dosya.read_text(encoding="utf-8")) if self.dosya.exists() else []

    def _onayli(self, nesine_adi: str, kaynak: str, ulke: str | None):
        for k in self.kayitlar:
            if k["kaynak"] == kaynak and normallestir(k["nesine_adi"]) == normallestir(nesine_adi) \
                    and (ulke is None or k.get("ulke") in (None, ulke)):
                return k
        return None

    def eslestir(self, nesine_adi: str, kaynak: str, adaylar: list[str], ulke: str | None = None,
                 oneri_esigi: float = 0.6) -> Eslesme:
        """adaylar: kaynağın aynı ülke/lig için verdiği takım adları (mümkünse önceden süzülmüş)."""
        o = self._onayli(nesine_adi, kaynak, ulke)
        if o:
            if o["kaynak_adi"] in adaylar or not adaylar:
                return Eslesme(nesine_adi, kaynak, "onayli", o["kaynak_adi"], 1.0, "kullanıcı onaylı eşleme")
            return Eslesme(nesine_adi, kaynak, "belirsiz", None, None,
                           f"onaylı ad '{o['kaynak_adi']}' bu aday listesinde yok", sorted(adaylar)[:5])
        n = normallestir(nesine_adi)
        birebir = [a for a in adaylar if normallestir(a) == n]
        if len(birebir) == 1 and ayirt_ediciler(nesine_adi) == ayirt_ediciler(birebir[0]):
            return Eslesme(nesine_adi, kaynak, "kesin", birebir[0], 1.0, "normalleştirilmiş ad birebir aynı ve tek")
        if len(birebir) > 1:
            return Eslesme(nesine_adi, kaynak, "belirsiz", None, 1.0, "birden çok aday aynı ada normalleşiyor",
                           birebir)
        puanli = sorted(((benzerlik(nesine_adi, a), a) for a in adaylar), reverse=True)
        oneriler = [{"ad": a, "skor": s} for s, a in puanli[:3] if s >= oneri_esigi]
        if oneriler:
            return Eslesme(nesine_adi, kaynak, "belirsiz", None, oneriler[0]["skor"],
                           "birebir eşleşme yok; öneriler kullanıcı onayı gerektirir", oneriler)
        return Eslesme(nesine_adi, kaynak, "yok", None, puanli[0][0] if puanli else None, "uygun aday bulunamadı")

    def onay_ekle(self, nesine_adi: str, kaynak: str, kaynak_adi: str, ulke: str | None = None,
                  onaylayan: str = "kullanici", kaydet: bool = True) -> dict:
        """Yalnızca kullanıcı açıkça onayladığında çağrılır."""
        if self._onayli(nesine_adi, kaynak, ulke):
            raise ValueError(f"'{nesine_adi}' için {kaynak} eşlemesi zaten var; önce kaldırın")
        k = {"nesine_adi": nesine_adi, "kaynak": kaynak, "kaynak_adi": kaynak_adi, "ulke": ulke,
             "onaylayan": onaylayan, "tarih": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        self.kayitlar.append(k)
        if kaydet:
            self.dosya.parent.mkdir(parents=True, exist_ok=True)
            self.dosya.write_text(json.dumps(self.kayitlar, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return k
