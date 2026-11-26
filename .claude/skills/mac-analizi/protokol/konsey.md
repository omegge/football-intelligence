# Savunucu konseyi ve karar verici (Footy-Skills konseyinin uyarlaması)

Kaynak: zetamins/Footy-Skills @ fdd4570 (`football-*-advocate`, `football-match-lite`). Özgün metinler: `../footy/orijinal/`.

## Ortak kurallar
- Her savunucu kendi tarafının **en güçlü DÜRÜST** davasını kurar. Kanıt uydurmaz, zayıflığı gizlemez, notlarda olmayan sayıyı kullanmaz.
- Olasılık ya da oran yazmaz. Diğer savunucuların metnini kullanmaz; her dava bağımsız kurulur.
- **İki geçiş:**
  - **Geçiş 1, sinyaller:** en güçlü 4–6 cümle, her biri kaynaklı bir bulguya dayanır.
  - **Geçiş 2, davayı batırabilecekler:** dürüst risk listesi.
- Çıktı: `taraf`, `güç 0-3`, `güven`, `sinyaller`, `riskler`.

## Yedi savunucu
1. **Ev sahibi:** Ev sahibi lehine hiçbir şeyin kaçmamasını sağlar; davayı neyin batırabileceğini açıkça söyler.
2. **Deplasman:** Ev sahibi savunucusunun simetriği.
3. **Beraberlik:** Beraberlikler nadiren tahmin edilir. Sinyaller:
   - iki takımın beklenen golü düşük (toplam yaklaşık 2,4'ün altında);
   - güçler yakın;
   - bir taraf için 1 puan yeterli;
   - iki takım da temkinli ya da düşük tempolu.
4. **Gol:** Kanıtın gösterdiği TEK yönü savunur (2,5 Üst, 2,5 Alt ya da KG Var). İki yönde de sinyal yoksa bunu söyler.
5. **Zayıf taraf:** Diğerlerinin atladığı soru: zayıf taraf bu savunmaya gol atabilir mi, atarsa sonra ne olur?
   - Favorinin savunma hataları (şuta ya da gole giden hata), ikili mücadele zaafları, bek arkası boşluklar, duran top, kalecinin kurtarış oranı.
   - Rakip gol attıktan sonra favorinin maçları nasıl gidiyor (galibiyet, beraberlik, yenilgi)?
6. **Oyun akışı:** Önde olan topu ve skoru korur, geride olan hücum eder; bu bir maçta birkaç kez yön değiştirir.
   - Sorular: ilk golü kim atar, önde olan skoru tutar mı, geride olan eşitler mi, skor el değiştirir mi?
   - Üçlü savunmayla hücum etmek savunmayı zayıflatır. Hataya açık bir savunma gol verir.
   - Bunlar eğilimdir, kesinlik değildir.
7. **Kaos:** Verinin göremediğini savunur: hatalar, kalecinin günü, penaltı, kırmızı kart, duran top.
   - Kaos nadirdir, kümelenir ve çoğunlukla öngörülemez. Yüksek "maruziyet" sayısı bir eğilimdir, tahmin değildir. **"DÜŞÜK KAOS" geçerli ve çoğu zaman doğru bir cevaptır.**
   - Bizim pilotumuzda 10 sürprizin 3'ünü maç içi olaylar belirledi (kırmızı kart, VAR); bunlar önceden bilinemezdi.

## Karar verici (football-match-lite "collection mode" uyarlaması)
- Uzman notlarını ve savunucu davalarını tartar; kabul edilen ve reddedilen gerekçeleri yazar.
- **SAYILAR yalnızca modelden gelir:** `python3 -m uygulama.sohbet dondur KOD`. Karar verici olasılığı değiştirmez, "düzeltilmiş xG" üretmez.
  - Model maçı ya da marketi kapsamıyorsa "hesaplanamaz" yazar.
  - Kapsamadığı yerde sayısal tahmin YOKTUR; yalnızca gerekçeli nitel değerlendirme vardır.
- **Footy'den farkı:**
  - Tek bahis zorunluluğu, "stake", "kupon" ve pazar skor tablosu YOKTUR.
  - Fiyat karşılaştırması yalnızca dondurmadan sonra `karsilastir` ile yapılır.
  - Pozitif EV avantaj değildir; "model–piyasa ayrışması · doğrulama gerekli" olarak etiketlenir.
- **Nihai etiket (adaylar için):** güçlü araştırma adayı / daha fazla doğrulama gerekli / pas geç. Bu etiket bir bahis önerisi değildir.
