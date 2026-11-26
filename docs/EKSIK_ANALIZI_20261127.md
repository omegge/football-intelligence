# Football Intelligence — eksik analizi ve geliştirme sırası (27.11.2026)

Temel: `feature/football-intelligence-v1` (86efd17) ve commit edilmemiş Render hazırlığı.
- Render hazırlığı silinmedi. Tam yaması `output/yedek/render_hazirligi_20261126T222303Z.patch` dosyasında (SHA-256 `a80b9554…`).
- Commit sırasında yayım dosyaları ayrı bir dala ayrılacak: `render.yaml`, `deploy/`, `.github/`, `.python-version`, `docs/BULUT_DAGITIMI.md`.

Önem = kullanıcıya doğru bağımsız olasılık verebilme üzerindeki etki × düzeltilebilirlik.

| # | Eksik | Kanıt | Önem |
|---|---|---|---|
| 1 | **Temel marketler kapsam dışı: MS 1, MS 2, ÇŞ 1X/X2, 2,5 Alt/Üst** | E2 sınamasında MS_1 kalibre değil. Uçlarda sistematik eksik güven: 0,1–0,2 kutusunda tahmin 0,164, gerçekleşen 0,086 (n = 139, ≈ 3,2 SH). 0,7–0,8 kutusunda tahmin 0,738, gerçekleşen 0,851 (n = 154, ≈ 3,9 SH). Lig ECE sco.1'de 0,066, gr.1'de 0,062. 2,5 Üst'te havuz ECE 0,018 ama tr.1 0,046. | **Çok yüksek** |
| 2 | **Büyük liglerde değerlendirilmiş model yok** | Kapsam kaydında E2 6 ligde (en.2, at.1, be.1, sco.1, tr.1, gr.1), Poisson E 5 ligde. en.1, de.1, it.1, es.1 hiçbir modelin ileriye dönük değerlendirme listesinde değil. Onaylansalar bile "hesaplanamaz". | **Çok yüksek** |
| 3 | **Sezon içi kayma denetimi yok** | Championship 2026-27: KG +0,080, 2,5 Üst +0,108 düşük tahmin (SOU–MID KG ayrışma raporu). Kapsam kararı yıllar öncesinin ortalamasına dayanıyor. | Yüksek |
| 4 | **İleriye dönük doğrulama birikmiyor** | 1 donmuş tahmin, 0 puanlanmış maç. Günlük otomatik dondurma ve puanlama yok. | Yüksek |
| 5 | Lig ve takım eşleme onayları darboğaz | Yalnızca en.2 onaylı. 28.11'de 7 Championship maçı takım onayı bekliyor. Arayüzde kanıtla onay aracı yok. | Yüksek (kullanılabilirlik) |
| 6 | İstatistik kaynakları dar | Yalnızca skor ve ilk yarı (OpenFootball + football-data.org ücretsiz, 9 yarışma). Kadro, xG, şut, sakatlık, kart ve korner verisi yok. | Orta–yüksek |
| 7 | Haber araştırması elle yapılıyor | Otomatik tur yok. İleriye dönük J protokolü (≥ 150 işaretli maç) başlamadı. | Orta |
| 8 | Sürpriz ve piyasa araştırması küçük, piyasa verisi yok | 10+10 keşif; izinli kapanış oranı kaynağı bulunamadı. | Orta (MK-1 gereği modele girmez) |
| 9 | Nesine özel marketleri (korner, kart, oyuncu, yarı marketleri) | Veri ve model yok. F2 devre modeli kapsamda değil. | Orta (veri gelmeden olasılık verilemez) |
| 10 | Arayüz birleştirme | Sürpriz, haber ve kapsam araçları kısmen bağlı. Onay ve araştırma iş akışları arayüzde yok. | Orta |

## Sıra
1. **E3 aşaması (bu adım), eksik 1 + 2 + 3:** E2'nin üstüne yalnızca geçmiş veriyle, zaman sıralı iki düzeltme eklenir.
   - Güç farkı ölçeği ve ev sahibi kayması (1X2 uç kalibrasyonu).
   - Sezon içi toplam gol kayması.
   - Hepsi tek bir skor matrisinden; tutarlılık korunur.
   - Ön kayıtla, daha önce gol marketleri değerlendirilmemiş liglerde tek seferlik sınama.
2. Günlük dondurma ve puanlama döngüsü + sezon içi kayma kapısı (eksik 3–4).
3. Kanıtlı eşleme onay aracı (eksik 5).
4. Kaynak genişletme (eksik 6), haber otomasyonu (eksik 7), özel marketler (eksik 9), arayüz birleştirme (eksik 10).
5. Sürpriz ve piyasa araştırmasının genişletilmesi (eksik 8).
