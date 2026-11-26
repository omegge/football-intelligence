"""H aşaması: kart ve hakem — PROTOTİP (ön kayıt bu docstring; tek çalıştırma, ayar yok).

Veri: OpenFootball '*-full' (CC0), yalnızca 2025-26 en.1, de.1, at.1 (izinli tek kart/hakem kaynağı). 'bookings' alanı
boş maç = kayıt yok ya da kartsız AYIRT EDİLEMEZ → değerlendirme dışı (0 sayılmaz). Kart olayı = her kayıt (Y, Y/R, R).
Nesine 'Kart Puanı' kuralı (sarı/kırmızı puanı) doğrulanmadı → Nesine marketine EŞLENMEZ.
Zaman ayrımı: 2026-01-01 öncesi yalnızca eğitim; sonrası genişleyen pencereyle (tahmin günü öncesi maçlar) test.
Modeller (k = 5 maç büzülme, önceden sabit):
  H0 lig ortalaması (Poisson, toplam kart)
  H1 takım eğilimi: λ = ort_ev_kendi + ort_dep_kendi (her biri lig takım ortalamasına k ile büzülmüş)
  H2 H1 × hakem çarpanı (hakemin maç başı toplamı / lig ortalaması, k ile 1'e büzülmüş). Hakem adı kaynağın geçmiş
     maç kaydından; GELECEK maçta hakem ataması doğrulanmadıkça H2 KULLANILMAZ.
Ölçüt: Poisson log olabilirlik (maç başı, yüksek iyi), ≥5 kart olayı için Brier; tarih kümeli bootstrap.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..kaynaklar import openfootball as O
from ..takim_adlari import normallestir
from .degerlendirme import kume_bootstrap

DOSYALAR = ("2025-26/en.1-full.json", "2025-26/de.1-full.json", "2025-26/at.1-full.json")
AYRIM = "2026-01-01"
K = 5.0


def veri() -> tuple[list[dict], dict]:
    out, say = [], {"mac": 0, "kart_kaydi_yok": 0}
    for d in DOSYALAR:
        for m in O._maclar(json.loads((O.KOK / d).read_bytes())):
            say["mac"] += 1
            b = m.get("bookings")
            if not b or len(b) != 2:
                say["kart_kaydi_yok"] += 1
                continue
            hakem = normallestir((m.get("referees") or [{}])[0].get("name") or "") or None
            out.append({"lig": d.split("/")[1][:4], "tarih": m["date"], "ev": normallestir(m["team1"]),
                        "dep": normallestir(m["team2"]), "kart_ev": len(b[0]), "kart_dep": len(b[1]), "hakem": hakem})
    return sorted(out, key=lambda m: m["tarih"]), say


def _pois_ll(k, lam):
    return k * math.log(lam) - lam - math.lgamma(k + 1)


def _p_en_az(n, lam):
    return 1 - sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(n))


def calistir() -> dict:
    ms, say = veri()
    kay = []
    for lig in sorted({m["lig"] for m in ms}):
        lm = [m for m in ms if m["lig"] == lig]
        for i, m in enumerate(lm):
            if m["tarih"] < AYRIM:
                continue
            g = [x for x in lm[:i] if x["tarih"] < m["tarih"]]
            if len(g) < 50:
                continue
            mu = np.mean([x["kart_ev"] + x["kart_dep"] for x in g])
            mu_takim = mu / 2
            t = defaultdict(lambda: [0.0, 0])
            h = defaultdict(lambda: [0.0, 0])
            for x in g:
                t[x["ev"]][0] += x["kart_ev"]; t[x["ev"]][1] += 1
                t[x["dep"]][0] += x["kart_dep"]; t[x["dep"]][1] += 1
                if x["hakem"]:
                    h[x["hakem"]][0] += x["kart_ev"] + x["kart_dep"]; h[x["hakem"]][1] += 1
            def tk(a):
                s, n = t[a]
                return (s + K * mu_takim) / (n + K)
            l1 = tk(m["ev"]) + tk(m["dep"])
            hs, hn = h[m["hakem"]] if m["hakem"] else (0.0, 0)
            carpan = ((hs / hn / mu) * hn + K * 1.0) / (hn + K) if hn else 1.0
            y = m["kart_ev"] + m["kart_dep"]
            kay.append({"tarih": m["tarih"], "lig": lig, "y": y, "H0": mu, "H1": l1, "H2": l1 * carpan,
                        "hakem_gecmis_mac": hn})
    r = {"veri": say, "test_mac": len(kay), "ligler": sorted({k["lig"] for k in kay})}
    kume = [k["tarih"] for k in kay]
    ll = {md: np.array([_pois_ll(k["y"], k[md]) for k in kay]) for md in ("H0", "H1", "H2")}
    br = {md: np.array([(_p_en_az(5, k[md]) - (k["y"] >= 5)) ** 2 for k in kay]) for md in ("H0", "H1", "H2")}
    r["poisson_ll_ortalama"] = {md: round(float(v.mean()), 4) for md, v in ll.items()}
    r["brier_5_ve_uzeri"] = {md: round(float(v.mean()), 4) for md, v in br.items()}
    r["olay_orani_5_ve_uzeri"] = round(float(np.mean([k["y"] >= 5 for k in kay])), 4)
    r["ortalama_kart"] = {"gozlenen": round(float(np.mean([k["y"] for k in kay])), 3),
                          **{md: round(float(np.mean([k[md] for k in kay])), 3) for md in ("H0", "H1", "H2")}}
    r["varyans_gozlenen"] = round(float(np.var([k["y"] for k in kay])), 3)
    r["farklar_ll"] = {"H1-H0": kume_bootstrap(ll["H1"] - ll["H0"], kume), "H2-H1": kume_bootstrap(ll["H2"] - ll["H1"], kume)}
    r["farklar_brier"] = {"H1-H0": kume_bootstrap(br["H1"] - br["H0"], kume), "H2-H1": kume_bootstrap(br["H2"] - br["H1"], kume)}
    return r


if __name__ == "__main__":
    import sys
    r = calistir()
    cik = Path(__file__).resolve().parents[3] / "output" / "model" / "h_asamasi"
    cik.mkdir(parents=True, exist_ok=True)
    (cik / "sonuc.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1, default=float))
