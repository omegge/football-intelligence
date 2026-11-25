"""Yayın zamanı çözümleme ve maç başlangıcıyla karşılaştırma.

Öncelik: JSON-LD datePublished → meta (article:published_time …) → <time datetime> → görünür tarih (yalnızca gün).
Sonuç durumları:
  mac_oncesi_dogrulandi   : yayın anı (saat dahil) < başlama; ya da yayın günü başlama gününden önce
  mac_sonrasi             : yayın ≥ başlama → maç öncesi analizde KULLANILMAZ
  ayni_gun_saat_yok       : maç günü yayımlanmış, saati doğrulanamadı → maç öncesi DOĞRULANMIŞ kanıt değildir
  guncelleme_mac_sonrasi  : yayın öncesi ama sayfa başlamadan sonra güncellenmiş → mevcut sürüm maç öncesi değil
  tarih_yok               : yayın tarihi bulunamadı → kanıt olamaz
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

GECERLI = "mac_oncesi_dogrulandi"


@dataclass
class YayinZamani:
    deger: str | None        # ISO
    kaynak: str              # jsonld | meta | time_etiketi | gorunur_tarih | yok
    hassasiyet: str          # saat | gun | yok


def _ayristir(v: str) -> tuple[datetime | date | None, str]:
    v = v.strip()
    try:
        if len(v) == 10:
            return date.fromisoformat(v), "gun"
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if d.tzinfo is None:
            return None, "yok"          # saat dilimi yoksa saat karşılaştırması güvenilmez
        return d.astimezone(timezone.utc), "saat"
    except ValueError:
        return None, "yok"


def coz(adaylar: dict, gorunur: list[str]) -> tuple[YayinZamani, YayinZamani | None]:
    """(yayın, güncelleme). Saat bilgisi içeren ilk geçerli aday tercih edilir; yalnızca gün olan aday 'gun'."""
    yayin = YayinZamani(None, "yok", "yok")
    gun_adayi = None
    for kaynak, v in adaylar.get("yayin", []):
        d, h = _ayristir(v)
        if h == "saat":
            yayin = YayinZamani(d.isoformat(), kaynak, "saat")
            break
        if h == "gun" and gun_adayi is None:
            gun_adayi = YayinZamani(d.isoformat(), kaynak, "gun")
        if h == "yok" and gun_adayi is None and len(v) >= 10:
            try:
                gun_adayi = YayinZamani(date.fromisoformat(v[:10]).isoformat(), kaynak, "gun")
            except ValueError:
                pass
    if yayin.hassasiyet == "yok":
        if gun_adayi:
            yayin = gun_adayi
        elif gorunur:
            yayin = YayinZamani(gorunur[0], "gorunur_tarih", "gun")
    guncel = None
    for kaynak, v in adaylar.get("guncelleme", []):
        d, h = _ayristir(v)
        if h == "saat":
            guncel = YayinZamani(d.isoformat(), kaynak, "saat")
            break
    return yayin, guncel


def mac_oncesi_durumu(yayin: YayinZamani, baslama_utc: str, guncelleme: YayinZamani | None = None) -> str:
    """baslama_utc: saat dilimli ISO (maç başlangıcı)."""
    b = datetime.fromisoformat(baslama_utc.replace("Z", "+00:00"))
    if b.tzinfo is None:
        raise ValueError("maç başlangıcı saat dilimli olmalı")
    b = b.astimezone(timezone.utc)
    if yayin.hassasiyet == "yok" or not yayin.deger:
        return "tarih_yok"
    if yayin.hassasiyet == "saat":
        y = datetime.fromisoformat(yayin.deger)
        if y >= b:
            return "mac_sonrasi"
    else:
        g = date.fromisoformat(yayin.deger)
        if g > b.date():
            return "mac_sonrasi"
        if g == b.date():
            return "ayni_gun_saat_yok"
    if guncelleme and guncelleme.deger and datetime.fromisoformat(guncelleme.deger) >= b:
        return "guncelleme_mac_sonrasi"
    return GECERLI
