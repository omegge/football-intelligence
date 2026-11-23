"""OpenFootball (github.com/openfootball/football.json, CC0) okuyucusu.

Erişim yalnızca git klonuyla (yeni host izni yok). Klon `output/kaynak_veri/` altında, git dışında durur.
Okuyucu ağa çıkmaz; yalnızca klasördeki JSON dosyalarını okur ve veri anlık görüntüsünü (commit + dosya özetleri)
kaydeder. Oran içermez.

Dosya biçimi: <sezon>/<lig>.json -> {"name", "matches":[{"round","date","time","team1","team2",
"score":{"ft":[e,d],"ht":[e,d]}}]}; bazı dosyalarda "score" listedir ya da "rounds" altında maçlar vardır.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from ..takim_adlari import normallestir

KOK = Path(__file__).resolve().parents[3] / "output" / "kaynak_veri" / "openfootball-football.json"
SEZON_DESENI = re.compile(r"\d{4}(-\d{2})?")


def _skor(m: dict, anahtar: str):
    s = m.get("score")
    if isinstance(s, dict):
        v = s.get(anahtar)
    elif isinstance(s, list) and anahtar == "ft":
        v = s
    else:
        v = None
    if isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) for x in v):
        return v
    return None


def _maclar(d: dict) -> list[dict]:
    return d.get("matches") or [m for r in d.get("rounds", []) for m in r.get("matches", [])]


def commit_kimligi(kok: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(kok), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def lig_oku(lig: str, kok: Path = KOK, sezonlar: list[str] | None = None) -> tuple[list[dict], dict]:
    """Bir ligin bütün (ya da seçili) sezonlarındaki SKORLU maçları tarih sırasıyla döndürür.
    Dönüş: (maclar, kaynak). Takım anahtarı `normallestir(ad)`; ham ad da saklanır."""
    kok = Path(kok)
    maclar, dosyalar, atlanan = [], {}, 0
    for d in sorted(p for p in kok.iterdir() if p.is_dir() and SEZON_DESENI.fullmatch(p.name)):
        if sezonlar and d.name not in sezonlar:
            continue
        f = d / f"{lig}.json"
        if not f.exists():
            continue
        ham = f.read_bytes()
        dosyalar[d.name] = hashlib.sha256(ham).hexdigest()
        for i, m in enumerate(_maclar(json.loads(ham))):
            ft = _skor(m, "ft")
            if not ft or not m.get("date") or not m.get("team1") or not m.get("team2"):
                atlanan += 1
                continue
            ht = _skor(m, "ht")
            maclar.append({"sezon": d.name, "tarih": m["date"], "saat": m.get("time"), "tur": m.get("round"),
                           "ev": normallestir(m["team1"]), "dep": normallestir(m["team2"]),
                           "ev_ad": m["team1"], "dep_ad": m["team2"], "ev_gol": ft[0], "dep_gol": ft[1],
                           "iy_ev": ht[0] if ht else None, "iy_dep": ht[1] if ht else None,
                           "kaynak_sira": i})
    maclar.sort(key=lambda m: (m["tarih"], m["saat"] or "", m["ev"]))
    kaynak = {"kaynak": "OpenFootball football.json (CC0 1.0)", "lig": lig, "klasor": str(kok),
              "commit": commit_kimligi(kok), "dosya_sha256": dosyalar, "skorsuz_atlanan": atlanan,
              "mac_sayisi": len(maclar), "son_mac_tarihi": maclar[-1]["tarih"] if maclar else None}
    return maclar, kaynak


def sezon_takimlari(maclar: list[dict]) -> dict[str, set]:
    s: dict[str, set] = {}
    for m in maclar:
        s.setdefault(m["sezon"], set()).update((m["ev"], m["dep"]))
    return s
