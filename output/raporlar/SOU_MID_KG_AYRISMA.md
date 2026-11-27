# Southampton – Middlesbrough: KG Var ayrışması (A izi)

Dondurulmuş tahmin `output/tahminler/nesine_3331002_20261126T181800Z.json`:
- SHA `8d4b1a45…`, donma zamanı 2026-11-26T18:18:00Z.
- Model E2_aday; λ ev 1,607, dep 1,150.

**Tahmin DEĞİŞTİRİLMEDİ; model piyasaya göre ayarlanmadı.** Bu rapor, sapmanın nedenini anlamak içindir.

## Rakamlar
| | Değer | Niteliği |
|---|---|---|
| E2 P(KG Var) | 0,546 | bağımsız olasılık |
| Nesine KG Var 1,35 → 1/oran | 0,741 | başabaş eşiği, olasılık değil |
| KG Var/Yok, marj çıkarılmış fiyat oranı | 0,624 | fiyat oranı, olasılık olarak sunulmaz |
| Championship 2026-27 gerçekleşen KG oranı (bugüne kadar) | 0,608 | veri (football-data.org) |
| Championship uzun dönem KG oranı | 0,507 | veri (openfootball) |

## Nedenler
1. **Büzülme, sapmanın ana nedeni değil.**
   - Varyantların hepsinde KG 0,543–0,551 arasında: w = 0,65 / b = 0, büzülmesiz ve farklı ceza değerleri.
2. **Asıl neden: lig düzeyinde sezon kayması.**
   - Bu sezon Championship maç başına 2,90 gol ve %60,8 KG üretiyor.
   - E2, 365 günlük lig ortalamasına büzüldüğü için bu yükselişi geç yakalıyor.
   - Geriye dönük kalibrasyon:
     - E2 Championship KG'yi 2025-26'da **+0,062**, 2026-27'de **+0,080** düşük tahmin etti;
     - 2,5 Üst'ü 2026-27'de **+0,108** düşük tahmin etti.
   - Kaymanın yarısı düzeltilse bile model KG ≈ 0,58–0,59 olur. Bu, 0,741 başabaş eşiğinin hâlâ çok altında.
3. **Takım düzeyi:**
   - E2'nin λ'ları ve maç öncesi haberler model içinde tutarlı.
   - Southampton ev hücumu lig ortalamasının üstünde.
   - Middlesbrough'da Lankshear'ın durumu çelişkili; Alfie Jones, Barron ve Pukstas yok. Kaynaklar `SOU_MID_20261127_RAPOR.md` ve genis v2.
   - Bunlar modele uygulanmadı; YORUM bölümünde tutuluyor.
4. **Analistlerin 2-1 / 1-1 / 2-2 tahminleri:**
   - İkisi de gol atar senaryosuna dayanıyor: iki takımın yoğun takvimi ve savunma eksikleri.
   - Bu, piyasa fiyatıyla aynı yönde ama bağımsız bir olasılık değil. Model girdisi olarak kullanılmadı.

## Sonuç
- Sapmanın en olası açıklaması: modelin bu sezonki gol artışına geç uyum sağlaması (yapısal, ölçülmüş bir yanlılık) ve buna ek olarak piyasanın KG Var tarafındaki yüksek marjı.
- KG Var'ın gerçek olasılığı muhtemelen 0,546'dan yüksek. Bu, modelin kendi geçmiş hatasından çıkan bir yargıdır, piyasadan değil.
- **"Pozitif EV" görünen KG Yok satırı bu yüzden güvenilir değildir.** Öneri değildir.

## Öneri (ön kayıt gerekiyor, şimdi uygulanmadı)
**Kapı "sezon içi kalibrasyon kayması":**
- Ölçüt: Bir ligin içinde bulunulan sezonda, oynanmış ≥ 100 maçta, bir pazarın ortalama tahmin ile gerçekleşen oranı arasındaki fark %95 güven aralığıyla sıfırı dışlıyorsa, o lig–pazar "kapsam dışı (kayma)" olur.
- İşleyiş: Bu ölçüt `is_akisi.bagimsiz_tahmin` içinde günlük olarak denetlenir.
- Neden önemli: Bu kural bugün geçerli olsaydı Championship KG ve 2,5 Alt/Üst pazarları raporlanmazdı.
- Uygulama ancak onayınızla ve yeni ön kayıt dosyasıyla yapılır.

## Bekleyen turlar
- T−6s (2026-11-27 14:00Z) ve T−90dk (18:30Z) zamanlandı.
- Kesin ilk 11'ler ayrı klasörlere kaydedilecek: `sou_mid_20261127_T6s`, `_T90dk`.
- Dondurulmuş tahmin değişmez.
