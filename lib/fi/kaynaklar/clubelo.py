"""ClubElo okuyucusu (kulüp gücü / rakip gücü).

Beklenen biçim (ilk gerçek erişimde doğrulanacak; doğrulanana kadar DOGRULANMIS_BICIM = False):
  http://api.clubelo.com/YYYY-MM-DD   -> o gündeki bütün kulüpler
  http://api.clubelo.com/KulupAdi     -> bir kulübün geçmişi
  CSV sütunları: Rank, Club, Country, Level, Elo, From, To
Elo bir derecelendirmedir; bahis oranı içermez. ClubElo'nun kendi maç tahminleri (Fixtures) burada okunmaz.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from ..kanit import Kanit

TABAN = "http://api.clubelo.com"
GEREKLI_SUTUNLAR = {"Club", "Country", "Elo", "From", "To"}
DOGRULANMIS_BICIM = False


class BicimHatasi(ValueError):
    pass


def gun_url(gun: date) -> str:
    return f"{TABAN}/{gun.isoformat()}"


def kulup_url(kulup: str) -> str:
    return f"{TABAN}/{kulup.replace(' ', '')}"


def ayristir(metin: str) -> list[dict]:
    okuyucu = csv.DictReader(io.StringIO(metin.lstrip("﻿")))
    sutunlar = set(okuyucu.fieldnames or [])
    eksik = GEREKLI_SUTUNLAR - sutunlar
    if eksik:
        raise BicimHatasi(f"ClubElo biçimi beklenenden farklı; eksik sütunlar: {sorted(eksik)} (gelen: {sorted(sutunlar)})")
    out = []
    for i, r in enumerate(okuyucu, 2):
        try:
            elo = float(r["Elo"])
            date.fromisoformat(r["From"])
            date.fromisoformat(r["To"])
        except (TypeError, ValueError):
            raise BicimHatasi(f"ClubElo satır {i} okunamadı: {r}")
        out.append({"kulup": r["Club"], "ulke": r["Country"], "seviye": _int(r.get("Level")), "sira": _int(r.get("Rank")),
                    "elo": elo, "baslangic": r["From"], "bitis": r["To"], "satir": i})
    return out


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def gune_gore(satirlar: list[dict], gun: date) -> list[dict]:
    g = gun.isoformat()
    return [r for r in satirlar if r["baslangic"] <= g <= r["bitis"]]


def elo_kaniti(satir: dict, mac_id: str, meta: dict) -> Kanit:
    """ClubElo satırını kanıta çevirir. Ölçüm dönemi = satırın geçerli olduğu tarih aralığı."""
    return Kanit(mac_id=mac_id, konu="elo", iddia=f"{satir['kulup']} ClubElo puanı {satir['elo']:.1f}",
                 deger={"elo": satir["elo"], "seviye": satir["seviye"], "ulke": satir["ulke"]}, birim="Elo",
                 takim=satir["kulup"], kaynak_adi="ClubElo", kaynak_url=meta["url"], erisim_zamani=meta["erisim_utc"],
                 dogrulama="veri_kaynagi", olcum_baslangic=satir["baslangic"], olcum_bitis=satir["bitis"],
                 ham_sha256=meta.get("sha256"),
                 notlar=None if DOGRULANMIS_BICIM else "ClubElo biçimi henüz gerçek veriyle doğrulanmadı")
