"""Günlük kapsam kaydı: hangi model, hangi markette, hangi liglerde olasılık verebilir (değerlendirme çıktılarından).

Kural (madde 8): bir market ancak
  (a) taban üstü: model − taban log loss, LİG-SEZON kümeli bootstrap GA üst sınırı < 0,
  (b) kalibre: havuz ECE ≤ 0,02, n ≥ 30 kutularda |tahmin − gerçekleşen| ≤ 0,05, her değerlendirme liginde ECE ≤ 0,04,
  (c) olay sıklığı %2–98
koşullarını sağlıyorsa kapsamdadır. Lig koşulu: model yalnızca değerlendirildiği liglerde kullanılır.
Kayıt dosyası: veri/model_kapsami.json (kaynak çıktıların SHA-256'sıyla).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
KAYIT = KOK / "veri" / "model_kapsami.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def e_poisson_kapsami(e_v1: Path, denetim: Path) -> dict:
    """E (Poisson) için: E1 lig-sezon kümeli GA (denetim) + kalibrasyon (v1 kutuları + denetim lig ECE)."""
    v1 = json.loads(Path(e_v1).read_text())["birlesik"]
    dn = json.loads(Path(denetim).read_text())["E"]["poisson"]
    out = {}
    for a, r in dn.items():
        kutu = v1[a]["poisson"]["buyuk_sapmali_kutu"]
        neden = []
        if not 0.02 <= r["olay_orani"] <= 0.98:
            neden.append("olay sıklığı %2–98 dışında")
        if not r["E1_lig_sezon"]:
            neden.append(f"tabanı geçmiyor (lig-sezon GA {r['GA_lig_sezon'][:2]})")
        if r["ece_havuz"] > 0.02:
            neden.append(f"havuz ECE {r['ece_havuz']:.3f} > 0,02")
        if kutu:
            neden.append(f"{len(kutu)} kutuda sapma > 0,05")
        kotu = {lg: e for lg, e in r["lig_ece"].items() if e > 0.04}
        if kotu:
            neden.append(f"lig ECE > 0,04: {kotu}")
        out[a] = {"kapsamda": not neden, "nedenler": neden}
    return out


def kayit_uret(e_v1: Path, denetim: Path, e2_sinama: Path | None = None, hedef: Path = KAYIT,
               e3_sinama: Path | None = None) -> dict:
    e = e_poisson_kapsami(e_v1, denetim)
    modeller = {"poisson_E": {"tanim": "GolModeli ξ=0,003, pencere 1095, ceza 2,0, önsel 0,8/1,2; Poisson",
                              "spec": {"ceza": 2.0},
                              "degerlendirme_ligleri": ["fr.1", "nl.1", "pt.1", "de.2", "es.2"],
                              "marketler": e}}
    kaynaklar = {"e_v1": {"yol": str(Path(e_v1).resolve().relative_to(KOK)), "sha256": _sha(e_v1)},
                 "denetim": {"yol": str(Path(denetim).resolve().relative_to(KOK)), "sha256": _sha(denetim)}}
    if e2_sinama:
        s = json.loads(Path(e2_sinama).read_text())
        modeller["E2_aday"] = {"tanim": f"E2 seçilen aday {s['secim']['model']} {s['secim']['spec']} (ON_KAYIT_E2)",
                               "spec": s["secim"]["spec"],
                               "degerlendirme_ligleri": sorted(s["lig_mac"]),
                               "marketler": {a: {"kapsamda": bool(r.get("gunluk_kapsam")),
                                                 "nedenler": [] if r.get("gunluk_kapsam") else
                                                 [k for k in ("bilgi_tasiyor", "kalibre") if not r.get(k)] or
                                                 [r.get("karar", "")]} for a, r in s["marketler"].items()}}
        kaynaklar["e2_sinama"] = {"yol": str(Path(e2_sinama).resolve().relative_to(KOK)), "sha256": _sha(e2_sinama)}
    if e3_sinama:
        s = json.loads(Path(e3_sinama).read_text())
        asil = s["asil"]
        modeller["E3"] = {"tanim": f"E3 {s['secilen']['ad']}: E2 (ceza 16, w 0,65, b 0) + zaman sıralı güç farkı ölçeği "
                                   "γ ve ev kayması δ (aynı ligin önceki 730 günü; ON_KAYIT_E3)",
                          "spec": {"ceza": 16.0, "w": 0.65, "b": 0.0, "A": bool(s["secilen"]["A"]),
                                   "K": s["secilen"]["K"], "s": s["secilen"]["s"]},
                          "degerlendirme_ligleri": sorted(asil["lig_mac"]),
                          "marketler": {a: {"kapsamda": bool(r.get("gunluk_kapsam")),
                                            "nedenler": [] if r.get("gunluk_kapsam") else
                                            [k for k in ("bilgi_tasiyor", "kalibre") if not r.get(k)] or
                                            [r.get("karar", "")]} for a, r in asil["marketler"].items()}}
        kaynaklar["e3_sinama"] = {"yol": str(Path(e3_sinama).resolve().relative_to(KOK)), "sha256": _sha(e3_sinama)}
    kayit = {"aciklama": "Günlük olasılık kapsamı. Kapsam dışı market = hesaplanamaz. Bu dosya değerlendirme "
                         "çıktılarından üretilir; elle düzenlenmez.",
             "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kaynaklar": kaynaklar,
             "devre_marketleri": "hesaplanamaz (F-v2 ve F2: 62 seçenekten yalnızca 3'ü kuralları geçti — İY/MS X/2, 587 "
                                 "'2.', 779 '0:1' — çoklu karşılaştırma riski nedeniyle ikinci ileriye dönük doğrulamaya "
                                 "kadar kapsam dışı; iş akışında devre modeli yok)",
             "korner_kart_oyuncu": "hesaplanamaz (G/I veri yok; H lig ortalamasını geçmiyor)",
             "ligler_arasi": "hesaplanamaz (D: M1 > B1 sezon kümeli GA 0'ı içeriyor; büyük-5 farkı eksik)",
             "modeller": modeller}
    Path(hedef).write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    return kayit


def kapsam_oku(yol: Path = KAYIT) -> tuple[dict, str]:
    return json.loads(Path(yol).read_text(encoding="utf-8")), _sha(yol)
