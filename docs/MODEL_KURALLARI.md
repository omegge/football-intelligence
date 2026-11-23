# Değişmez modelleme kuralları

Durum: **mimari gereksinim** (23.11.2026). Mevcut kod davranışını değiştirmez; bundan sonra yazılacak her araştırma,
model, karşılaştırma ve kupon bileşeni bu kurala uymak zorundadır. Kuralın gevşetilmesi yalnızca kullanıcının açık,
yazılı kararıyla olur.

## MK-1 — Oran bağımsızlığı

1. Nesine oranları (ve oranlardan türetilen her şey: ima edilen olasılık, marjı arındırılmış olasılık, favori/sürpriz
   etiketi, oran hareketi, MBS) şu aşamalarda **kullanılmaz**: favori belirleme, takım gücü değerlendirme, maç sonucu
   tahmini, olasılık hesaplama, kalibrasyon, ağırlıklandırma, model seçimi, hiperparametre ayarı, backtest.
2. Favori ve sürpriz adayları yalnızca bağımsız futbol verileriyle belirlenir (geçmiş sonuçlar, rakip kalitesi,
   güncel haberler, kadro, taktik, doğrulanmış istatistikler).
3. Bağımsız tahmin, oranlardan ima edilen olasılıklarla **düzeltilmez, ağırlıklandırılmaz, harmanlanmaz, kalibre
   edilmez** (ör. "piyasa ile karışım", "kapanış oranına göre kalibrasyon" yasak).
4. Zorunlu sıra:
   1. Bağımsız kanıt toplama (`lib/fi/kanit.py`) ve bağımsız tahmin.
   2. Tahmini **dondurma**: tahmin dosyası + oluşturma zamanı (UTC/TR) + içerik SHA-256 + kullanılan kanıt kimlikleri
      + veri anlık görüntüsü özetleri. Dondurulmuş dosya değiştirilemez; değişiklik yeni sürüm demektir.
   3. Ancak bundan sonra Nesine oranları açılır ve **fiyat karşılaştırması** yapılır. Karşılaştırma dondurulmuş tahmini
      geriye dönük değiştirmez.
5. Aynı olayın farklı Nesine pazarlarındaki fiyatları (ör. MS 1 ile "1 ve 2,5 Üst") birbirleriyle **matematiksel olarak
   karşılaştırılabilir**; ancak bu fiyat oranları gerçek olasılık ya da bağımsız/koşullu olasılık olarak sunulmaz,
   raporda "fiyat oranı" olarak etiketlenir.
6. Yeterli veri ya da doğrulanmış model olmayan pazarlarda (korner, kart, oyuncu, özel/birleşik pazarlar vb.) olasılık
   uydurulmaz; sonuç "hesaplanamaz — eksik veri/model: …" olur.

## Bileşenlere göre uygulama

| Bileşen | Gereksinim |
|---|---|
| `CLAUDE.md` | Kural 4 (MK-1) her oturumda yüklenir. |
| Araştırma modülleri | Yalnızca `girdi.fikstur_oku` ile oransız fikstür okunur; bülten dosyaları doğrudan okunmaz. Kanıt kaydı oran/bahis konusunu ve Nesine hostlarını reddeder (`kanit.py`, mevcut). |
| Model girdileri | Model fonksiyonları yalnızca kanıt kaydından ve oransız girdiden beslenir; girdide `oran/odds/market/secenek/mbs/kupon/bahis/fiyat` anahtarı bulunursa `OranSizintisi` (mevcut `girdi.oransiz_mi`). Model modülleri bülten çekicisini ya da bülten JSON/Excel dosyalarını içe aktaramaz. |
| Dondurma | Tahmin dosyası SHA-256 + zaman damgasıyla yazılır; karşılaştırma modülü dondurulmamış ya da özeti tutmayan tahmini reddeder; karşılaştırma zamanı dondurma zamanından sonra olmalıdır. |
| Fiyat karşılaştırması | Ayrı modül; tahmine yazamaz. Pazarlar arası fiyat ilişkileri "fiyat oranı" etiketiyle raporlanır, olasılık olarak değil. |
| Testler | Her yeni model/karşılaştırma bileşeni için: oran sızıntısı testi, dondurma-öncesi-karşılaştırma reddi testi, özet değişikliği tespiti testi, veri yetersiz pazarda "hesaplanamaz" testi. Kuralın `CLAUDE.md` ve bu belgede bulunduğu da test edilir (`tests/test_altyapi.py`). |
| Kupon (ileride, yalnızca açık talep) | Seçimler yalnızca dondurulmuş bağımsız tahmine dayanır; oranlar yalnızca fiyat/değer karşılaştırmasında görünür. Ek olarak: doğrulanmamış eşleşmeli maçlar, `oynanabilir` olmayan oranlar ve "hesaplanamaz" pazarlar kupona alınmaz. |
