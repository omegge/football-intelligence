"""Gol modelleri: zaman ağırlıklı Poisson (Maher tipi) ve Dixon–Coles.

log λ_ev  = μ + ev + hücum[ev]  + savunma[dep]
log λ_dep = μ      + hücum[dep] + savunma[ev]
Kestirim: ağırlıklı, cezalandırılmış Poisson log-olabilirliği (IRLS / Newton). Ağırlık w = exp(−ξ · gün_önce),
yalnızca son `pencere_gun` gün. Ceza (ridge) takım parametrelerini önsel değere çeker:
  - ligde verisi olan takım: 0
  - pencerede hiç verisi olmayan (yeni gelen) takım: hücum = ln(yeni_hucum), savunma = ln(yeni_savunma)
    (DOĞRULANMAMIŞ VARSAYIM; raporda ayrıca belirtilir).
Dixon–Coles: düşük skorlar için τ düzeltmesi; ρ, λ'lar sabitken altın oran aramasıyla kestirilir (iki aşamalı yaklaşım).
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np

from .optim import altin_oran


def _gun(t: str) -> int:
    return date.fromisoformat(t[:10]).toordinal()


def tau(x: int, y: int, lh: float, la: float, rho: float) -> float:
    if x == 0 and y == 0:
        return 1 - lh * la * rho
    if x == 0 and y == 1:
        return 1 + lh * rho
    if x == 1 and y == 0:
        return 1 + la * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


def skor_matrisi(lh: float, la: float, rho: float = 0.0, maks: int = 10) -> np.ndarray:
    g = np.arange(maks + 1)
    fakt = np.array([math.factorial(int(k)) for k in g], dtype=float)
    ph = np.exp(-lh) * lh ** g / fakt
    pa = np.exp(-la) * la ** g / fakt
    m = np.outer(ph, pa)
    for x in (0, 1):
        for y in (0, 1):
            m[x, y] *= tau(x, y, lh, la, rho)
    m = np.clip(m, 0, None)
    return m / m.sum()


def pazarlar(m: np.ndarray) -> dict:
    n = m.shape[0]
    i, j = np.indices(m.shape)
    return {"H": float(m[i > j].sum()), "D": float(np.trace(m)), "A": float(m[i < j].sum()),
            "ust25": float(m[(i + j) >= 3].sum()), "alt25": float(m[(i + j) <= 2].sum()),
            "kg_var": float(m[1:, 1:].sum()), "kg_yok": float(1 - m[1:, 1:].sum()),
            "beklenen_ev": float((m.sum(axis=1) * np.arange(n)).sum()),
            "beklenen_dep": float((m.sum(axis=0) * np.arange(n)).sum())}


class GolModeli:
    def __init__(self, xi: float = 0.002, pencere_gun: int = 1095, ceza: float = 2.0,
                 yeni_hucum: float = 0.8, yeni_savunma: float = 1.2, dixon_coles: bool = True, maks_gol: int = 10):
        self.xi, self.pencere_gun, self.ceza = xi, pencere_gun, ceza
        self.yeni_hucum, self.yeni_savunma = yeni_hucum, yeni_savunma
        self.dixon_coles, self.maks_gol = dixon_coles, maks_gol
        self.ad = "dixon_coles" if dixon_coles else "poisson"
        self.param = None
        self.rho = 0.0
        self.kesim = None
        self._beta = None

    def hazirla(self, gecmis: list[dict], tarih: str, takimlar: set):
        """`gecmis` yalnızca `tarih`'ten ÖNCEKİ maçları içermelidir (backtest motoru garanti eder ve denetler)."""
        bugun = _gun(tarih)
        veri = [m for m in gecmis if 0 < bugun - _gun(m["tarih"]) <= self.pencere_gun]
        self.kesim = max((m["tarih"] for m in veri), default=None)
        if self.kesim is not None and self.kesim >= tarih:
            raise AssertionError(f"sızıntı: eğitim verisi {self.kesim}, tahmin tarihi {tarih}")
        verili = {m["ev"] for m in veri} | {m["dep"] for m in veri}
        takim = sorted(verili | set(takimlar))
        ix = {t: i for i, t in enumerate(takim)}
        n = len(takim)
        p = 2 + 2 * n                         # μ, ev, hücum[n], savunma[n]
        onsel = np.zeros(p)
        for t in takim:
            if t not in verili:
                onsel[2 + ix[t]] = math.log(self.yeni_hucum)
                onsel[2 + n + ix[t]] = math.log(self.yeni_savunma)
        ceza = np.full(p, self.ceza)
        ceza[:2] = 0.0
        if not veri:
            beta = onsel.copy()
            beta[0] = math.log(1.35)
        else:
            k = len(veri)
            X = np.zeros((2 * k, p))
            y = np.empty(2 * k)
            w = np.empty(2 * k)
            for r, m in enumerate(veri):
                a = math.exp(-self.xi * (bugun - _gun(m["tarih"])))
                h, d = ix[m["ev"]], ix[m["dep"]]
                X[2 * r, [0, 1, 2 + h, 2 + n + d]] = 1.0
                X[2 * r + 1, [0, 2 + d, 2 + n + h]] = 1.0
                y[2 * r], y[2 * r + 1] = m["ev_gol"], m["dep_gol"]
                w[2 * r] = w[2 * r + 1] = a
            beta = onsel.copy()
            beta[0] = math.log(max(y.mean(), 0.1))
            P = np.diag(ceza)
            for _ in range(25):
                eta = X @ beta
                lam = np.exp(eta)
                W = w * lam
                z = eta + (y - lam) / lam
                A = X.T @ (W[:, None] * X) + P
                b = X.T @ (W * z) + ceza * onsel
                yeni = np.linalg.solve(A, b)
                if np.max(np.abs(yeni - beta)) < 1e-7:
                    beta = yeni
                    break
                beta = yeni
            if self.dixon_coles:
                lh = np.exp(X[0::2] @ beta)
                la = np.exp(X[1::2] @ beta)
                gx, gy, ww = y[0::2].astype(int), y[1::2].astype(int), w[0::2]
                dusuk = (gx <= 1) & (gy <= 1)
                ust = min(1.0, float(np.min(1 / np.maximum(lh * la, 1e-9))), float(np.min(1 / np.maximum(lh, 1e-9))),
                          float(np.min(1 / np.maximum(la, 1e-9))))
                alt = max(-1.0, -float(np.min(1 / np.maximum(lh, 1e-9))), -float(np.min(1 / np.maximum(la, 1e-9))))
                def nll(r):
                    t = [tau(int(a_), int(b_), l1, l2, r) for a_, b_, l1, l2 in
                         zip(gx[dusuk], gy[dusuk], lh[dusuk], la[dusuk])]
                    return -float(np.sum(ww[dusuk] * np.log(np.clip(t, 1e-12, None))))
                self.rho = altin_oran(nll, max(alt, -0.3) + 1e-6, min(ust, 0.3) - 1e-6)
        self.param = {"ix": ix, "n": n, "beta": beta}
        return self

    def oranlar(self, ev: str, dep: str) -> tuple[float, float]:
        b, ix, n = self.param["beta"], self.param["ix"], self.param["n"]
        lh = math.exp(b[0] + b[1] + b[2 + ix[ev]] + b[2 + n + ix[dep]])
        la = math.exp(b[0] + b[2 + ix[dep]] + b[2 + n + ix[ev]])
        return lh, la

    def tahmin(self, mac: dict) -> dict:
        lh, la = self.oranlar(mac["ev"], mac["dep"])
        return pazarlar(skor_matrisi(lh, la, self.rho if self.dixon_coles else 0.0, self.maks_gol))
