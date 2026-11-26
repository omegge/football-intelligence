"""Güncel veri birleştirme: OpenFootball geçmişi + football-data.org (ücretsiz plan) 2026-27 sezonu.

Kurallar:
- football-data.org verisi yalnızca `season=YYYY` sorgusuyla alınır. Uzun tarih aralıklı sorgu bu planda SESSİZCE EKSİK
  sonuç döndürüyor (26.11.2026 denetimi: ELC 2026-08-01…11-26 aralığı 80 maç, season=2026 sorgusu 204 biten maç).
- Takım eşlemesi yalnızca 'kesin' (normalleştirilmiş ad birebir) ya da kullanıcı onaylı; diğerleri aday listesine yazılır
  ve o takımın maçları EKLENMEZ.
- Çakışan dönemde (OpenFootball'un da kaydı olan maçlar) iki kaynağın maç sonu ve ilk yarı skoru karşılaştırılır.
  Tek bir uyuşmazlık bile raporlanır; uyuşmazlıkta OpenFootball kaydı tutulur, maç işaretlenir.
- Yalnızca normal süre skoru (90 dk) kullanılır; uzatma/penaltı skoru alınmaz.
- MK-1: football-data.org `odds` alanı okunmaz (okuyucu düzeyinde).
"""
from __future__ import annotations

from datetime import date, timedelta

from ..takim_adlari import TakimEslestirici, normallestir
from . import openfootball as O

FD_KODU = {"en.1": "PL", "en.2": "ELC", "de.1": "BL1", "it.1": "SA", "es.1": "PD", "fr.1": "FL1", "nl.1": "DED",
           "pt.1": "PPL", "uefa.cl": "CL"}
SEZON = "2026-27"


def fd_sezon(kod: str, yil: int = 2026, istemci=None) -> tuple[list[dict], dict]:
    from .footballdataorg import FdorgIstemcisi, adres, maclari_ayristir
    istemci = istemci or FdorgIstemcisi()
    veri, meta = istemci.getir(adres("maclar", kod, season=yil), 900)
    return maclari_ayristir(veri), meta


def birlestir(of_maclar: list[dict], fd_maclar: list[dict], lig: str, sezon: str = SEZON,
              eslestirici: TakimEslestirici | None = None) -> tuple[list[dict], dict]:
    """OpenFootball maçlarına (lig_oku biçimi) football-data.org'un bitmiş normal süre maçlarını ekler."""
    E = eslestirici or TakimEslestirici()
    yakin = [m for m in of_maclar if m["sezon"] in (sezon, _onceki(sezon))]
    adaylar = sorted({m["ev_ad"] for m in yakin} | {m["dep_ad"] for m in yakin})
    anahtar = {m["ev_ad"]: m["ev"] for m in yakin} | {m["dep_ad"]: m["dep"] for m in yakin}
    harita, esmeyen = {}, {}
    for ad in sorted({m["ev"] for m in fd_maclar} | {m["dep"] for m in fd_maclar}):
        r = E.eslestir(ad, f"openfootball:{lig}", adaylar)
        if r.kullanilabilir:
            harita[ad] = anahtar[r.kaynak_adi]
        else:
            esmeyen[ad] = {"durum": r.durum, "alternatifler": r.alternatifler}
    of_sezon = {(m["ev"], m["dep"]): m for m in of_maclar if m["sezon"] == sezon}
    rapor = {"lig": lig, "fd_bitmis": 0, "ayni": 0, "farkli": [], "eklenen": 0, "eslenmeyen_takim": esmeyen,
             "esleme_disi_atlanan": 0, "normal_sure_yok": 0, "iy_eksik_eklenen": 0}
    eklenen = []
    for m in fd_maclar:
        if m["durum"] != "FINISHED":
            continue
        rapor["fd_bitmis"] += 1
        if m["normal_sure_ev"] is None:
            rapor["normal_sure_yok"] += 1
            continue
        if m["ev"] not in harita or m["dep"] not in harita:
            rapor["esleme_disi_atlanan"] += 1
            continue
        ev, dep = harita[m["ev"]], harita[m["dep"]]
        tarih = m["utc_baslama"][:10]
        o = of_sezon.get((ev, dep))
        if o is not None and abs((date.fromisoformat(o["tarih"]) - date.fromisoformat(tarih)).days) <= 3:
            ayni_ms = (o["ev_gol"], o["dep_gol"]) == (m["normal_sure_ev"], m["normal_sure_dep"])
            ayni_iy = o["iy_ev"] is None or m["iy_ev"] is None or (o["iy_ev"], o["iy_dep"]) == (m["iy_ev"], m["iy_dep"])
            if ayni_ms and ayni_iy:
                rapor["ayni"] += 1
            else:
                rapor["farkli"].append({"tarih": tarih, "ev": ev, "dep": dep, "of": [o["ev_gol"], o["dep_gol"], o["iy_ev"],
                                        o["iy_dep"]], "fd": [m["normal_sure_ev"], m["normal_sure_dep"], m["iy_ev"],
                                        m["iy_dep"]]})
            continue
        if m["sure_turu"] != "REGULAR":
            rapor["normal_sure_yok"] += 1   # kupa: uzatmalı maçta 'regularTime' güvenilirliği ayrıca doğrulanmadı
            continue
        if m["iy_ev"] is None:
            rapor["iy_eksik_eklenen"] += 1
        eklenen.append({"sezon": sezon, "tarih": tarih, "saat": m["utc_baslama"][11:16], "tur": f"Matchday {m['hafta']}",
                        "ev": ev, "dep": dep, "ev_ad": m["ev"], "dep_ad": m["dep"], "ev_gol": m["normal_sure_ev"],
                        "dep_gol": m["normal_sure_dep"], "iy_ev": m["iy_ev"], "iy_dep": m["iy_dep"],
                        "kaynak": "football-data.org", "kaynak_id": m["kaynak_id"]})
    rapor["eklenen"] = len(eklenen)
    tum = sorted(of_maclar + eklenen, key=lambda x: (x["tarih"], x.get("saat") or "", x["ev"]))
    rapor["son_tarih"] = tum[-1]["tarih"] if tum else None
    return tum, rapor


def _onceki(sezon: str) -> str:
    y = int(sezon[:4])
    return f"{y - 1}-{str(y)[2:]}"


def lig_guncel(lig: str, istemci=None) -> tuple[list[dict], dict]:
    """Ligin okunabilen bütün OpenFootball sezonları + football-data.org 2026-27."""
    of, atlanan = [], []
    for d in sorted(p for p in O.KOK.iterdir() if p.is_dir() and O.SEZON_DESENI.fullmatch(p.name)):
        if (d / f"{lig}.json").exists():
            try:
                of.extend(O.lig_oku(lig, sezonlar=[d.name])[0])
            except O.VeriTutarsizligi as e:
                atlanan.append({"sezon": d.name, "neden": str(e)[:160]})
    fd, meta = fd_sezon(FD_KODU[lig], 2026, istemci)
    tum, rapor = birlestir(of, fd, lig)
    rapor["fd_meta"] = {k: meta.get(k) for k in ("url", "erisim_utc", "sha256", "onbellekten", "atif")}
    rapor["openfootball_atlanan_sezonlar"] = atlanan
    return tum, rapor


# ------------------------------------------------------------------------------------------- güncelleme + bütünlük
from collections import Counter as _Counter
import hashlib as _hashlib
import json as _json
from datetime import datetime as _dt, timezone as _tz
from pathlib import Path as _Path

GUNCEL_KOK = O.KOK.parents[1] / "guncel"


def butunluk(fd_maclar: list[dict], onceki: list[dict] | None = None) -> dict:
    """season=… çekiminin iç tutarlılığı ve önceki çekimle karşılaştırma. Sorun = boş olmayan liste."""
    takimlar = {m["ev"] for m in fd_maclar} | {m["dep"] for m in fd_maclar}
    tur_basi = len(takimlar) // 2
    biten = [m for m in fd_maclar if m["durum"] == "FINISHED"]
    hafta = _Counter(m["hafta"] for m in biten if m.get("asama") in (None, "REGULAR_SEASON"))
    son_tam = max((h for h, n in hafta.items() if n == tur_basi), default=0)
    tum_hafta = _Counter(m["hafta"] for m in fd_maclar if m.get("asama") in (None, "REGULAR_SEASON"))
    # Kayıt hiç yoksa veri eksikliği; kayıt var ama bitmemişse (ertelenmiş/yeniden planlanmış) yalnızca bilgi
    eksik_hafta = {h: n for h, n in hafta.items() if h <= son_tam and tum_hafta[h] < tur_basi}
    ertelenen = [{"hafta": m["hafta"], "mac": f"{m['ev']} - {m['dep']}", "durum": m["durum"], "yeni_tarih": m["utc_baslama"][:10]}
                 for m in fd_maclar if m.get("asama") in (None, "REGULAR_SEASON") and m["durum"] != "FINISHED"
                 and m["hafta"] is not None and m["hafta"] <= son_tam]
    cift = [k for k, n in _Counter((m["ev"], m["dep"]) for m in fd_maclar
                                   if m.get("asama") in (None, "REGULAR_SEASON")).items() if n > 1]
    skorsuz_biten = [m["kaynak_id"] for m in biten if m["normal_sure_ev"] is None]
    iy_eksik = [m["kaynak_id"] for m in biten if m["iy_ev"] is None]
    sonuc = {"takim": len(takimlar), "toplam": len(fd_maclar), "biten": len(biten), "son_tam_hafta": son_tam,
             "son_tam_haftadan_once_eksik": eksik_hafta, "ertelenen_bilgi": ertelenen, "mukerrer_eslesme": cift, "skorsuz_biten": skorsuz_biten,
             "iy_eksik_biten": iy_eksik}
    if onceki is not None:
        o = {m["kaynak_id"]: m for m in onceki if m["durum"] == "FINISHED"}
        y = {m["kaynak_id"]: m for m in biten}
        sonuc["onceki_biten"] = len(o)
        sonuc["kaybolan_biten"] = sorted(set(o) - set(y))
        sonuc["skoru_degisen"] = sorted(k for k in set(o) & set(y)
                                        if (o[k]["normal_sure_ev"], o[k]["normal_sure_dep"], o[k]["iy_ev"], o[k]["iy_dep"])
                                        != (y[k]["normal_sure_ev"], y[k]["normal_sure_dep"], y[k]["iy_ev"], y[k]["iy_dep"]))
    sonuc["sorunlar"] = [k for k in ("son_tam_haftadan_once_eksik", "mukerrer_eslesme", "skorsuz_biten",
                                     "kaybolan_biten", "skoru_degisen") if sonuc.get(k)]
    return sonuc


def guncelle(kodlar=tuple(FD_KODU.values()), istemci=None, kok: _Path = GUNCEL_KOK) -> dict:
    """Her yarışma için season=2026 çekimi + bütünlük; anlık görüntü output/guncel/<zaman>/ altına (git dışı)."""
    from .footballdataorg import FdorgIstemcisi
    istemci = istemci or FdorgIstemcisi()
    simdi = _dt.now(_tz.utc)
    hedef = _Path(kok) / simdi.strftime("%Y%m%dT%H%M%SZ")
    hedef.mkdir(parents=True, exist_ok=True)
    onceki_klasor = sorted(p for p in _Path(kok).iterdir() if p.is_dir() and p != hedef)[-1:] if _Path(kok).exists() else []
    rapor = {"utc": simdi.isoformat(timespec="seconds"), "yarismalar": {}}
    for kod in kodlar:
        ms, meta = fd_sezon(kod, 2026, istemci)
        onceki = None
        if onceki_klasor and (onceki_klasor[0] / f"{kod}.json").exists():
            onceki = _json.loads((onceki_klasor[0] / f"{kod}.json").read_text())
        b = butunluk(ms, onceki)
        govde = _json.dumps(ms, ensure_ascii=False, sort_keys=True).encode()
        (hedef / f"{kod}.json").write_bytes(govde)
        rapor["yarismalar"][kod] = {"butunluk": b, "kaynak_sha256": meta.get("sha256"),
                                    "kayit_sha256": _hashlib.sha256(govde).hexdigest(), "url": meta.get("url"),
                                    "son_biten_utc": max((m["utc_baslama"] for m in ms if m["durum"] == "FINISHED"), default=None)}
    rapor["sorunlu"] = {k: v["butunluk"]["sorunlar"] for k, v in rapor["yarismalar"].items() if v["butunluk"]["sorunlar"]}
    (hedef / "rapor.json").write_text(_json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
    return rapor


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["guncelle"]:
        r = guncelle()
        for k, v in r["yarismalar"].items():
            b = v["butunluk"]
            print(k, "biten", b["biten"], "son tam hafta", b["son_tam_hafta"], "son", (v["son_biten_utc"] or "")[:10],
                  "SORUN" if b["sorunlar"] else "temiz", b["sorunlar"])
