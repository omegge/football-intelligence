"""Özgün Elo benzeri takım gücü modeli (ClubElo'yu taklit etmez; yalnızca sonuçlardan hesaplanır).

- Maç sonrası güncelleme: Δ = K · G(gol farkı) · (S − E), E = 1 / (1 + 10^(−(r_ev + H − r_dep)/400)); toplam sıfır.
- Gol farkı çarpanı G: fark ≤ 1 → 1, 2 → 1.5, ≥ 3 → (11 + fark)/8.
- Sezon başında puanlar lig ortalamasına doğru λ oranında çekilir.
- Lige yeni gelen takım: önceki sezon ligden ayrılan (düşen) takımların ortalama puanı; yoksa başlangıç puanı.
- 1X2 olasılığı: sıralı lojistik P(D≤ k) = σ(θ_k − β·x), x = (r_ev + H − r_dep)/400.
  θ ve β her sezon başında YALNIZCA geçmiş sezonların (maç öncesi) Elo farkları ve sonuçlarıyla yeniden kestirilir.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .optim import nelder_mead


@dataclass
class EloAyar:
    k: float = 20.0
    ev_avantaji: float = 60.0
    sezon_cekimi: float = 0.2
    baslangic: float = 1500.0


def gol_carpani(fark: int) -> float:
    f = abs(fark)
    return 1.0 if f <= 1 else (1.5 if f == 2 else (11 + f) / 8)


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    e = math.exp(z)
    return e / (1 + e)


@dataclass
class SiraliLojistik:
    theta1: float = -0.75       # P(deplasman) = σ(θ1 − βx)
    theta2: float = 0.35        # P(deplasman veya beraberlik) = σ(θ2 − βx)
    beta: float = 2.5
    ornek: int = 0

    def olasilik(self, x: float) -> dict:
        p_a = _sigmoid(self.theta1 - self.beta * x)
        p_ad = _sigmoid(self.theta2 - self.beta * x)
        return {"H": 1 - p_ad, "D": p_ad - p_a, "A": p_a}

    def kestir(self, veri: list[tuple[float, str]]):
        if len(veri) < 200:
            return self
        def nll(p):
            t1, gap, b = p
            t2 = t1 + abs(gap)
            s = 0.0
            for x, y in veri:
                pa = _sigmoid(t1 - b * x)
                pad = _sigmoid(t2 - b * x)
                pr = {"A": pa, "D": pad - pa, "H": 1 - pad}[y]
                s -= math.log(max(pr, 1e-12))
            return s
        (t1, gap, b), _ = nelder_mead(nll, [self.theta1, self.theta2 - self.theta1, self.beta], adim=0.3)
        self.theta1, self.theta2, self.beta, self.ornek = t1, t1 + abs(gap), b, len(veri)
        return self


@dataclass
class EloModeli:
    ayar: EloAyar = field(default_factory=EloAyar)
    puan: dict = field(default_factory=dict)
    sezon: str | None = None
    onceki_takimlar: set = field(default_factory=set)
    gecmis: list = field(default_factory=list)          # (x, sonuç, sezon) — yalnızca oynanmış maçlar
    donusum: SiraliLojistik = field(default_factory=SiraliLojistik)
    ad = "elo"

    def sezon_basla(self, sezon: str, takimlar: set):
        """Sezonun takım listesi fikstür yayımlandığında bilinir (maç öncesi bilgi)."""
        if self.puan:
            ort = sum(self.puan[t] for t in self.onceki_takimlar) / len(self.onceki_takimlar)
            for t in self.onceki_takimlar:
                self.puan[t] = ort + (1 - self.ayar.sezon_cekimi) * (self.puan[t] - ort)
            ayrilanlar = self.onceki_takimlar - takimlar
            yeni_puan = (sum(self.puan[t] for t in ayrilanlar) / len(ayrilanlar)) if ayrilanlar else self.ayar.baslangic
        else:
            yeni_puan = self.ayar.baslangic
        for t in takimlar:
            if t not in self.onceki_takimlar:
                self.puan[t] = yeni_puan
        self.onceki_takimlar = set(takimlar)
        self.sezon = sezon
        self.donusum.kestir([(x, y) for x, y, s in self.gecmis if s != sezon])

    def fark(self, ev: str, dep: str) -> float:
        return (self.puan[ev] + self.ayar.ev_avantaji - self.puan[dep]) / 400.0

    def tahmin(self, mac: dict) -> dict:
        return self.donusum.olasilik(self.fark(mac["ev"], mac["dep"]))

    def sonuc_isle(self, mac: dict):
        x = self.fark(mac["ev"], mac["dep"])
        e = 1 / (1 + 10 ** (-x))
        g = mac["ev_gol"] - mac["dep_gol"]
        s = 1.0 if g > 0 else (0.5 if g == 0 else 0.0)
        d = self.ayar.k * gol_carpani(g) * (s - e)
        self.puan[mac["ev"]] += d
        self.puan[mac["dep"]] -= d
        self.gecmis.append((x, "H" if g > 0 else ("D" if g == 0 else "A"), self.sezon))
