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


def rho_sinirlari(lh: np.ndarray, la: np.ndarray) -> tuple[float, float]:
    """τ > 0 için geçerli ρ aralığı (DÜZELTİLDİ; WIP sürümünde 1/λ değerleri yanlışlıkla üst sınıra eklenmişti):
    τ(0,0)=1−λhλaρ>0 → ρ<1/(λhλa); τ(0,1)=1+λhρ>0 → ρ>−1/λh; τ(1,0)=1+λaρ>0 → ρ>−1/λa; τ(1,1)=1−ρ>0 → ρ<1."""
    lh, la = np.asarray(lh, float), np.asarray(la, float)
    ust = min(1.0, float(np.min(1.0 / np.maximum(lh * la, 1e-12))))
    alt = max(-float(np.min(1.0 / np.maximum(lh, 1e-12))), -float(np.min(1.0 / np.maximum(la, 1e-12))))
    return alt, ust


def rho_kestir(gx, gy, lh, la, w, arama: float = 0.35) -> float:
    """λ'lar sabitken ağırlıklı DC log-olabilirliğini ρ'ya göre en büyükleyen değer (yalnızca τ ≠ 1 olan skorlar)."""
    gx, gy, lh, la, w = (np.asarray(v) for v in (gx, gy, lh, la, w))
    d = (gx <= 1) & (gy <= 1)
    if not d.any():
        return 0.0
    x, yv, l1, l2, ww = gx[d], gy[d], lh[d].astype(float), la[d].astype(float), w[d].astype(float)
    alt, ust = rho_sinirlari(lh, la)
    a, b = max(alt, -arama) + 1e-6, min(ust, arama) - 1e-6
    if a >= b:
        return 0.0

    def nll(r):
        t = np.where((x == 0) & (yv == 0), 1 - l1 * l2 * r,
            np.where((x == 0) & (yv == 1), 1 + l1 * r,
            np.where((x == 1) & (yv == 0), 1 + l2 * r, 1 - r)))
        return -float(np.sum(ww * np.log(np.clip(t, 1e-12, None))))
    return altin_oran(nll, a, b)


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
            "skor_0_0": float(m[0, 0]), "skor_1_0": float(m[1, 0]), "skor_0_1": float(m[0, 1]), "skor_1_1": float(m[1, 1]),
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
            hi = np.fromiter((ix[m["ev"]] for m in veri), int, k)
            di = np.fromiter((ix[m["dep"]] for m in veri), int, k)
            gun = np.fromiter((bugun - _gun(m["tarih"]) for m in veri), float, k)
            r_ = np.arange(k)
            X = np.zeros((2 * k, p))
            X[2 * r_, 0] = 1.0
            X[2 * r_, 1] = 1.0
            X[2 * r_, 2 + hi] = 1.0
            X[2 * r_, 2 + n + di] = 1.0
            X[2 * r_ + 1, 0] = 1.0
            X[2 * r_ + 1, 2 + di] = 1.0
            X[2 * r_ + 1, 2 + n + hi] = 1.0
            y = np.empty(2 * k)
            y[0::2] = np.fromiter((m["ev_gol"] for m in veri), float, k)
            y[1::2] = np.fromiter((m["dep_gol"] for m in veri), float, k)
            w = np.repeat(np.exp(-self.xi * gun), 2)
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
                self.rho = rho_kestir(gx, gy, lh, la, ww)
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


class PoissonGorunumu:
    """Aynı kestirimin bağımsız Poisson hâli (ρ = 0). Kendi kestirimi yoktur; listede kaynak modelden SONRA gelmelidir."""
    ad = "poisson"

    def __init__(self, kaynak: GolModeli):
        self.kaynak = kaynak
        self.kesim = None

    def hazirla(self, gecmis, tarih, takimlar):
        self.kesim = self.kaynak.kesim
        return self

    def tahmin(self, mac: dict) -> dict:
        lh, la = self.kaynak.oranlar(mac["ev"], mac["dep"])
        return pazarlar(skor_matrisi(lh, la, 0.0, self.kaynak.maks_gol))
