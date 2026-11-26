# F aşaması — ön kayıttan sapma kaydı (26.11.2026)

İlk çalıştırma (output/model/f_asamasi_20261126_161200) ön kayda uygun yapıldı ve SAKLANDI.
Seçilim yanlılığı kontrolü şunu gösterdi: ilk yarı skoru eksik maçların maç sonu gol ortalaması 0,00–0,05
(it.2 0,046; fr.2 0,031; en.3 0,000; en.4 0,000), skoru olanlarınki 2,66–2,83. Kaynak, 0-0 biten maçların çoğunda
ilk yarı skorunu yazmıyor. Bu maçlar dışarıda kalınca değerlendirme kümesi 0-0'ları kaybediyor; λ'lar ise bütün
maçlardan kestirildiği için model ile değerlendirme kümesi tutarsızlaşıyor.

Düzeltme (mantıksal, tahmin değil): maç sonu 0-0 ise ilk yarı 0-0'dır. Yalnızca bu durumda ilk yarı skoru 0-0 kabul
edilir ve sayısı raporlanır. Maç sonu 0-0 olmayan eksik maçlar eksik kalır. Model, parametreler, ligler, dönem ve karar
kuralları DEĞİŞMEZ. İkinci çalıştırma "F-v2 (sapma)" olarak etiketlenir; iki çalıştırma da raporda yan yana verilir.
