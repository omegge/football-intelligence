# F2 aşaması — devre bağımlılığı modeli ön kaydı (sınama verisi açılmadan önce, 26.11.2026)

Gerekçe: F-v2'de "λ verildiğinde bağımsız devreler" (F0) varsayımı birleşik devre seçeneklerinde reddedildi
(1Y KG–2Y KG olasılık oranı gözlenen 1,20, model 1,12; 801 ve İY/MS seçeneklerinde gerçekleşen−tahmin ≠ 0).

## Veri ayrımı
- GELİŞTİRME (katsayı kestirimi): it.2, fr.2, en.3, en.4, 2019-07-01 sonrası (F'nin verisi).
- SINAMA (tek çalıştırma): en.2 (football-data.org 2026-27 dahil), at.1, be.1, sco.1, tr.1, gr.1. Bu liglerin devre
  skorları hiçbir değerlendirmede kullanılmadı.
- İlk yarı skoru: kaynakta yoksa ve maç sonu 0-0 ise 0-0 (mantıksal; ON_KAYIT_F_SAPMA.md); diğer eksikler dışarıda.
  Takım başına devre golü > 7 olan maç kırpılmaz, dışarıda bırakılır.

## Modeller
λ_ev, λ_dep: M0 Poisson (ceza 2,0). s_ev, s_dep: ligde tahmin tarihinden önceki kayıtların 1Y gol payı.
- F0: dört devre golü bağımsız Poisson (F aşamasıyla aynı).
- F1 (durum bağımlı): 1Y bağımsız Poisson; 2Y hızı ilk yarı durumuna bağlı:
  λ_takım,2 = λ_takım·(1 − s)·exp(β_önde·[takım 1Y önde] + β_geride·[takım 1Y geride]).
  β_önde, β_geride geliştirme verisinde 2Y gollerinin Poisson regresyonuyla (ofset log λ_takım,2) kestirilir ve
  sınamada SABİT tutulur.

## Ölçütler ve karar kuralları
Marketler: Nesine 7, 9, 209, 14, 15, 452, 599, 455, 457, 779 (marjinal); 801, 5, 48, 295, 296, 528, 529, 584, 585,
591, 592, 586, 587 (birleşik). Taban: ligde tarih öncesi frekans.
- "Bilgi taşıyor": F1 − taban log loss lig-sezon kümeli GA üst sınırı < 0.
- "Kalibre": havuz ECE ≤ 0,02, n ≥ 30 kutularda sapma ≤ 0,05, her sınama liginde ECE ≤ 0,04.
- "Bağımlılık açıklandı" (birleşik seçenek): F1'de ortalama (gerçekleşen − tahmin) GA'sı 0'ı içerir.
- "İyileşme": F1 − F0 GA üst sınırı < 0.
Günlük kapsam yalnızca "bilgi taşıyor" VE "kalibre" seçeneklere (birleşiklerde ayrıca "bağımlılık açıklandı").
Yüksek oranlı seçenekler (olay sıklığı < %5) için ayrıca kutu başına n ≥ 30 sağlanmadıkça kalibre sayılmaz.
