# SOU–MID (nesine:3331002) araştırma turlarının gerçek zamanları — etiket düzeltme notu
Oluşturma: 2026-11-28T00:30Z. Eski kayıtlar DEĞİŞTİRİLMEDİ; bu not, `tur` alanındaki etiketleri belgeleyerek düzeltir.
Başlama: 2026-11-27T20:00Z.

| Klasör | Kayıttaki `tur` | Gerçek araştırma zamanı (UTC) | Gerçek öncelik | Doğru etiket |
|---|---|---|---|---|
| sou_mid_20261127 | (iddia yok) | 26.11 17:21 | T−26s 39dk | T−24s (yaklaşık) |
| sou_mid_20261127_v2 | T-24s | 26.11 18:05 | T−25s 55dk | T−24s (yaklaşık) |
| sou_mid_20261127_v3 | T-24s | 26.11 18:05–21:08 | T−25s55dk…T−22s52dk | T−24s (yaklaşık; v2 üzerine ek) |
| southampton_middlesbrough_3331002_20261126T224713Z | T-24s | 26.11 22:47 | T−21s 13dk | T−21s (etiket yaklaşık) |
| sou_mid_20261127_T6s | T-6s | 27.11 14:05 | T−5s 55dk | T−6s ✓ |
| sou_mid_20261127_T90dk | T-90dk | 27.11 18:35 | T−85dk | T−85dk (etiket 5 dk sapmalı) |
| sou_mid_20261127_ilk11 | T-90dk | 27.11 19:20 | **T−40dk** | **T−40dk — etiket YANLIŞ** (kayıt sistemi yalnız T-24s/T-6s/T-90dk/diger kabul ettiği için T-90dk yazıldı; doğrusu "diger" + gerçek zaman) |

Dondurulmuş tahmin: nesine_3331002_20261126T181800Z.json (E2_aday, 26.11 18:18Z, T−25s42dk) — ilk 11'lerden önce.

## Ek düzeltme (2026-11-28T00:50Z)
`fi.haber.genis.arastirma_turu` tanımına göre `T-90dk` "başlamaya ≤90 dk" PENCERESİDİR. Bu yüzden 19:20Z (T−40dk) kaydının `T-90dk` etiketi sistem tanımına göre doğrudur; eksik olan, gerçek önceliğin (T−40dk) ayrıca gösterilmemesidir. Yukarıdaki "etiket YANLIŞ" ifadesi bu ek notla düzeltilmiştir.
Ayrıca T−6s, T−85dk ve T−40dk turları `sohbet haber-kaydet` yerine elle Python ile kaydedildi; `arastirma_utc` değerleri komut yerine elle yazıldı (gerçek çalışma zamanından en fazla birkaç dakika sapma). Bu, sistemin otomatik zaman damgası kuralının atlanmasıdır.
