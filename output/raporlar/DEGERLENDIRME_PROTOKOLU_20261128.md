# İleriye dönük model değerlendirme protokolü (2026-11-28; mevcut kod değişmedi)
- Sonuçlar, gerçekleştikten sonra football-data.org'dan `fi.kaynaklar.guncel guncelle` + `sohbet hafiza --guncelle` ile AYRI kaydedilir; dondurulmuş tahmin dosyaları değiştirilmez (SHA-256 kayit.jsonl ile denetlenir).
- Maç başladıktan sonra yayımlanan bilgi maç öncesi kayda eklenmez.
- `sohbet performans` şu an maç başına 26–38 marketin ORTALAMA log-kaybını gösterir; bu marketler ilişkili olduğundan örneklem büyüklüğü = maç sayısıdır, market sayısı değil.
- Birincil ölçüt: maç başına tek olay (1X2 üç sınıflı log-kayıp/Brier); ikincil: 2,5 A/Ü. Kalibrasyon kutuları ve bootstrap aralıkları maç düzeyinde hesaplanır.
- 100 puanlanmış maçtan önce performans iddiası yapılmaz (mevcut kural).
