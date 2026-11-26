# J aşaması — haber ve sürpriz sinyalleri: keşif özeti ve ileriye dönük test ön kaydı (26.11.2026)

## Keşif (tamamlandı; BAŞARI KANITI DEĞİLDİR)
Veri: output/arastirma/set_v1 (30 sürpriz + 30 eşleştirilmiş kontrol; GERİYE DÖNÜK seçildi) ve pilot_v1 (8 sürpriz +
8 kontrol, 17 maç öncesi haber kanıtı). Çıktı: output/arastirma/kesif_j/ozellik_karsilastirmasi.json.
- Sayısal maç öncesi özelliklerin hiçbirinde sürpriz−kontrol farkının %95 GA'sı 0'ı dışlamıyor (favori form5 −0,21
  [−0,63; +0,25]; favori yoğunluk14 −0,27 [−0,60; +0,10]). "Dinlenme" sezon ilk maçında yaz arasını sayıyor (yapay).
- Favori aleyhine maç öncesi doğrulanmış haber (sakatlık/ceza/TD cezası): sürpriz 5/8, kontrol 1/8 (Fisher iki yönlü
  p ≈ 0,12). Araştırma sonuç bilinerek yapıldı → doğrulama yanlılığı dışlanamaz. Yalnızca HİPOTEZ.

## İleriye dönük test (H-J1)
Hipotez: Maç öncesi, sonuç bilinmeden kaydedilmiş "favori aleyhine doğrulanmış önemli eksik" işareti olan maçlarda
favorinin kazanamama oranı, bağımsız modelin (dondurulmuş) öngördüğünden yüksektir.
- Evren: günlük akışta bağımsız olasılığı DONDURULMUŞ (hazırlık kapısını geçmiş) ve favorisi P(kazanır) ≥ 0,55 olan
  maçlar; favori yalnızca bağımsız modelle belirlenir (oran yok).
- Körlük: haber araştırması maç başlamadan önce yapılır ve `AramaOturumu(mod="guncel", tahmin_sha256=…)` ile
  dondurulur; araştırma hem işaretli olabilecek hem olamayacak maçlarda aynı kontrol listesiyle (KONTROL_LISTESI) yapılır.
- İşaret tanımı (değişmez): favori takımda, yayın zamanı maç başlangıcından önce ve kanıt düzeyi `resmi` ya da
  `cok_kaynak` olan, ilk 11 oyuncusunun (son 5 lig maçının ≥3'ünde ilk 11) sakatlık/ceza nedeniyle yokluğu, ya da
  teknik direktör cezası/değişikliği. Tek kaynak işaret sayılmaz.
- Ölçüm: işaretli grupta (gerçekleşen kazanamama − dondurulmuş tahmin) ortalaması, lig-sezon kümeli bootstrap %95 GA.
  Doğru pozitif (işaretli ve sürpriz), yanlış alarm (işaretli ve favori kazandı), yakalama ve yanlış keşif oranı birlikte
  raporlanır.
- Karar: en az 150 işaretli maçtan önce sonuç raporlanmaz (ara rapor yalnızca sayım). GA alt sınırı > 0 ise "modele
  yansımamış bilgi" sayılır; bu bile otomatik olarak olasılığa EKLENMEZ — ayrı bir ön kayıtla düzeltme modeli kurulur
  ve yeni bir ileriye dönük dönemde sınanır.
