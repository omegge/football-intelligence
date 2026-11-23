# Araştırma altyapısı (lib/fi, 0.3.0)

Yalnızca Python standart kütüphanesi. Testler: `tests/test_altyapi.py` (B1–B6, ağsız).
Kullanım: `PYTHONPATH=lib python3 -c "from fi import girdi; ..."`

## Akış
```
bülten klasörü (oranlı)  --girdi.fikstur_yaz-->  fikstur.json (ORANSIZ)  --mac_bul-->  output/analiz/<tarih>_<kod>/
                                                                                       ├── girdi.json (oransız)
                                                                                       └── kanit.jsonl
kaynaklar (ClubElo, football-data) --http.VeriIstemcisi--> okuyucu --> Kanit --> kanit.jsonl
```
Analiz modülleri bülten dosyalarını DOĞRUDAN okumaz; `girdi.fikstur_oku` oransız fikstür dışındaki dosyayı reddeder.

## kanit.py
Alanlar: `mac_id, konu, iddia, deger, kaynak_adi, kaynak_url, erisim_zamani, dogrulama, yayin_tarihi,
olcum_baslangic, olcum_bitis, birim, takim, ham_sha256, turetildigi, notlar, kimlik`.

Doğrulama seviyeleri: `resmi`, `veri_kaynagi`, `cok_kaynak`, `tek_kaynak`, `tahmin`, `hesaplandi`, `dogrulanamadi`.

Kurallar (ihlal = `KanitHatasi`):
- Kaynak URL'si yoksa yalnızca `hesaplandi` olabilir ve `turetildigi` depoda bulunan kanıtları göstermeli.
- `dogrulanamadi` değer taşıyamaz; değeri olmayan kanıt yalnızca `dogrulanamadi` olabilir (sayı uydurma yasağı).
- Konu `oran/bahis/piyasa/kupon` olamaz; Nesine bülten hostları kaynak olamaz; değerde `oran`, `odds`, `mbs` … anahtarı olamaz.
- Yayın tarihi erişimden sonra, ölçüm başlangıcı bitişten sonra olamaz.
- Depo JSON Lines, yalnızca ekler; aynı içerik bir kez yazılır (kimlik = içerik özeti).

## takim_adlari.py
- Otomatik kabul yalnızca `onayli` (kullanıcı onayı, `veri/takim_eslemeleri.json`) ve `kesin` (normalleştirilmiş ad
  birebir aynı, aday listesinde tek, gençler/kadın/B takımı gibi ayırt edici ekler aynı).
- Normalleştirme: Türkçe harfler, aksanlar, noktalama, kulüp ekleri (FC, SK, AC …), az sayıda belirsiz olmayan
  kısaltma (`utd → united`, `st → saint`).
- Benzerlik skoru yalnızca öneri üretir (`belirsiz` + `alternatifler`); hiçbir zaman tek başına kabul sebebi değildir.
- `onay_ekle` yalnızca kullanıcı açıkça onayladığında çağrılır.

## girdi.py
- Beyaz liste: `kod, nid, canli_kodu, akis, lig, lig_ulke, lig_kodu, ev, deplasman, karsilasma, baslama_tr, tarih,
  saat, diger_akista_da_var, dogrulanmamis_eslesme, isim_celiskisi, baslama_saati_gecmis, zaman_okunamadi`
  + `mac_id`, `ewma_kaydi`.
- `oransiz_mi` her anahtarı tarar (`oran, odds, market, secenek, mbs, kupon, bahis, oynanabilir, price, fiyat`).
- Doğrulanmamış eşleşmeli maçın araştırma girdisine "kupona alınmamalı" uyarısı yazılır.

## http.py
- `KAYNAKLAR`: kaynak → izinli hostlar, asgari istek aralığı (2 sn), önbellek süresi, beklenen tür, koşullar sayfası.
  Nesine burada yoktur.
- Dürüst User-Agent; çerez/token/tarayıcı taklidi yok.
- Önbellek: `output/onbellek/` (git dışı), SHA-256 ile bütünlük kontrolü.
- 401/403/407/429/451, ortam proxy'si reddi ya da beklenmeyen HTML = engel → yeniden denenmez, aşılmaz.
- 5xx ve zaman aşımı: bir yeniden deneme (3 sn sonra).
- Her yanıtta: `kaynak, url, erisim_utc, erisim_tr, http_durumu, icerik_turu, bayt, sha256, onbellekten, deneme, sure_sn`.

## kaynaklar/
- `clubelo.py`: gün ve kulüp CSV'leri → `elo` kanıtı (ölçüm dönemi = From–To). ClubElo tahminleri okunmaz.
- `footballdata.py`: ana (`mmz4281/<sezon>/<lig>.csv`) ve ek (`new/<ülke>.csv`) biçimleri; yalnızca beyaz listedeki
  maç istatistiği sütunları alınır, bütün oran sütunları atılır ve yalnızca sayılır.
- İkisinin biçimi gerçek veriyle doğrulanana kadar `DOGRULANMIS_BICIM = False`; beklenmeyen biçim `BicimHatasi` verir.
