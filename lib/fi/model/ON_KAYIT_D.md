# D aşaması — önceden kayıt (doğrulama çalıştırılmadan önce yazıldı, 24.11.2026)

Doğrulama verisi: de.1, es.1, it.1 — 2022-23 … 2025-26 (OpenFootball). Bu ligler bu projede daha önce hiç
model değerlendirmesinde kullanılmadı. Model ayarları değişmez: Dixon–Coles/Poisson ξ = 0,003, pencere 1095 gün,
ceza 2,0 (en.1 ayar döneminde seçilmişti). Elo: K = 15, ev avantajı 70, sezon çekimi 0,15. MK-1: oran yok.

## Hipotezler ve karar kuralları
- H1 (Dixon–Coles faydası): geliştirmede (en.1 2016-17…2021-22) DC − Poisson log-loss farkı +0,0016
  (%95 GA +0,0003/+0,0028; DC daha kötü). Doğrulamada üç ligin en az ikisinde fark ≥ 0 ise ya da birleşik GA'nın
  alt sınırı > 0 ise → 1X2 için varsayılan model Poisson önerilir; DC yalnızca karşılaştırma olarak tutulur.
  Aksi halde karar ertelenir (DC lehine kanıt sayılmaz).
- H2 (düşük skor/beraberlik): DC'nin beklenen beraberlik sayısı gerçekleşenden büyüktür ve Poisson'unkinden büyüktür.
- H3 (yeni takım önseli): mevcut uygulamada önsel yalnızca ilk maçtan önce etkili olduğu için geçmişten kestirilen
  önsel (V1) ile sabit önsel (V0) arasındaki log-loss farkı |fark| < 0,001 olur.
- Seçilen önsel varyantı: `V1_gecmisten`

## Form işaretleri (keşif: en.1 2022-23…2025-26 — önceden görülmüş veri; doğrulama: de.1/es.1/it.1)
Favori: Dixon–Coles maç öncesi olasılığına göre, P(favori kazanır) ≥ 0,5. Sürpriz-1: favori kaybeder.
Sürpriz-2: favori kazanamaz (beraberlik dahil).
- F1 "form düşüşü-5": favorinin son 5 lig maçında Σ(sonuç − Elo beklentisi) ≤ −1,0.
- F2 "form düşüşü-10": son 10 maçta Σ ≤ −1,5.
- F3 "kısa dinlenme": önceki lig maçından bu yana ≤ 3 gün (yalnızca lig maçları görülür; kupa/Avrupa yok).
- F4 "yoğun fikstür": son 14 günde ≥ 3 lig maçı.
- F5 "deplasman favorisi".
Ölçüm: işaretli ve işaretsiz gruplarda (gerçekleşen − tahmin edilen) sürpriz oranı ve %95 GA; işaret alarmı olarak
isabet, yakalama, yanlış pozitif oranı (FPR), yanlış keşif oranı (FDR), taban orana kaldıraç. Bir işaret ancak
doğrulama liglerinde de işaretli grupta (gerçekleşen − tahmin) > 0 ve GA alt sınırı > 0 ise "modele yansımamış bilgi"
sayılır. Hiçbir işaret bu aşamada modele eklenmez.
