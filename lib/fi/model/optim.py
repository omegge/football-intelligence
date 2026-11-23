"""Bağımlılıksız küçük optimizasyon yardımcıları (scipy kurulu değil, paket kurulmuyor)."""

from __future__ import annotations

import math


def nelder_mead(f, x0, adim=0.5, tol=1e-7, maks_iter=2000):
    n = len(x0)
    noktalar = [list(x0)] + [[x0[j] + (adim if j == i else 0.0) for j in range(n)] for i in range(n)]
    degerler = [f(p) for p in noktalar]
    for _ in range(maks_iter):
        sira = sorted(range(n + 1), key=lambda i: degerler[i])
        noktalar = [noktalar[i] for i in sira]
        degerler = [degerler[i] for i in sira]
        if abs(degerler[-1] - degerler[0]) < tol:
            break
        merkez = [sum(p[j] for p in noktalar[:-1]) / n for j in range(n)]
        kotu = noktalar[-1]
        yans = [merkez[j] + (merkez[j] - kotu[j]) for j in range(n)]
        fy = f(yans)
        if fy < degerler[0]:
            gen = [merkez[j] + 2 * (merkez[j] - kotu[j]) for j in range(n)]
            fg = f(gen)
            noktalar[-1], degerler[-1] = (gen, fg) if fg < fy else (yans, fy)
        elif fy < degerler[-2]:
            noktalar[-1], degerler[-1] = yans, fy
        else:
            dar = [merkez[j] + 0.5 * (kotu[j] - merkez[j]) for j in range(n)]
            fd = f(dar)
            if fd < degerler[-1]:
                noktalar[-1], degerler[-1] = dar, fd
            else:
                en_iyi = noktalar[0]
                noktalar = [en_iyi] + [[en_iyi[j] + 0.5 * (p[j] - en_iyi[j]) for j in range(n)] for p in noktalar[1:]]
                degerler = [degerler[0]] + [f(p) for p in noktalar[1:]]
    i = min(range(n + 1), key=lambda i: degerler[i])
    return noktalar[i], degerler[i]


def altin_oran(f, a, b, tol=1e-5):
    g = (math.sqrt(5) - 1) / 2
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    while b - a > tol:
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = f(d)
    return (a + b) / 2
