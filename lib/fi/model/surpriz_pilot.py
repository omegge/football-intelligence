"""S aşaması pilot seçimi (ön kayıt: ON_KAYIT_S.md). Yalnızca sonuç ve bağımsız model olasılığı kullanılır; oran yok.

Kullanım: PYTHONPATH=lib python3 -m fi.model.surpriz_pilot
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from ..kaynaklar import openfootball as O
from .backtest import yuruyen_test
from .goller import GolModeli

BURASI = Path(__file__).resolve().parent
CIKTI = BURASI.parents[2] / "output" / "arastirma" / "surpriz_pilot_v1"
LIGLER = ("en.1", "es.1", "de.1", "it.1", "fr.1")
SEZONLAR = ("2022-23", "2023-24", "2024-25", "2025-26")
KOTA = {"50-60": 2, "60-70": 3, "70-80": 3, "80+": 2}
SIRA = ["80+", "70-80", "60-70", "50-60"]


def kategori(p: float) -> str | None:
    if p < 0.5:
        return None
    return "50-60" if p < 0.6 else "60-70" if p < 0.7 else "70-80" if p < 0.8 else "80+"


def lig_kayitlari(lig: str) -> list[dict]:
    from .e_asamasi import lig_verisi
    maclar, _ = lig_verisi(lig)
    gm = GolModeli(xi=0.003, pencere_gun=1095, ceza=2.0, yeni_hucum=0.8, yeni_savunma=1.2, dixon_coles=False)
    kay = yuruyen_test(maclar, [gm], "2022-07-01", "2026-06-30", O.sezon_takimlari(maclar))
    out = []
    for k in kay:
        if k["sezon"] not in SEZONLAR:
            continue
        p = k["tahmin"]["poisson"]
        out.append({"yarisma": lig, "sezon": k["sezon"], "tarih": k["tarih"], "ev": k["ev_ad"], "dep": k["dep_ad"],
                    "skor": [k["ev_gol"], k["dep_gol"]], "P": {"H": p["H"], "D": p["D"], "A": p["A"]},
                    "model": "Poisson (E ayarı)", "egitim_kesimi": k["egitim_kesimi"]})
    return out


def ucl_kayitlari() -> list[dict]:
    from . import ligler_arasi as L
    s = L.calistir()
    out = []
    for k in s["kayitlar"]:
        if k["sezon"] != "2024-25" or not k.get("M1_ortak_elo"):
            continue
        g = k["sonuc"]
        out.append({"yarisma": "uefa.cl", "sezon": k["sezon"], "tarih": k["tarih"], "ev": k["ev_ad"], "dep": k["dep_ad"],
                    "sonuc_kodu": g, "P": dict(k["M1_ortak_elo"]), "model": "M1 ortak Elo", "tur": k.get("tur")})
    return out


def favori_bilgisi(m: dict) -> dict | None:
    p = m["P"]
    taraf = "ev" if p["H"] >= p["A"] else "dep"
    pf = max(p["H"], p["A"])
    kat = kategori(pf)
    if kat is None:
        return None
    if "skor" in m:
        e, d = m["skor"]
        sonuc = "H" if e > d else ("D" if e == d else "A")
    else:
        sonuc = m["sonuc_kodu"]
    kazandi = (sonuc == "H" and taraf == "ev") or (sonuc == "A" and taraf == "dep")
    return {**m, "favori_saha": taraf, "favori": m[taraf], "rakip": m["dep" if taraf == "ev" else "ev"],
            "P_favori": round(pf, 4), "kategori": kat, "sonuc": sonuc,
            "etiket": "favori_kazandi" if kazandi else ("berabere" if sonuc == "D" else "favori_kaybetti")}


def sec(havuz: list[dict], tohum: int) -> dict:
    rnd = random.Random(tohum)
    surpriz = [m for m in havuz if m["etiket"] != "favori_kazandi"]
    secilen, kullanilan_fav, notlar = [], set(), []
    eksik = 0
    for kat in SIRA:
        istenen = KOTA[kat] + eksik
        aday = sorted([m for m in surpriz if m["kategori"] == kat and m["favori"] not in kullanilan_fav],
                      key=lambda m: (m["tarih"], m["ev"]))
        al = []
        while aday and len(al) < istenen:
            m = aday.pop(rnd.randrange(len(aday)))
            if m["favori"] in kullanilan_fav:
                continue
            al.append(m)
            kullanilan_fav.add(m["favori"])
        eksik = istenen - len(al)
        if eksik:
            notlar.append(f"{kat}: {eksik} eksik, bir alt kategoriden tamamlandı")
        secilen += al
    kullanilan = {(m["yarisma"], m["tarih"], m["ev"]) for m in secilen}
    kontroller = []
    for s in secilen:
        aday = [m for m in havuz if m["etiket"] == "favori_kazandi" and m["yarisma"] == s["yarisma"]
                and m["sezon"] == s["sezon"] and m["favori_saha"] == s["favori_saha"]
                and (m["yarisma"], m["tarih"], m["ev"]) not in kullanilan]
        aday.sort(key=lambda m: (abs(m["P_favori"] - s["P_favori"]), m["favori"] == s["favori"], m["tarih"]))
        k = aday[0] if aday else None
        if k:
            kullanilan.add((k["yarisma"], k["tarih"], k["ev"]))
        kontroller.append(k)
    return {"surprizler": secilen, "kontroller": kontroller, "notlar": notlar}


def main() -> int:
    on = BURASI / "ON_KAYIT_S.md"
    oz = hashlib.sha256(on.read_bytes()).hexdigest()
    assert oz == (BURASI / "ON_KAYIT_S.sha256").read_text().strip(), "ön kayıt değişmiş"
    ham = [m for lig in LIGLER for m in lig_kayitlari(lig)] + ucl_kayitlari()
    havuz = [x for x in (favori_bilgisi(m) for m in ham) if x]
    set_v1 = json.loads((BURASI.parents[2] / "output" / "arastirma" / "set_v1" / "arastirma_seti.json").read_text())
    eski = {(k["tarih"], k["ev"]) for grup in set_v1["kartlar"].values() for k in grup}
    s = sec(havuz, int(oz[:16], 16))
    for m in s["surprizler"] + [k for k in s["kontroller"] if k]:
        m["set_v1_tekrar"] = (m["tarih"], m["ev"]) in eski
    dagilim = {}
    for m in havuz:
        d = dagilim.setdefault(m["kategori"], {"mac": 0, "favori_kazandi": 0, "berabere": 0, "favori_kaybetti": 0})
        d["mac"] += 1
        d[m["etiket"]] += 1
    CIKTI.mkdir(parents=True, exist_ok=True)
    (CIKTI / "havuz.json").write_text(json.dumps(havuz, ensure_ascii=False, default=str), encoding="utf-8")
    ornek = []
    for anahtar in (("uefa.cl", "Lille"), ("en.1", "Bournemouth")):
        for m in havuz + [favori_bilgisi(x) or x for x in ham if "Real Madrid" in x["dep"] and "Lille" in x["ev"]]:
            if m and m.get("yarisma") == anahtar[0] and anahtar[1] in m["ev"] and (
                    "Real Madrid" in m["dep"] or "Manchester City" in m["dep"]):
                ornek.append(m)
                break
    s["kullanici_ornekleri"] = ornek
    sonuc = {"on_kayit_sha256": oz, "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "havuz_mac": len(ham), "favorili_mac": len(havuz), "kategori_dagilimi": dagilim, **s}
    (CIKTI / "pilot_secimi.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"havuz": len(ham), "favorili": len(havuz), "dagilim": dagilim, "notlar": s["notlar"]}, ensure_ascii=False))
    for a, b in zip(s["surprizler"], s["kontroller"]):
        print(f"S {a['tarih']} {a['yarisma']:7s} {a['ev']} {a.get('skor') or a['sonuc']} {a['dep']} | fav {a['favori']} {a['P_favori']} [{a['kategori']}] {a['etiket']}{' TEKRAR' if a['set_v1_tekrar'] else ''}")
        if b:
            print(f"   K {b['tarih']} {b['ev']} {b.get('skor') or b['sonuc']} {b['dep']} | fav {b['favori']} {b['P_favori']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
