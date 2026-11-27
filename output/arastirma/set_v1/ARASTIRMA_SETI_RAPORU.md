# Araştırma seti v1 — 30 sürpriz + 30 karşılaştırma (24.11.2026)

> **Bu set bağımsız kör test DEĞİLDİR.** Bütün maçların sonuçları biliniyor ve seçim sonuca göre yapıldı (sürpriz =
> favori kazanamadı). Bulgular yalnızca hipotez üretir; doğrulama ancak dokunulmamış dönem/lig ya da ileriye dönük
> testle yapılır. SHA-256 yalnızca bu kaydın sonradan değişmediğini gösterir, körlük sağlamaz.
> Set dosyası: `arastirma_seti.json` · SHA-256 `954a74877439a392…`

## Yöntem
- **Veri ve model:**
  - Veri: OpenFootball (düzeltilmiş tarihler ve tamamlanmış skorlar; commit `e6744429`).
  - Dönem: 2022-23…2025-26.
  - Ligler: Premier League (PL), Bundesliga (BL), La Liga (LL), Serie A (SA).
  - Model: Elo K=15/H=70/λ=0,15; Poisson & Dixon–Coles ξ=0,003, 1095 gün, ceza 2,0 (değiştirilmedi). Her tahmin kronolojik olarak, yalnızca maç öncesi veriyle üretildi.
- **Favori (MK-1):** Dixon–Coles'un maç öncesi olasılığına göre P(favori kazanır) ≥ 0,5. Nesine oranı kullanılmadı.
- **Seçim:**
  - A — favori kaybetti: favori kaybetti, DC ≥ 0.55, lig başına önce 4, her favori takım en fazla 1, en yüksek olasılıktan.
  - B — favori kazanamadı (berabere): berabere, DC ≥ 0.6, aynı kurallar, A'daki takımlar ayrı sayılır.
  - Ek kural: lig kotası, ligde en az temsil edilen sezona öncelik, yaklaşık üçte bir deplasman favorisi. Bir favori takım 30 sürprizin içinde yalnızca bir kez yer alır.
- **Karşılaştırma grubu (K):** aynı lig + sezon + favori saha durumu, en yakın DC olasılığı, favori kazandı; ana sette olmayan favori takım tercih.
- **Özellikler** (hepsi maç tarihinden önceki lig maçlarından hesaplandı):
  - son 5 sonuç;
  - Elo'ya göre rakip gücü düzeltilmiş form (son 5 ve son 10 maçta sonuç − beklenti toplamı);
  - son 10 rakibin ortalama Elo'su;
  - bu sezon aynı sahadaki maç başı puan;
  - ortak rakiplere karşı maç başı puan (bu sezon, maçtan önce; saha dengelenmemiş);
  - dinlenme süresi ve 14 günlük maç yoğunluğu.

## Dağılım
- **A (18):** lig {'en.1': 5, 'de.1': 5, 'es.1': 4, 'it.1': 4} · sezon {'2022-23': 6, '2023-24': 4, '2024-25': 4, '2025-26': 4} · favori sahası {'ev': 12, 'deplasman': 6} · DC favori kazanma aralığı [0.602, 0.858]
- **B (12):** lig {'en.1': 3, 'de.1': 3, 'es.1': 3, 'it.1': 3} · sezon {'2022-23': 4, '2023-24': 4, '2024-25': 3, '2025-26': 1} · favori sahası {'ev': 9, 'deplasman': 3} · DC favori kazanma aralığı [0.608, 0.813]
- **K (30):** lig {'en.1': 8, 'de.1': 8, 'es.1': 7, 'it.1': 7} · sezon {'2022-23': 10, '2023-24': 8, '2024-25': 7, '2025-26': 5} · favori sahası {'ev': 21, 'deplasman': 9} · DC favori kazanma aralığı [0.595, 0.87]
- **Takım çeşitliliği:** 30 sürprizde 30 farklı favori takım var. Karşılaştırma grubunda bazı büyük takımlar 2–3 kez tekrar ediyor, çünkü benzer olasılıkta kazanılmış maç havuzu bu takımlarda yoğun.
- **Havuz** (2022-26, DC favori maçları): {"en.1": {"favori_maci": 797, "aday_kaybetti(>=0.55)": 81, "aday_berabere(>=0.60)": 82}, "de.1": {"favori_maci": 633, "aday_kaybetti(>=0.55)": 62, "aday_berabere(>=0.60)": 71}, "es.1": {"favori_maci": 693, "aday_kaybetti(>=0.55)": 60, "aday_berabere(>=0.60)": 55}, "it.1": {"favori_maci": 763, "aday_kaybetti(>=0.55)": 73, "aday_berabere(>=0.60)": 69}}

## A — Favori kaybetti (18)
| Lig | Tarih | Maç | Favori (saha) | DC kaz/ber/kay | Poisson kaz | Elo kaz | Fav son 5 | Fav form5/10 | Rakip form5 | Fav bu saha (sezon) | Ortak rakip: fav–rakip p/m | Fav dinlenme (gün) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PL | 2022-11-12 | Manchester City FC **1-2** Brentford FC | Manchester City FC (ev) | 0.86 / 0.10 / 0.05 | 0.86 | 0.84 | GMGGG | 0.087 / 0.451 | 0.052 | 3.0 p/m (7) | 10: 2.6–1.1 p | 7 |
| BL | 2022-08-20 | Borussia Dortmund **2-3** SV Werder Bremen | Borussia Dortmund (ev) | 0.75 / 0.15 / 0.10 | 0.76 | 0.78 | MGGGG | 0.309 / -0.271 | -0.662 | 3.0 p/m (1) | 0 | 8 |
| LL | 2023-04-15 | Villarreal CF **1-2** Real Valladolid CF | Villarreal CF (ev) | 0.75 / 0.16 / 0.08 | 0.75 | 0.72 | GBGGG | 2.028 / -0.046 | -0.127 | 2.0 p/m (13) | 18: 1.63–1.07 p | 7 |
| SA | 2022-10-30 | SS Lazio **1-3** US Salernitana 1919 | SS Lazio (ev) | 0.76 / 0.16 / 0.08 | 0.76 | 0.76 | GGGBG | 1.408 / 1.627 | -0.055 | 2.17 p/m (6) | 6: 2.33–1.83 p | 7 |
| PL | 2023-12-09 | Sheffield United FC **1-0** Brentford FC | Brentford FC (dep) | 0.71 / 0.17 / 0.12 | 0.70 | 0.54 | GMMGM | -0.455 / -0.767 | -0.318 | 1.0 p/m (7) | 13: 1.0–0.15 p | 3 |
| BL | 2024-02-18 | VfL Bochum 1848 **3-2** FC Bayern München | FC Bayern München (dep) | 0.67 / 0.19 / 0.14 | 0.68 | 0.66 | MGGGM | -0.86 / -0.698 | 0.386 | 2.2 p/m (10) | 16: 2.35–1.1 p | 8 |
| LL | 2024-03-09 | Cádiz CF **2-0** Club Atlético de Madrid | Club Atlético de Madrid (dep) | 0.60 / 0.25 / 0.14 | 0.61 | 0.63 | BMGBG | -0.28 / 0.085 | -0.365 | 1.15 p/m (13) | 18: 2.0–0.73 p | 6 |
| SA | 2024-05-04 | US Sassuolo Calcio **1-0** FC Internazionale Milano | FC Internazionale Milano (dep) | 0.81 / 0.13 / 0.07 | 0.81 | 0.82 | GGBGG | 0.469 / 1.054 | -0.602 | 2.75 p/m (16) | 18: 2.7–0.7 p | 6 |
| PL | 2025-02-22 | Arsenal FC **0-1** West Ham United FC | Arsenal FC (ev) | 0.78 / 0.14 / 0.07 | 0.79 | 0.81 | GBGGG | 0.654 / 0.798 | -0.681 | 2.33 p/m (12) | 18: 2.08–1.12 p | 7 |
| BL | 2025-03-08 | Bayer 04 Leverkusen **0-2** SV Werder Bremen | Bayer 04 Leverkusen (ev) | 0.78 / 0.15 / 0.07 | 0.79 | 0.80 | GBBGG | 0.377 / 1.331 | -1.212 | 2.25 p/m (12) | 16: 2.26–1.26 p | 7 |
| LL | 2024-12-15 | FC Barcelona **0-1** CD Leganés | FC Barcelona (ev) | 0.85 / 0.10 / 0.05 | 0.85 | 0.86 | MBMGB | -1.681 / -1.284 | -0.097 | 2.5 p/m (6) | 15: 2.13–1.0 p | 8 |
| SA | 2024-09-24 | Atalanta BC **2-3** Como 1907 | Atalanta BC (ev) | 0.75 / 0.16 / 0.09 | 0.76 | 0.74 | MGMMG | -0.809 / 0.587 | None | 3.0 p/m (1) | 0 | 9 |
| PL | 2025-11-22 | Liverpool FC **0-3** Nottingham Forest FC | Liverpool FC (ev) | 0.67 / 0.18 / 0.15 | 0.67 | 0.72 | MMMGM | -2.161 / -1.629 | -0.867 | 2.4 p/m (5) | 8: 1.5–0.75 p | 13 |
| BL | 2026-02-28 | TSG 1899 Hoffenheim **0-1** FC St. Pauli 1910 | TSG 1899 Hoffenheim (ev) | 0.62 / 0.23 / 0.15 | 0.63 | 0.68 | GGMGB | 0.813 / 2.827 | 0.981 | 2.18 p/m (11) | 16: 1.95–0.91 p | 7 |
| LL | 2026-03-02 | Real Madrid CF **0-1** Getafe CF | Real Madrid CF (ev) | 0.74 / 0.18 / 0.08 | 0.74 | 0.83 | GGGGM | 0.262 / 0.127 | 0.828 | 2.75 p/m (12) | 18: 2.38–1.21 p | 9 |
| SA | 2025-08-23 | AC Milan **1-2** US Cremonese | AC Milan (ev) | 0.68 / 0.19 / 0.13 | 0.68 | 0.73 | GGGMG | 0.781 / 0.392 | 0.326 | — | 0 | sezon başı |
| PL | 2022-08-21 | Leeds United FC **3-0** Chelsea FC | Chelsea FC (dep) | 0.63 / 0.20 / 0.16 | 0.64 | 0.52 | GBGGB | 0.435 / -0.95 | 0.757 | 3.0 p/m (1) | 0 | 7 |
| BL | 2023-03-18 | VfL Bochum 1848 **1-0** RB Leipzig | RB Leipzig (dep) | 0.63 / 0.22 / 0.14 | 0.65 | 0.62 | MGGMG | -0.026 / 0.672 | -0.816 | 1.33 p/m (12) | 16: 1.83–0.96 p | 7 |

## B — Favori kazanamadı / berabere (12)
| Lig | Tarih | Maç | Favori (saha) | DC kaz/ber/kay | Poisson kaz | Elo kaz | Fav son 5 | Fav form5/10 | Rakip form5 | Fav bu saha (sezon) | Ortak rakip: fav–rakip p/m | Fav dinlenme (gün) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PL | 2022-10-18 | Brighton & Hove Albion FC **0-0** Nottingham Forest FC | Brighton & Hove Albion FC (ev) | 0.72 / 0.19 / 0.09 | 0.72 | 0.69 | MGBMM | -0.897 / 1.103 | -1.585 | 1.75 p/m (4) | 5: 1.4–0.6 p | 4 |
| BL | 2023-02-04 | Borussia Mönchengladbach **0-0** FC Schalke 04 | Borussia Mönchengladbach (ev) | 0.81 / 0.13 / 0.06 | 0.82 | 0.69 | MGMMG | -0.559 / -0.715 | 0.178 | 2.0 p/m (9) | 16: 1.41–0.53 p | 7 |
| LL | 2022-08-19 | Sevilla FC **1-1** Real Valladolid CF | Sevilla FC (ev) | 0.67 / 0.23 / 0.10 | 0.68 | 0.72 | BBBGM | -0.61 / -1.285 | -1.658 | — | 0 | 7 |
| SA | 2023-04-30 | SSC Napoli **1-1** US Salernitana 1919 | SSC Napoli (ev) | 0.81 / 0.13 / 0.06 | 0.81 | 0.85 | GMGBG | -0.208 / -0.234 | 1.139 | 2.33 p/m (15) | 18: 2.5–1.1 p | 7 |
| PL | 2024-03-30 | Sheffield United FC **3-3** Fulham FC | Fulham FC (dep) | 0.66 / 0.19 / 0.15 | 0.66 | 0.49 | MGGMG | 1.093 / 1.786 | 0.226 | 0.71 p/m (14) | 18: 1.25–0.52 p | 14 |
| BL | 2023-11-25 | SC Freiburg **1-1** SV Darmstadt 98 | SC Freiburg (ev) | 0.74 / 0.16 / 0.10 | 0.75 | 0.65 | MGMBM | -0.711 / -1.168 | -0.3 | 2.0 p/m (5) | 9: 1.22–0.78 p | 13 |
| LL | 2024-01-14 | UD Almería **0-0** Girona FC | Girona FC (dep) | 0.61 / 0.19 / 0.20 | 0.61 | 0.60 | GGGBG | 1.817 / 3.196 | -0.285 | 2.56 p/m (9) | 18: 2.5–0.28 p | 11 |
| SA | 2024-05-12 | Juventus FC **1-1** US Salernitana 1919 | Juventus FC (ev) | 0.75 / 0.18 / 0.07 | 0.76 | 0.85 | GBBBB | -0.029 / -1.371 | -1.024 | 2.12 p/m (17) | 18: 1.85–0.44 p | 7 |
| PL | 2025-05-11 | Nottingham Forest FC **2-2** Leicester City FC | Nottingham Forest FC (ev) | 0.68 / 0.20 / 0.12 | 0.68 | 0.76 | MMGMB | -1.012 / 0.119 | 0.201 | 1.82 p/m (17) | 18: 1.71–0.62 p | 6 |
| BL | 2026-02-22 | 1. FC Heidenheim 1846 **3-3** VfB Stuttgart | VfB Stuttgart (dep) | 0.63 / 0.21 / 0.16 | 0.64 | 0.63 | BGGMG | -0.075 / 1.027 | -1.049 | 1.45 p/m (11) | 16: 1.86–0.62 p | 8 |
| LL | 2025-03-30 | Athletic Club **0-0** CA Osasuna | Athletic Club (ev) | 0.65 / 0.21 / 0.14 | 0.65 | 0.66 | BGMBG | -0.238 / 0.593 | -1.087 | 2.07 p/m (14) | 18: 1.81–1.22 p | 14 |
| SA | 2024-08-25 | ACF Fiorentina **0-0** Venezia FC | ACF Fiorentina (ev) | 0.70 / 0.18 / 0.12 | 0.71 | 0.68 | GBGGB | 1.235 / 0.656 | 0.423 | — | 0 | 8 |

## K — Karşılaştırma (favori kazandı, 30)
| Lig | Tarih | Maç | Favori (saha) | DC kaz/ber/kay | Poisson kaz | Elo kaz | Fav son 5 | Fav form5/10 | Rakip form5 | Fav bu saha (sezon) | Ortak rakip: fav–rakip p/m | Fav dinlenme (gün) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PL | 2022-11-05 | Manchester City FC **2-1** Fulham FC | Manchester City FC (ev) | 0.87 / 0.09 / 0.04 | 0.87 | 0.87 | GGMGG | 0.198 / 0.145 | 0.811 | 3.0 p/m (6) | 8: 2.12–1.5 p | 7 |
| BL | 2022-11-05 | SV Werder Bremen **2-1** FC Schalke 04 | SV Werder Bremen (ev) | 0.73 / 0.17 / 0.09 | 0.74 | 0.55 | GGMMG | 0.956 / 1.688 | -1.785 | 1.17 p/m (6) | 10: 1.8–0.6 p | 8 |
| LL | 2023-05-28 | FC Barcelona **3-0** RCD Mallorca | FC Barcelona (ev) | 0.75 / 0.17 / 0.08 | 0.75 | 0.80 | GGGMM | -1.105 / -2.083 | 0.041 | 2.5 p/m (18) | 18: 2.34–1.34 p | 5 |
| SA | 2022-08-30 | AS Roma **3-0** AC Monza | AS Roma (ev) | 0.75 / 0.17 / 0.08 | 0.76 | 0.74 | BGGGB | 0.825 / 0.12 | None | 3.0 p/m (1) | 0 | 3 |
| PL | 2024-05-19 | Sheffield United FC **0-3** Tottenham Hotspur FC | Tottenham Hotspur FC (dep) | 0.71 / 0.15 / 0.13 | 0.71 | 0.65 | MMMGM | -1.256 / -1.979 | -1.522 | 1.33 p/m (18) | 18: 1.67–0.44 p | 5 |
| BL | 2024-01-27 | FC Augsburg **2-3** FC Bayern München | FC Bayern München (dep) | 0.67 / 0.19 / 0.14 | 0.67 | 0.68 | GGGMG | -0.123 / 0.139 | -0.124 | 2.38 p/m (8) | 16: 2.41–1.24 p | 3 |
| LL | 2024-04-13 | Cádiz CF **0-1** FC Barcelona | FC Barcelona (dep) | 0.60 / 0.25 / 0.15 | 0.61 | 0.67 | GBGGG | 0.945 / 0.447 | 0.98 | 2.14 p/m (14) | 18: 2.21–0.86 p | 14 |
| SA | 2024-05-10 | Frosinone Calcio **0-5** FC Internazionale Milano | FC Internazionale Milano (dep) | 0.74 / 0.16 / 0.09 | 0.75 | 0.81 | GBGGM | -0.472 / 0.022 | 1.361 | 2.59 p/m (17) | 18: 2.53–0.94 p | 6 |
| PL | 2025-04-26 | Newcastle United FC **3-0** Ipswich Town FC | Newcastle United FC (ev) | 0.78 / 0.13 / 0.09 | 0.78 | 0.80 | GGGGM | 0.694 / 0.337 | 0.287 | 2.0 p/m (16) | 18: 1.75–0.66 p | 7 |
| BL | 2024-09-27 | Borussia Dortmund **4-2** VfL Bochum 1848 | Borussia Dortmund (ev) | 0.78 / 0.15 / 0.07 | 0.79 | 0.75 | GGBGM | -0.01 / -0.661 | -1.458 | 3.0 p/m (2) | 0 | 5 |
| LL | 2024-08-25 | Real Madrid CF **3-0** Real Valladolid CF | Real Madrid CF (ev) | 0.83 / 0.12 / 0.05 | 0.84 | 0.85 | GGBBB | -0.533 / 0.708 | 0.971 | — | 0 | 7 |
| SA | 2025-05-24 | AC Milan **2-0** AC Monza | AC Milan (ev) | 0.74 / 0.17 / 0.09 | 0.74 | 0.80 | MGGGM | 0.121 / 0.601 | -0.335 | 1.72 p/m (18) | 18: 1.58–0.5 p | 6 |
| PL | 2025-11-30 | Aston Villa FC **1-0** Wolverhampton Wanderers FC | Aston Villa FC (ev) | 0.66 / 0.20 / 0.14 | 0.66 | 0.72 | GGMGG | 1.455 / 1.189 | -2.028 | 2.17 p/m (6) | 10: 2.1–0.1 p | 7 |
| BL | 2025-12-13 | Eintracht Frankfurt **1-0** FC Augsburg | Eintracht Frankfurt (ev) | 0.59 / 0.22 / 0.19 | 0.60 | 0.61 | BGGBM | -0.125 / -0.615 | 0.157 | 1.67 p/m (6) | 10: 1.5–1.0 p | 7 |
| LL | 2026-05-17 | FC Barcelona **3-1** Real Betis Balompié | FC Barcelona (ev) | 0.74 / 0.15 / 0.11 | 0.74 | 0.75 | GGGGM | 0.065 / 1.104 | 1.035 | 3.0 p/m (18) | 18: 2.51–1.63 p | 4 |
| SA | 2026-02-28 | Como 1907 **3-1** US Lecce | Como 1907 (ev) | 0.65 / 0.24 / 0.11 | 0.65 | 0.68 | GBMBG | 0.52 / 1.247 | 0.846 | 1.77 p/m (13) | 18: 1.68–0.96 p | 7 |
| PL | 2023-04-17 | Leeds United FC **1-6** Liverpool FC | Liverpool FC (dep) | 0.65 / 0.18 / 0.17 | 0.65 | 0.62 | GMMBB | -0.838 / -0.912 | 0.34 | 0.87 p/m (15) | 18: 1.57–0.9 p | 8 |
| BL | 2022-10-22 | TSG 1899 Hoffenheim **0-2** FC Bayern München | FC Bayern München (dep) | 0.64 / 0.19 / 0.17 | 0.65 | 0.57 | BMGBG | -0.758 / -0.503 | 0.049 | 1.6 p/m (5) | 6: 1.83–1.67 p | 6 |
| PL | 2022-12-27 | Manchester United FC **3-0** Nottingham Forest FC | Manchester United FC (ev) | 0.72 / 0.18 / 0.10 | 0.72 | 0.74 | GBGMG | 0.717 / 1.83 | 1.667 | 2.17 p/m (6) | 12: 1.83–0.83 p | sezon başı |
| BL | 2023-05-27 | RB Leipzig **4-2** FC Schalke 04 | RB Leipzig (ev) | 0.80 / 0.14 / 0.05 | 0.81 | 0.77 | MGGGG | 1.216 / 0.468 | 1.061 | 2.38 p/m (16) | 16: 1.88–0.97 p | 7 |
| LL | 2023-03-19 | Real Sociedad de Fútbol **2-0** Elche CF | Real Sociedad de Fútbol (ev) | 0.67 / 0.21 / 0.12 | 0.67 | 0.73 | GBMBB | -0.787 / -0.12 | -0.285 | 1.58 p/m (12) | 18: 1.75–0.54 p | 7 |
| SA | 2022-08-30 | FC Internazionale Milano **3-1** US Cremonese | FC Internazionale Milano (ev) | 0.81 / 0.13 / 0.06 | 0.81 | 0.83 | GGGGM | 0.14 / 0.359 | None | 3.0 p/m (1) | 0 | 4 |
| PL | 2023-09-01 | Luton Town FC **1-2** West Ham United FC | West Ham United FC (dep) | 0.65 / 0.18 / 0.17 | 0.65 | 0.42 | GMBGG | 0.994 / 0.365 | None | 2.0 p/m (2) | 2: 3.0–0.0 p | 6 |
| BL | 2024-03-10 | Bayer 04 Leverkusen **2-0** VfL Wolfsburg | Bayer 04 Leverkusen (ev) | 0.74 / 0.18 / 0.09 | 0.75 | 0.73 | GGGGG | 1.366 / 2.354 | -0.694 | 2.67 p/m (12) | 16: 2.65–1.09 p | 7 |
| LL | 2024-04-13 | RCD Mallorca **0-1** Real Madrid CF | Real Madrid CF (dep) | 0.60 / 0.25 / 0.15 | 0.60 | 0.66 | GBGGG | 0.529 / 0.847 | 1.007 | 2.27 p/m (15) | 18: 2.48–1.07 p | 13 |
| SA | 2023-08-27 | SSC Napoli **2-0** US Sassuolo Calcio | SSC Napoli (ev) | 0.76 / 0.15 / 0.09 | 0.76 | 0.75 | MGBGG | -0.326 / -0.685 | -1.925 | — | 0 | 8 |
| PL | 2025-05-25 | AFC Bournemouth **2-0** Leicester City FC | AFC Bournemouth (ev) | 0.65 / 0.20 / 0.14 | 0.65 | 0.74 | BBGMM | 0.042 / -0.911 | 0.852 | 1.39 p/m (18) | 18: 1.47–0.61 p | 5 |
| BL | 2025-10-31 | FC Augsburg **0-1** Borussia Dortmund | Borussia Dortmund (dep) | 0.63 / 0.21 / 0.16 | 0.64 | 0.54 | GGBMG | 0.478 / 1.715 | -0.924 | 1.75 p/m (4) | 7: 2.0–0.57 p | 6 |
| LL | 2024-11-02 | CA Osasuna **1-0** Real Valladolid CF | CA Osasuna (ev) | 0.65 / 0.21 / 0.14 | 0.65 | 0.64 | BGBMG | 1.05 / 1.496 | -0.858 | 2.17 p/m (6) | 6: 2.17–0.33 p | 6 |
| SA | 2024-10-26 | SSC Napoli **1-0** US Lecce | SSC Napoli (ev) | 0.70 / 0.22 / 0.08 | 0.71 | 0.72 | GBGGG | 1.348 / 1.095 | -0.771 | 3.0 p/m (4) | 2: 3.0–2.0 p | 6 |

## Kullanıcı adayları (ana sette olmayanlar; aynı yöntemle)
| Lig | Tarih | Maç | Favori (saha) | DC kaz/ber/kay | Poisson kaz | Elo kaz | Fav son 5 | Fav form5/10 | Rakip form5 | Fav bu saha (sezon) | Ortak rakip: fav–rakip p/m | Fav dinlenme (gün) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PL | 2022-10-22 | Nottingham Forest FC **1-0** Liverpool FC | Liverpool FC (dep) | 0.83 / 0.12 / 0.05 | 0.83 | 0.78 | BBMGG | -0.415 / -1.496 | -0.687 | 0.5 p/m (4) | 7: 2.14–0.71 p | 3 |
| PL | 2022-10-29 | Liverpool FC **1-2** Leeds United FC | Liverpool FC (ev) | 0.83 / 0.11 / 0.05 | 0.83 | 0.80 | BMGGM | -0.999 / -1.999 | -1.797 | 2.33 p/m (6) | 5: 0.8–0.2 p | 7 |
| PL | 2023-09-30 | Wolverhampton Wanderers FC **2-1** Manchester City FC | Manchester City FC (dep) | 0.76 / 0.15 / 0.09 | 0.76 | 0.73 | GGGGG | 0.865 / 0.361 | -0.495 | 3.0 p/m (3) | 0 | 7 |
| PL | 2023-12-31 | Fulham FC **2-1** Arsenal FC | Arsenal FC (dep) | 0.53 / 0.21 / 0.25 | 0.52 | 0.59 | GMGBM | -0.715 / -0.419 | -0.609 | 1.89 p/m (9) | 18: 2.17–1.11 p | 3 |
| PL | 2024-04-14 | Arsenal FC **0-2** Aston Villa FC | Arsenal FC (ev) | 0.69 / 0.18 / 0.13 | 0.69 | 0.65 | GGBGG | 0.951 / 2.515 | -0.765 | 2.53 p/m (15) | 18: 2.37–1.84 p | 8 |
| PL | 2024-10-19 | AFC Bournemouth **2-0** Arsenal FC | Arsenal FC (dep) | 0.68 / 0.20 / 0.12 | 0.68 | 0.65 | BGBGG | 0.406 / 1.605 | -0.358 | 2.33 p/m (3) | 2: 3.0–1.5 p | 14 |
| PL | 2024-11-02 | AFC Bournemouth **2-1** Manchester City FC | Manchester City FC (dep) | 0.67 / 0.20 / 0.13 | 0.67 | 0.70 | BBGGG | -0.014 / 0.838 | 0.5 | 2.5 p/m (4) | 4: 2.0–1.75 p | 7 |
| PL | 2025-05-03 | Arsenal FC **1-2** AFC Bournemouth | Arsenal FC (ev) | 0.64 / 0.21 / 0.15 | 0.64 | 0.71 | GBBGB | -0.547 / -1.425 | -0.441 | 2.12 p/m (17) | 18: 2.03–1.42 p | 10 |

- **Fulham 3-0 Tottenham (16.03.2024):** Modelde favori maçı değil. Tottenham'ın kazanma olasılığı DC'de %43, Elo'da %48. Bu yüzden "favori kaybetti" sınıfına girmiyor.
- **Fulham 2-1 Arsenal (31.12.2023):** Arsenal yalnızca %53 favori; eşiğin altında olduğu için ek listede.

## İlk bulgular (eşleştirilmiş fark = sürpriz − kontrol, %95 bootstrap GA)
Eşleştirme kalitesi iyi: DC favori olasılık farkı ortalama +0,007.

| Özellik | A: kaybetti − kontrol | B: berabere − kontrol | Tüm sürprizler − kontrol |
|---|---|---|---|
| favori_form5 | +0.04 [-0.62; +0.64] (n=18) | -0.58 [-1.11; -0.04] (n=12) | -0.21 [-0.67; +0.24] (n=30) |
| favori_form10 | +0.18 [-0.54; +0.90] (n=18) | -0.42 [-1.20; +0.38] (n=12) | -0.06 [-0.60; +0.48] (n=30) |
| rakip_form5 | -0.15 [-0.60; +0.30] (n=16) | -0.53 [-1.32; +0.20] (n=10) | -0.30 [-0.72; +0.09] (n=26) |
| rakip_form10 | -0.26 [-0.81; +0.31] (n=16) | -0.90 [-1.62; -0.17] (n=10) | -0.51 [-0.98; -0.07] (n=26) |
| favori_dinlenme_gun(<=30) | +1.06 [-0.59; +2.47] (n=17) | +2.46 [+0.64; +4.54] (n=11) | +1.61 [+0.36; +2.86] (n=28) |
| rakip_dinlenme_gun(<=30) | +0.71 [-0.94; +2.12] (n=17) | +1.46 [-1.27; +4.64] (n=11) | +1.00 [-0.39; +2.61] (n=28) |
| favori_14gun_mac | -0.44 [-0.89; +0.00] (n=18) | +0.00 [-0.50; +0.50] (n=12) | -0.27 [-0.63; +0.10] (n=30) |
| favori_son10_rakip_elo | +1.22 [-11.88; +14.69] (n=18) | +10.58 [-3.99; +24.53] (n=12) | +4.97 [-4.74; +14.99] (n=30) |
| elo_eksi_dc_favori_kazanir | -0.00 [-0.03; +0.03] (n=18) | -0.01 [-0.04; +0.03] (n=12) | -0.00 [-0.03; +0.02] (n=30) |
| dc_favori_kazanir(esleme_denetimi) | +0.01 [+0.00; +0.02] (n=18) | +0.00 [+0.00; +0.01] (n=12) | +0.01 [+0.00; +0.01] (n=30) |

**Ek ortalamalar (fark değil, grup değerleri):**

| Grup | Ortak rakiplere karşı favori − rakip | Favorinin bu sezon aynı sahadaki maç başı puanı (n ≥ 3 maç) |
|---|---|---|
| A | +1.06 p/m (n=14) | 2.14 p/m (n=14) |
| B | +1.08 p/m (n=10) | 1.88 p/m (n=10) |
| K | +1.18 p/m (n=25) | 2.05 p/m (n=24) |

**Yorum (keşif):**
- **A — favori kaybetti:** Hiçbir istatistik işareti kontrollerden ayrışmıyor. Favorinin formu, rakibin formu, dinlenme, yoğunluk ve rakip kalitesi farklarının güven aralıklarının hepsi sıfırı içeriyor. Kaybedilen maçların çoğunda favori formdaydı; örneğin Inter, Leverkusen, Arsenal ve Lazio'nun son 10 maçtaki formu beklentinin üzerindeydi.
- **B — berabere:**
  - Favorinin son 5 maçtaki formu kontrollerden düşük (−0,58 [−1,11; −0,04]).
  - Rakibin son 10 maçtaki formu da düşük (−0,90 [−1,62; −0,17]).
  - Favorinin dinlenmesi 2,5 gün daha uzun.

  Bu üç fark çoklu karşılaştırma düzeltmesi olmadan anlamlı. On özellik × üç grup test edildiği için tesadüf olabilirler. Ön kayıttaki F1 hipotezi (son 5 maçta form düşüşü) ile yön olarak tutarlılar, ama n=12.
- **Dinlenme:** Sürprizlerde favori daha az değil, daha **çok** dinlenmiş görünüyor. Lig dışı maçlar (kupa ve Avrupa) veride olmadığı için uzun lig arası, araya giren bir kupa veya Avrupa maçı ya da milli ara anlamına gelebilir. Yorgunluk bu veriyle **ölçülemez**.
- **Model ayrışması:** Elo ile DC'nin farkı sürprizlerde ve kontrollerde aynı (fark ≈ 0). Modellerin birbirinden ayrılması bu sette sürprizi işaret etmiyor.
- **Önceki tüm-maç analiziyle uyum:** Ön kayıttaki F1–F5 işaretleri bu aşamada çalıştırılmadı. Bu set onların yerine geçmez; bütün favori maçlarında çalıştırılmalıdır.

## Veri eksiklikleri
| Eksik | Etki | Çözüm yolu |
|---|---|---|
| Kupa ve Avrupa maçları | Dinlenme, yorgunluk ve rotasyon eksik ölçülüyor | Lisanslı ve ücretsiz kaynak (OpenFootball `uefa.cl` vb. kapsamı denetlenecek) ya da Katman 2 |
| Kadro, ilk 11, sakatlık, ceza | Asıl sürpriz açıklayıcıları yok | Katman 2 (tasarım: `docs/HABER_KATMANI.md`); tarihsel yapılandırılmış veri yok |
| Kırmızı kart, penaltı, maç içi sakatlık | Yalnızca maç sonrası açıklama olarak gerekli | Kaynakta yok → "veri yok" |
| xG ve şut | Şans ile performansı ayırmak mümkün değil | Açık ve lisanslı kaynak bulunamadı |
| İlk yarı skorları | Sonraki aşama | OpenFootball'da çoğu maç için var; yarı bazında analiz sonraki aşamada |
| Haberler | Bu sette hiç araştırılmadı | Katman 2 pilotu |
| Küçük örneklem | n=18/12; çoklu test | Sonuçlar hipotezdir |

## Araştırma planı (onayınızla)
1. **Katman 2 pilotu.** Bu 60 maçtan önceden belirlenmiş bir alt kümede (ör. her ligden 2 sürpriz ve 2 kontrol, 16 maç), `HABER_KATMANI.md`'deki sabit kontrol listesiyle maç öncesi haber araştırması yapılır.
   - Sürpriz ve kontrol maçları **aynı** listeyle araştırılır. Böylece "sürprizde haber bulundu" yanlılığı ölçülebilir.
   - Önce sayfa okuma için gerekli hostlar size önerilir.
2. **İşaretlerin bütün favori maçlarında ölçülmesi.** F1–F5 işaretleri dört ligin bütün favori maçlarında ölçülür. Önceden kayıtlı kurala göre en.1 keşif, de.1/es.1/it.1 doğrulama.
3. **Yarı bazında gol istatistikleri** (sonraki aşama).
4. **İleriye dönük test.** 2026-27 maçlarında tahmin ve haber kaydı maçtan önce dondurulur. Gerçek kör test ancak bu olur.
