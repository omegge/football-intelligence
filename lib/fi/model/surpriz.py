"""Sürpriz sonuç analizi ve favori galibiyet serisi değerlendirmesi.

Favori, Nesine oranlarına göre DEĞİL, değerlendirilen modelin kendi maç öncesi olasılığına göre belirlenir (MK-1).
- Favori maçı: max(P(H), P(A)) ≥ `favori_esigi`.
- Sürpriz: favorinin kaybetmesi (zayıf tarafın kazanması). Ayrıca "favori kazanamadı" (beraberlik dahil) da raporlanır.
- Alarm: zayıf tarafın kazanma olasılığı ≥ eşik. İsabet (precision), yakalama (recall), yanlış alarm oranı
  (1 − isabet), yanlış pozitif oranı (sürpriz olmayan maçlarda alarm), taban orana göre kaldıraç (lift) ve AUC.
"""

from __future__ import annotations

import math

import numpy as np

from .metrikler import auc, kalibrasyon


def favori(p: dict) -> tuple[str, str]:
    return ("H", "A") if p["H"] >= p["A"] else ("A", "H")


def surpriz_analizi(kayitlar: list[dict], model: str, favori_esigi: float = 0.5,
                    alarm_esikleri=(0.15, 0.20, 0.25, 0.30)) -> dict:
    s = []
    for k in kayitlar:
        p = k["tahmin"][model]
        f, z = favori(p)
        if p[f] < favori_esigi:
            continue
        s.append((p[f], p[z], k["sonuc"] == z, k["sonuc"] != f))
    if not s:
        return {"n": 0}
    pf = np.array([x[0] for x in s])
    pz = np.array([x[1] for x in s])
    surp = np.array([x[2] for x in s])
    kazanamadi = np.array([x[3] for x in s])
    taban = float(surp.mean())
    alarmlar = []
    for t in alarm_esikleri:
        a = pz >= t
        na, tp = int(a.sum()), int((a & surp).sum())
        alarmlar.append({
            "esik": t, "alarm": na, "dogru_alarm": tp,
            "isabet": round(tp / na, 4) if na else None,
            "yanlis_alarm_orani": round(1 - tp / na, 4) if na else None,
            "yakalama": round(tp / int(surp.sum()), 4) if surp.sum() else None,
            "yanlis_pozitif_orani": round(int((a & ~surp).sum()) / int((~surp).sum()), 4) if (~surp).sum() else None,
            "kaldirac": round((tp / na) / taban, 3) if na and taban else None})
    return {"n_favori_maci": len(s), "favori_esigi": favori_esigi,
            "surpriz_orani": round(taban, 4), "ort_tahmin_surpriz": round(float(pz.mean()), 4),
            "favori_kazanamadi_orani": round(float(kazanamadi.mean()), 4),
            "ort_tahmin_favori_kazanamadi": round(float((1 - pf).mean()), 4),
            "auc_zayif_kazanir": None if auc(pz, surp) is None else round(auc(pz, surp), 4),
            "alarmlar": alarmlar, "kalibrasyon_zayif_kazanir": kalibrasyon(pz, surp, 10)}


def seri_analizi(kayitlar: list[dict], model: str, gecmis: list[dict], min_seri: int = 3,
                 favori_esigi: float = 0.5) -> dict:
    """Favorinin maç öncesi lig galibiyet serisi (≥ min_seri) ve serideki rakiplerin maç öncesi göreli Elo'su.
    Model olasılığı ile gerçekleşen favori galibiyet oranı gruplar arasında karşılaştırılır. `gecmis` her maç için
    {'tarih','ev','dep','sonuc','elo_ev_goreli','elo_dep_goreli'} içerir (yalnızca maç öncesi değerler)."""
    sira: dict[str, list] = {}
    for m in gecmis:
        for t, r, rakip_goreli in ((m["ev"], {"H": "G", "D": "B", "A": "M"}[m["sonuc"]], m["elo_dep_goreli"]),
                                   (m["dep"], {"A": "G", "D": "B", "H": "M"}[m["sonuc"]], m["elo_ev_goreli"])):
            sira.setdefault(t, []).append((m["tarih"], r, rakip_goreli))

    def seri(takim: str, tarih: str):
        n, rakipler = 0, []
        for t, r, g in reversed([x for x in sira.get(takim, []) if x[0] < tarih]):
            if r != "G":
                break
            n += 1
            rakipler.append(g)
        return n, (float(np.mean(rakipler)) if rakipler else None)

    gruplar: dict[str, list] = {"seri_yok": [], "seri_guclu_rakipler": [], "seri_zayif_rakipler": []}
    for k in kayitlar:
        p = k["tahmin"][model]
        f, _ = favori(p)
        if p[f] < favori_esigi:
            continue
        takim = k["ev"] if f == "H" else k["dep"]
        n, g = seri(takim, k["tarih"])
        ad = "seri_yok" if n < min_seri else ("seri_guclu_rakipler" if g >= 0 else "seri_zayif_rakipler")
        gruplar[ad].append((p[f], k["sonuc"] == f))
    out = {}
    for ad, v in gruplar.items():
        if not v:
            out[ad] = {"n": 0}
            continue
        pt, gr = np.array([x[0] for x in v]), np.array([x[1] for x in v], float)
        fark = gr.mean() - pt.mean()
        se = math.sqrt(max(gr.mean() * (1 - gr.mean()), 1e-9) / len(v))
        out[ad] = {"n": len(v), "ort_tahmin_favori_kazanir": round(float(pt.mean()), 4),
                   "gerceklesen": round(float(gr.mean()), 4), "fark": round(float(fark), 4),
                   "fark_alt95": round(float(fark - 1.96 * se), 4), "fark_ust95": round(float(fark + 1.96 * se), 4)}
    out["tanim"] = (f"seri = favorinin maçtan hemen önceki ardışık lig galibiyetleri (≥{min_seri}); rakip gücü = serideki "
                    "rakiplerin maç öncesi Elo'sunun o anki lig ortalamasına farkı (≥0 güçlü, <0 zayıf)")
    return out
