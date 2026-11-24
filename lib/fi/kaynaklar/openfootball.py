"""OpenFootball (github.com/openfootball/football.json, CC0) okuyucusu.

Erişim yalnızca git klonuyla (yeni host izni yok). Klon `output/kaynak_veri/` altında, git dışında durur.
Okuyucu ağa çıkmaz; yalnızca klasördeki JSON dosyalarını okur ve veri anlık görüntüsünü (commit + dosya özetleri)
kaydeder. Oran içermez.

Dosya biçimi: <sezon>/<lig>.json -> {"name", "matches":[{"round","date","time","team1","team2",
"score":{"ft":[e,d],"ht":[e,d]}}]}; bazı dosyalarda "score" listedir ya da "rounds" altında maçlar vardır.

Tarih bütünlüğü (veri doğruluğu önceliği):
- Kaynak dosyalar DEĞİŞTİRİLMEZ. Bilinen kaynak hataları yalnızca `veri/tarih_duzeltmeleri.json` içindeki, kanıtı
  yazılı TEKİL kayıtlarla düzeltilir (lig + sezon + takımlar + tam skor + ilk yarı + kaynak tarih tam eşleşmeli).
  Genel/otomatik bir yıl kuralı yoktur. Eşleşmeyen ya da kaynakta artık bulunmayan kayıt hata verir.
- Uygulanan her düzeltme `kaynak["tarih_duzeltmeleri"]` içinde döner.
- Kaynakta skoru BOŞ kalmış bitmiş maçlar yalnızca `veri/skor_tamamlamalari.json` içindeki, iki kaynağın tam skorda
  uyuştuğu kanıtlı kayıtlarla tamamlanır (lig + sezon + tarih + takımlar tam eşleşmeli). Kaynakta skor varsa ve kayıtla
  aynıysa ikinci kez uygulanmaz; farklıysa okuma durur. Uygulananlar `kaynak["skor_tamamlamalari"]` içinde döner.
- Düzeltmeden sonra kalan sert tutarsızlıklar (sezon yılları dışında tarih, 1. haftanın ilk maçından önce oynanmış
  maç, aynı sezonda mükerrer ev–deplasman eşleşmesi) `VeriTutarsizligi` ile okumayı durdurur. Hafta sırası
  terslikleri (ertelemelerde olağan) yalnızca uyarı olarak `kaynak["tarih_uyarilari"]`na yazılır.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from ..takim_adlari import normallestir

KOK = Path(__file__).resolve().parents[3] / "output" / "kaynak_veri" / "openfootball-football.json"
DUZELTME_DOSYASI = Path(__file__).resolve().parents[3] / "veri" / "tarih_duzeltmeleri.json"
SKOR_DOSYASI = Path(__file__).resolve().parents[3] / "veri" / "skor_tamamlamalari.json"
SEZON_DESENI = re.compile(r"\d{4}(-\d{2})?")
HAFTA_DESENI = re.compile(r"(\d+)")


class VeriTutarsizligi(ValueError):
    """Kaynak veride düzeltilmemiş sert tutarsızlık; okuma durdurulur (sessizce devam edilmez)."""


def duzeltmeleri_yukle(yol: Path | None, anahtar: str = "duzeltmeler") -> list[dict]:
    if yol is None or not Path(yol).exists():
        return []
    return json.loads(Path(yol).read_text(encoding="utf-8"))[anahtar]


def _ozet(yol: Path | None) -> str | None:
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest() if yol and Path(yol).exists() else None


def _hafta(tur) -> int | None:
    m = HAFTA_DESENI.search(tur or "")
    return int(m.group(1)) if m else None


def tarih_denetimi(maclar: list[dict]) -> tuple[list[str], list[str]]:
    """Dönüş: (sert sorunlar, uyarılar). Yalnızca maç listesine bakar; kaynak dosyaya dokunmaz."""
    sert, uyari = [], []
    sezonlar: dict[str, list] = {}
    for m in maclar:
        sezonlar.setdefault(m["sezon"], []).append(m)
    for s, ms in sorted(sezonlar.items()):
        y = int(s[:4])
        yillar = {y, y + 1} if "-" in s else {y}
        for m in ms:
            if int(m["tarih"][:4]) not in yillar:
                sert.append(f"{s}: {m['tarih']} {m['ev_ad']} – {m['dep_ad']} sezon yılları dışında")
        ilk = [m["tarih"] for m in ms if _hafta(m.get("tur")) == 1]
        if ilk:
            for m in ms:
                if m["tarih"] < min(ilk):
                    sert.append(f"{s}: {m.get('tur')} {m['tarih']} {m['ev_ad']} – {m['dep_ad']} 1. haftanın ilk maçından "
                                f"({min(ilk)}) önce")
        c: dict = {}
        for m in ms:
            c[(m["ev"], m["dep"])] = c.get((m["ev"], m["dep"]), 0) + 1
        sert += [f"{s}: {e} – {d} mükerrer ({n}×)" for (e, d), n in c.items() if n > 1]
        hafta: dict[int, list] = {}
        for m in ms:
            if _hafta(m.get("tur")) is not None:
                hafta.setdefault(_hafta(m.get("tur")), []).append(m["tarih"])
        med = {h: sorted(v)[len(v) // 2] for h, v in hafta.items()}
        sira = sorted(med)
        uyari += [f"{s}: hafta {a} (medyan {med[a]}) hafta {b}'den (medyan {med[b]}) sonra" for a, b in zip(sira, sira[1:])
                  if med[a] > med[b]]
    return sert, uyari


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


def lig_oku(lig: str, kok: Path = KOK, sezonlar: list[str] | None = None,
            duzeltmeler: Path | None = DUZELTME_DOSYASI,
            skor_tamamlamalari: Path | None = SKOR_DOSYASI) -> tuple[list[dict], dict]:
    """Bir ligin bütün (ya da seçili) sezonlarındaki SKORLU maçları tarih sırasıyla döndürür.
    Dönüş: (maclar, kaynak). Takım anahtarı `normallestir(ad)`; ham ad da saklanır.
    Kayıtlı tarih düzeltmeleri uygulanır; sert tutarsızlık kalırsa `VeriTutarsizligi`."""
    kok = Path(kok)
    maclar, dosyalar, atlanan = [], {}, 0
    duz = {(d["lig"], d["sezon"], d["ev_ad"], d["dep_ad"], tuple(d["skor"]),
            tuple(d["ilk_yari"]) if d.get("ilk_yari") else None): d for d in duzeltmeleri_yukle(duzeltmeler)}
    uygulanan, zaten_dogru, okunan_sezonlar = [], [], set()
    tam = {(k["lig"], k["sezon"], k["tarih"], k["ev_ad"], k["dep_ad"]): k
           for k in duzeltmeleri_yukle(skor_tamamlamalari, "tamamlamalar")}
    tamamlanan, kaynakta_skorlu = [], []
    for d in sorted(p for p in kok.iterdir() if p.is_dir() and SEZON_DESENI.fullmatch(p.name)):
        if sezonlar and d.name not in sezonlar:
            continue
        f = d / f"{lig}.json"
        if not f.exists():
            continue
        ham = f.read_bytes()
        dosyalar[d.name] = hashlib.sha256(ham).hexdigest()
        okunan_sezonlar.add(d.name)
        for i, m in enumerate(_maclar(json.loads(ham))):
            ft = _skor(m, "ft")
            sk = tam.get((lig, d.name, m.get("date"), m.get("team1"), m.get("team2")))
            if sk is not None:
                if ft is None:
                    ft = list(sk["skor"])
                    m = {**m, "score": {"ft": ft, "ht": sk.get("ilk_yari")}}
                    tamamlanan.append({k: sk[k] for k in ("sezon", "tarih", "ev_ad", "dep_ad", "skor")})
                elif list(ft) == list(sk["skor"]):
                    kaynakta_skorlu.append(sk)
                else:
                    raise VeriTutarsizligi(f"skor kaydı kaynakla çelişiyor: {d.name} {m['team1']} – {m['team2']} "
                                           f"kaynak {ft}, kayıt {sk['skor']}")
            if not ft or not m.get("date") or not m.get("team1") or not m.get("team2"):
                atlanan += 1
                continue
            ht = _skor(m, "ht")
            tarih = m["date"]
            kayit = duz.get((lig, d.name, m["team1"], m["team2"], tuple(ft), tuple(ht) if ht else None))
            if kayit is not None:
                if tarih == kayit["kaynak_tarih"]:
                    tarih = kayit["duzeltilmis_tarih"]
                    uygulanan.append({k: kayit[k] for k in ("sezon", "ev_ad", "dep_ad", "kaynak_tarih", "duzeltilmis_tarih")})
                elif tarih == kayit["duzeltilmis_tarih"]:
                    zaten_dogru.append(kayit)
                else:
                    raise VeriTutarsizligi(f"düzeltme kaydı kaynakla tutmuyor: {d.name} {m['team1']} – {m['team2']} "
                                           f"kaynak {tarih}, kayıt {kayit['kaynak_tarih']}")
            maclar.append({"sezon": d.name, "tarih": tarih, "saat": m.get("time"), "tur": m.get("round"),
                           "ev": normallestir(m["team1"]), "dep": normallestir(m["team2"]),
                           "ev_ad": m["team1"], "dep_ad": m["team2"], "ev_gol": ft[0], "dep_gol": ft[1],
                           "iy_ev": ht[0] if ht else None, "iy_dep": ht[1] if ht else None,
                           "kaynak_sira": i})
    kullanilan = len(uygulanan) + len(zaten_dogru)
    beklenen = sum(1 for k in duz.values() if k["lig"] == lig and k["sezon"] in okunan_sezonlar)
    if kullanilan != beklenen:
        raise VeriTutarsizligi(f"{lig}: {beklenen} düzeltme kaydından yalnızca {kullanilan} tanesi kaynakta bulundu")
    beklenen_skor = sum(1 for k in tam.values() if k["lig"] == lig and k["sezon"] in okunan_sezonlar)
    if len(tamamlanan) + len(kaynakta_skorlu) != beklenen_skor:
        raise VeriTutarsizligi(f"{lig}: {beklenen_skor} skor kaydından yalnızca "
                               f"{len(tamamlanan) + len(kaynakta_skorlu)} tanesi kaynakta bulundu")
    sert, uyari = tarih_denetimi(maclar)
    if sert:
        raise VeriTutarsizligi(f"{lig}: {len(sert)} düzeltilmemiş tarih tutarsızlığı: " + "; ".join(sert[:5]))
    maclar.sort(key=lambda m: (m["tarih"], m["saat"] or "", m["ev"]))
    kaynak = {"kaynak": "OpenFootball football.json (CC0 1.0)", "lig": lig, "klasor": str(kok),
              "commit": commit_kimligi(kok), "dosya_sha256": dosyalar, "skorsuz_atlanan": atlanan,
              "mac_sayisi": len(maclar), "son_mac_tarihi": maclar[-1]["tarih"] if maclar else None,
              "tarih_duzeltmeleri": uygulanan, "kaynakta_duzelmis_kayit": len(zaten_dogru),
              "duzeltme_dosyasi_sha256": _ozet(duzeltmeler),
              "skor_tamamlamalari": tamamlanan, "kaynakta_skorlu_kayit": len(kaynakta_skorlu),
              "skor_dosyasi_sha256": _ozet(skor_tamamlamalari),
              "tarih_uyarilari": uyari}
    return maclar, kaynak


def sezon_takimlari(maclar: list[dict]) -> dict[str, set]:
    s: dict[str, set] = {}
    for m in maclar:
        s.setdefault(m["sezon"], set()).update((m["ev"], m["dep"]))
    return s
