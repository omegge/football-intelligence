"""D/E/F değerlendirme yöntemlerinin denetimi (önceki çıktılar DEĞİŞTİRİLMEZ; bu modül ayrı sürüm üretir).

Denetlenenler:
- Tekrarlanabilirlik: aynı ön kayıtlı kodla yeniden çalıştırınca aynı ölçümler mi (fark yalnızca bilinen düzeltmeler)?
- Güven aralığı yöntemi: v1 tarih kümeli bootstrap. Aynı takımın aynı sezondaki maçları bağımlıdır; bu yüzden
  ISO hafta kümesi ve lig-sezon kümesi (en tutucu; takım-sezon bağımlılığını içine alır) ile yeniden hesaplanır.
- Lig bazında kalibrasyon (ECE) ve lig-sezon bazında işaret tutarlılığı (model tabandan iyi olan lig-sezon oranı).
Kullanım: PYTHONPATH=lib python3 -m fi.model.denetim
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from .degerlendirme import kume_bootstrap
from .metrikler import kalibrasyon

CIKTI = Path(__file__).resolve().parents[3] / "output" / "model"


def _ll(p, y):
    p = np.clip(np.asarray(p, float), 1e-15, 1 - 1e-15)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def _sezon(tarih: str) -> str:
    d = date.fromisoformat(tarih)
    y = d.year if d.month >= 7 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def market_denetimi(satirlar: list[dict], marketler: list[str], model_al, taban_al, y_al) -> dict:
    kume = {"tarih": [s["tarih"] for s in satirlar],
            "hafta": ["%d-W%02d" % date.fromisoformat(s["tarih"]).isocalendar()[:2] for s in satirlar],
            "lig_sezon": [f"{s['lig']}|{_sezon(s['tarih'])}" for s in satirlar]}
    out = {}
    for ad in marketler:
        y = np.array([y_al(s, ad) for s in satirlar], float)
        pm = np.array([model_al(s, ad) for s in satirlar])
        pt = np.array([taban_al(s, ad) for s in satirlar])
        d = _ll(pm, y) - _ll(pt, y)
        r = {"olay_orani": round(float(y.mean()), 4), "fark": round(float(d.mean()), 5)}
        for k, ids in kume.items():
            b = kume_bootstrap(d, ids)
            r[f"GA_{k}"] = [round(b["alt95"], 5), round(b["ust95"], 5), b["n_kume"]]
            r[f"E1_{k}"] = bool(b["ust95"] < 0)
        ligler = sorted({s["lig"] for s in satirlar})
        r["lig_ece"] = {}
        for lg in ligler:
            m = np.array([s["lig"] == lg for s in satirlar])
            r["lig_ece"][lg] = kalibrasyon(pm[m], y[m], 10)["ece"]
        ls = sorted(set(kume["lig_sezon"]))
        iyi = [float(d[np.array([x == k for x in kume["lig_sezon"]])].mean()) < 0 for k in ls]
        r["lig_sezon_model_iyi_orani"] = [sum(iyi), len(ls)]
        r["ece_havuz"] = kalibrasyon(pm, y, 10)["ece"]
        out[ad] = r
    return out


def e_denetimi() -> dict:
    from . import e_asamasi as E
    from .pazar_modelleri import OLAYLAR
    tum = []
    for lig in E.LIGLER:
        r = E.lig_kayitlari(lig)
        for s in r["satirlar"]:
            s["lig"] = lig
        tum.extend(r["satirlar"])
    m = list(OLAYLAR)
    return {"mac": len(tum), "poisson": market_denetimi(tum, m, lambda s, a: s["poisson"][a], lambda s, a: s["taban"][a],
                                                        lambda s, a: s["y"][a])}


def f_denetimi() -> dict:
    from . import f_asamasi as F
    tum = []
    for lig in F.LIGLER:
        r = F.lig_kayitlari(lig)
        for s in r["satirlar"]:
            s["lig"] = lig
        tum.extend(r["satirlar"])
    m = list(F.OLAYLAR)
    return {"mac": len(tum), "F0": market_denetimi(tum, m, lambda s, a: s["model"][a], lambda s, a: s["taban"][a],
                                                   lambda s, a: float(F.OLAYLAR[a][1][s["nokta"]]))}


def main() -> int:
    sonuc = {"tur": "yontem_denetimi", "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "not": "E v1.1: gozlenen() kırpmasız (v1'de 0-13 maçında tek/çift yanlış). F: v2 + ızgara dışı devre skoru "
                    "kırpılmaz, değerlendirme dışı.", "E": e_denetimi(), "F": f_denetimi()}
    cik = CIKTI / f"denetim_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    cik.mkdir(parents=True, exist_ok=True)
    (cik / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(cik / "sonuc.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
