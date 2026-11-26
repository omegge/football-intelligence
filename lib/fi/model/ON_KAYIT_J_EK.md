# J aşaması — ileriye dönük test protokolü EKİ: geniş kaynak araştırması (26.11.2026)
Ana kayıt: ON_KAYIT_J.md (değişmedi). Bu ek, açık internet araştırmasının (lib/fi/haber/genis.py) ileriye dönük
testte nasıl kullanılacağını sabitler.

## Evren ve körlük
- Evren: hazırlık kapısını geçmiş, bağımsız olasılığı DONDURULMUŞ ve bağımsız modelde favorisi P(kazanır) ≥ 0,55 olan
  maçlar. Favori oranlarla ya da dış görüşlerle belirlenmez.
- Turlar: T−24s, T−6s, T−90dk; her turda aynı sorgu şablonu (her iki takım ayrı: kulüp, yerel basın, ulusal basın,
  ajans, muhabir, önizleme, istatistik, topluluk). Araştırma sonuçtan önce kaydedilir ve SHA-256 ile dondurulur.

## Haber türleri (keşifte tanımlandı; pilot 16 maç: favori_eksik_veya_ceza 5/8 sürpriz vs 1/8 kontrol)
- H1 favori_eksik_veya_ceza: favori takımda son 5 lig maçının ≥ 3'ünde ilk 11 başlamış oyuncunun sakatlık/ceza ile
  yokluğu ya da teknik direktör cezası.
- H2 rakip_td_degisimi: rakipte son 14 günde teknik direktör değişikliği.
- H3 favori_yogun_fikstur: favorinin önceki resmi maçından bu yana ≤ 72 saat (veriyle hesaplanır, haber gerekmez).
- H4 celiskili_kadro: favori için çözülmemiş "hazır ↔ şüpheli/yok" çelişkisi T−90dk'da.
İşaret yalnızca doğrulama düzeyi `resmi` ya da `iki_bagimsiz` olan iddialarla verilir (H3 hariç: veri). Arama özeti
düzeyinde kalan iddia işaret değildir; ayrıca "araştırma kapsamı" olarak raporlanır.

## Ölçüm ve karar
- Her tür için: işaretli maçlarda (gerçekleşen kazanamama − dondurulmuş tahmin) ortalaması, lig-sezon kümeli %95 GA;
  doğru pozitif, yanlış alarm, yakalama, yanlış keşif oranı.
- En az 150 işaretli maç (tür başına) birikmeden karar yok. GA alt sınırı > 0 → "modele yansımamış bilgi" (ancak yine de
  olasılığa otomatik eklenmez; ayrı ön kayıtla düzeltme modeli kurulur ve yeni dönemde sınanır).
- Dış görüşler (önizleme yüzdeleri, tahminler) hiçbir türün tanımına ve hiçbir ölçüme girmez.
