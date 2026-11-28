# Test planı: modelin yeni yükselen takımlarda yanlılığı (2026-11-28; UYGULANMADI, model değişmedi)
Tetikleyici: 28.11'de en büyük model–fiyat ayrışmalarının çoğu yükselen takımlarda (Elche, Málaga, Frosinone, Elversberg, Coventry). Bu seçilmiş örnek tek başına kanıt DEĞİLDİR.

1. Örneklem: model değerlendirme liglerinde (E3, E2, Poisson E) son 5–6 sezonda yükselen TÜM takımlar; ilk sezon 1–19. ve 20–38. maçlar ayrı.
2. Karşılaştırma: aynı sezonlarda ligde kalan takımlar.
3. Zaman sıralı yeniden tahmin: her maç yalnızca o tarihten önceki veriyle (sızıntı yok). Oran kullanılmaz (MK-1).
4. Ölçütler: maç başına TEK birincil olay (1X2 üç sınıflı log-kayıp ve Brier; ayrıca 2,5 A/Ü ayrı analiz). Aynı maçın ilişkili marketleri bağımsız örnek sayılmaz.
   Kalibrasyon: güvenilirlik eğrisi, kutu başına gözlenen–beklenen, ECE; ev/deplasman ayrımı; yükselen takım lehine ve aleyhine sapma yönü.
5. Belirsizlik: maç düzeyinde bootstrap (≥1000) ile %95 aralık; lig bazında ayrı ve birleşik.
6. Karar ölçütü (önceden kayıt): yanlılık ancak yükselen–kalan farkı bootstrap aralığının dışında VE en az iki ligde aynı yönde ise kabul edilir. Aksi hâlde "kanıt yok".
7. Sonuç ne olursa olsun düzeltme ayrı ön kayıt + kullanıcı onayı gerektirir.
