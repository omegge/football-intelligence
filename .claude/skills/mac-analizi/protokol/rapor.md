# Rapor biçimleri (sohbette sunulur)

Footy-Skills `football-match-lite/template.md` kurallarından korunanlar:
- Her istatistik takımını aynı cümlede adlandırır.
- Alıntılanan her geçmiş sonuç rakip, tarih, o takımın tarafından skor ve iç saha/deplasman bilgisini verir.
- Kaynakta olmayan türetilmiş her sayı hesabıyla yazılır (`python3 -c` ile hesaplanır).
- Beraberliği galibiyet ya da yenilgi diye anlatma; bir istatistiği diğer takıma taşıma.

## A. Aday (bülten taraması sonrası, her ilginç seçenek için)
```
### {Ev} - {Deplasman} · {lig} · {gg.aa SS:DD TR} · Nesine {kod}
Seçenek: {market} — {seçenek} @ {oran}  (bülten {klasör}, {N} dk önce çekildi)
Neden araştırmaya değer: {hangi sportif soru; oran düzeyi tek başına gerekçe değildir}
Asıl soru: destekleyen somut kanıtlar / karşıt kanıtlar (ikisi de kaynaklı ve tarihli)
Destekleyen doğrulanmış bulgular: {kaynak, tarih; doğrulama seviyesi}
Kadro / takım haberleri: {resmi / iki bağımsız / doğrulanmadı / çelişkili}
Taktik gerekçe: {eşleşme; vekil göstergeler etiketli}
Diğer siteler ve analistler: {beklenti + gerekçe; yüzdeleri karantinada}
Benzer tarihsel sürprizler: {pilottan; "kanıtlanmış tahmin gücü değildir"}
Karşıt kanıtlar ve en büyük riskler: {…}
Olayın olasılığı (yalnızca bağımsız model): {donmuş model p (SHA) | "hesaplanamaz: neden"}
Fiyatın cazibesi (ayrı değerlendirme): {başabaş eşiği; modelle fark ya da yalnızca nitel; oran düzeyi tek başına gerekçe değildir}
Fiyat karşılaştırması (isteğe bağlı): {yalnızca kalibre bağımsız olasılık varsa; başabaş, EV, ayrışma etiketi ve belirsizlik | "geçerli model yok: fiyat değerlendirmesi yapılmadı"}
Sonuç: güçlü araştırma adayı | daha fazla doğrulama gerekli | pas geç
Araştırma kapsamı: {yapılan arama sayısı, okunan kaynak türleri, bulunamayanlar}
```

## B. Derin maç raporu
1. Başlık: maç, lig, saat (TR), Nesine kodu, bülten klasörü ve yaşı.
2. **Bağımsız model:** durum (donmuş, SHA, model, veri kesimi) ve kalibre marketlerin olasılıkları. Diğer marketler "hesaplanamaz".
3. **Simetrik mercek tablosu** (Footy lenses):

   | mercek | Ev | Deplasman | kimin lehine |
   |---|---|---|---|
   - Mercekler: şans–performans, hücum, savunma, stil, rakip kalitesi, hedefler, fikstür/yorgunluk, kadro, ortam.
4. **Son 5–10 maç:** iki takım; rakip gücüyle birlikte (puan/maç, gol farkı).
5. **Uzman notları:** 5 not, her biri yön, güç ve güven ile.
6. **Haberler:** doğrulanmış / doğrulanmamış / çelişkili. Her birinde yayın zamanı ve kaynak sınıfı.
7. **Analistler ve tahmin siteleri:** beklenti + gerekçe. Yüzdeler karantinada.
8. **Konsey:** 7 savunucu; her biri güç ve en önemli risk ile.
9. **En önemli sürpriz sinyali:** tek cümle, kanıtı ve karşı kanıtıyla.
10. **Özel marketler** (yalnızca dondurmadan sonra, oranlarla): ilginç olanlar, her biri "model kapsamında: p" ya da "hesaplanamaz: nitel gerekçe".
11. **Fiyat karşılaştırması:** `karsilastir` tablosu ve eşdeğer marketlerde en yüksek fiyat.
12. **Belirsizlikler ve araştırma kapsamı:** bulunamayanlar, tek kaynaklı iddialar, sayfası okunamayan kaynaklar.
