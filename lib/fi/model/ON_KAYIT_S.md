# S aşaması — tarihsel sürpriz ve piyasa sinyalleri PİLOT (10 sürpriz + 10 kontrol) ön kaydı (26.11.2026)

Bu set, J'nin 30+30 setinden (output/arastirma/set_v1) AYRIDIR; ortak maçlar "tekrar" olarak işaretlenir. Sonuçlar
KEŞİFSELDİR; ileriye dönük başarı kanıtı değildir.

## Evren ve bağımsız favori (A sütunu)
- Ligler: en.1, es.1, de.1, it.1, fr.1 — sezonlar 2022-23…2025-26. Model: GolModeli Poisson (ξ 0,003, pencere 1095,
  ceza 2,0, önsel 0,8/1,2), yürüyen test; maç öncesi olasılık. Kalibrasyon: E aşamasında Poisson 1X2 havuz ECE ≈ 0,016;
  bu liglerde lig bazında ileriye dönük doğrulanmadı → olasılıklar yalnızca KATEGORİ olarak kullanılır.
- UEFA Şampiyonlar Ligi 2024-25: ligler_arasi M1 (ortak Elo, sıralı lojistik geçmiş sezonlardan). M1'in büyük-5 farkını
  eksik verdiği biliniyor (D aşaması) → kategori yalnızca analiz amaçlı.
- Favori: max(P(ev kazanır), P(dep kazanır)) ≥ 0,50 olan taraf. Kategoriler: 50–60, 60–70, 70–80, ≥ 80.
- Sürpriz (A): favori kazanamadı; "kaybetti" ve "berabere" ayrı etiket.

## Seçim (sonuç dışında hiçbir maç bilgisine bakılmadan; haber araştırmasından önce donduruldu)
- Tohum = bu dosyanın SHA-256'sının ilk 16 hex hanesi (tamsayı). random.Random(tohum).
- Kota (10 sürpriz): 50–60: 2 · 60–70: 3 · 70–80: 3 · ≥80: 2. Her kategori içinde sürpriz havuzundan (lig + UCL birlikte)
  tarih+ev sırasına dizilmiş adaylardan rastgele seçim; aynı favori takım bir kez. Kategori havuzu yetmezse bir alt
  kategoriden tamamlanır ve raporlanır.
- Kontrol (her sürpriz için 1): aynı yarışma ve sezon, aynı favori saha durumu, favori KAZANDI, |P farkı| en küçük,
  favori takım farklıysa tercih; kullanılmış maç tekrar kullanılmaz.
- Kullanıcının adını verdiği örnekler (Real Madrid–Sheriff 2021, Lille–Real Madrid 2024, Bournemouth–Man City 2024,
  Arjantin–Suudi Arabistan 2022) seçime GİRMEZ; ayrı "kullanıcı örnekleri" ekinde veri kapsamıyla raporlanır.

## Piyasa sütunu (B) — MK-1
Kapanış 1X2 (marj ayrıştırılmış) yalnızca izinli ve kaynaklı veri varsa; yoksa "piyasa verisi eksik". Basında aktarılan
fiyat varsa kaynak, tarih ve saatle "basın aktarımı" olarak ayrı yazılır; açılış–kapanış hareketi ancak iki zaman damgalı
fiyat varsa. Oranlar hiçbir model girdisine, etikete ya da kalibrasyona girmez.

## Haber ve neden-sonuç
Her maç: (A) maç öncesi doğrulanmış riskler (yayın zamanı maç öncesi), (B) maç içi gelişmeler, (C) maç sonrası
açıklamalar. Yalnızca A sinyal sayılır. Her aday sinyal için sürpriz/kontrol sıklığı, yanlış alarm, belirsizlik, kaynak
kalitesi ve bilinebilirlik raporlanır. Bulgular ileriye dönük test hipotezi olarak yazılır (ON_KAYIT_J/J_EK ile uyumlu).
