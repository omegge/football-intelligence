"""Olasılık tahmini ölçütleri (yalnızca numpy). Sonuç kodları: H (ev), D (beraberlik), A (deplasman)."""

from __future__ import annotations

import numpy as np

SONUCLAR = ("H", "D", "A")


def _matris(olasiliklar: list[dict]) -> np.ndarray:
    return np.array([[p[k] for k in SONUCLAR] for p in olasiliklar], float)


def _birsicak(sonuclar: list[str]) -> np.ndarray:
    o = np.zeros((len(sonuclar), 3))
    o[np.arange(len(sonuclar)), [SONUCLAR.index(s) for s in sonuclar]] = 1
    return o


def log_loss(olasiliklar, sonuclar) -> float:
    P, O = _matris(olasiliklar), _birsicak(sonuclar)
    return float(-np.mean(np.log(np.clip((P * O).sum(1), 1e-15, None))))


def brier(olasiliklar, sonuclar) -> float:
    """Çok sınıflı Brier: Σ_k (p_k − o_k)², maç başına ortalama (0 mükemmel, 2 en kötü)."""
    P, O = _matris(olasiliklar), _birsicak(sonuclar)
    return float(np.mean(((P - O) ** 2).sum(1)))


def rps(olasiliklar, sonuclar) -> float:
    """Sıralı olasılık skoru (H < D < A sırası)."""
    P, O = _matris(olasiliklar), _birsicak(sonuclar)
    cp, co = np.cumsum(P, 1)[:, :2], np.cumsum(O, 1)[:, :2]
    return float(np.mean(((cp - co) ** 2).sum(1) / 2))


def maclik_log_loss(olasiliklar, sonuclar) -> np.ndarray:
    P, O = _matris(olasiliklar), _birsicak(sonuclar)
    return -np.log(np.clip((P * O).sum(1), 1e-15, None))


def ikili(p, y) -> dict:
    p, y = np.clip(np.asarray(p, float), 1e-15, 1 - 1e-15), np.asarray(y, float)
    return {"log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "brier": float(np.mean((p - y) ** 2)), "ort_tahmin": float(p.mean()), "gerceklesen": float(y.mean()),
            "n": int(len(p))}


def kalibrasyon(p, y, kutu: int = 10) -> dict:
    """Eşit genişlikli kutular. ECE = Σ (n_k/N)·|ort_tahmin_k − gerçekleşen_k|."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    kenar = np.linspace(0, 1, kutu + 1)
    satir, ece = [], 0.0
    for i in range(kutu):
        m = (p >= kenar[i]) & ((p < kenar[i + 1]) if i < kutu - 1 else (p <= kenar[i + 1]))
        if m.sum() == 0:
            continue
        ot, gr = float(p[m].mean()), float(y[m].mean())
        ece += m.sum() / len(p) * abs(ot - gr)
        satir.append({"aralik": f"{kenar[i]:.1f}-{kenar[i + 1]:.1f}", "n": int(m.sum()), "ort_tahmin": round(ot, 4),
                      "gerceklesen": round(gr, 4)})
    return {"ece": round(float(ece), 4), "kutular": satir}


def sonuc_kalibrasyonu(olasiliklar, sonuclar, kutu: int = 10) -> dict:
    P, O = _matris(olasiliklar), _birsicak(sonuclar)
    return {k: kalibrasyon(P[:, i], O[:, i], kutu) for i, k in enumerate(SONUCLAR)}


def bootstrap_ortalama_fark(a, b, n: int = 2000, tohum: int = 7) -> dict:
    """Eşleştirilmiş fark (a − b) ortalaması ve %95 güven aralığı (maç bazında yeniden örnekleme)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    rng = np.random.default_rng(tohum)
    ornek = rng.integers(0, len(d), (n, len(d)))
    ort = d[ornek].mean(1)
    return {"fark": float(d.mean()), "alt95": float(np.percentile(ort, 2.5)), "ust95": float(np.percentile(ort, 97.5)),
            "n": int(len(d))}


def auc(skor, etiket) -> float | None:
    """Mann–Whitney AUC (eşitlikler yarım sayılır)."""
    s, e = np.asarray(skor, float), np.asarray(etiket, bool)
    poz, neg = s[e], s[~e]
    if len(poz) == 0 or len(neg) == 0:
        return None
    sira = np.argsort(np.concatenate([poz, neg]), kind="mergesort")
    deger = np.concatenate([poz, neg])[sira]
    r = np.empty(len(deger))
    i = 0
    while i < len(deger):
        j = i
        while j + 1 < len(deger) and deger[j + 1] == deger[i]:
            j += 1
        r[i:j + 1] = (i + j) / 2 + 1
        i = j + 1
    rank = np.empty(len(deger))
    rank[sira] = r
    return float((rank[:len(poz)].sum() - len(poz) * (len(poz) + 1) / 2) / (len(poz) * len(neg)))
