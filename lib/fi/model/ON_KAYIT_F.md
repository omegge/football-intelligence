# F aşaması — önceden kayıt (değerlendirme çalıştırılmadan önce yazıldı, 26.11.2026)

Amaç: İlk yarı / ikinci yarı marketlerini GERÇEK devre skorlarıyla sınamak ve iki devre arasındaki bağımlılığın
"λ verildiğinde bağımsız devreler" varsayımıyla açıklanıp açıklanmadığını test etmek. Parametre ayarı YAPILMAZ.

## Veri
OpenFootball (CC0), ilk yarı skoru olan maçlar. Değerlendirme ligleri: **it.2, fr.2, en.3, en.4** (daha önce hiçbir
model değerlendirmesinde kullanılmadı; E aşamasının liglerinden ayrı). Dönem: 2019-07-01 sonrası. Sert tarih
tutarsızlığı olan sezonlar okunmaz. İlk yarı skoru eksik maçlar değerlendirme dışı; eksiklik oranı ve eksik/tam
maçların maç sonu gol ortalaması ayrıca raporlanır (seçilim yanlılığı kontrolü).

## Model (F0, tek model)
Maç λ'ları: E aşamasıyla aynı GolModeli (ξ 0,003, pencere 1095, ceza 2,0, önsel 0,8/1,2), Poisson görünümü (ρ = 0).
Devre payı: s_ev = Σ ev 1Y golü / Σ ev golü, s_dep aynı biçimde; ligde tahmin tarihinden ÖNCE oynanmış ve devre skoru
olan maçlardan (genişleyen pencere). λ_ev,1 = s_ev·λ_ev, λ_ev,2 = (1−s_ev)·λ_ev (deplasman aynı). Dört devre golü
λ verildiğinde bağımsız Poisson. Olaylar fi.pazar.esdegerlik olay tanımlarıyla birebir aynı (Nesine kodları).

## Taban
Aynı ligde tahmin tarihinden önceki devre skorlu maçlarda olay sıklığı.

## Marketler (Nesine kodu)
7 (1Y sonucu), 9 (2Y sonucu), 209/14/15 (1Y 0,5/1,5/2,5 AÜ), 452 (1Y KG), 599 (2Y KG), 801 (1Y/2Y KG dört seçenek),
5 (İY/MS dokuz seçenek), 48 (en çok gol olacak yarı), 295/296 (takım iki yarıda da gol), 528/529 (iki yarı 1,5 alt/üst),
584/585 (herhangi bir yarıyı kazanır), 591/592 (iki yarıyı da kazanır), 586/587 (takımın daha çok gol attığı yarı),
455/457 (takım 1Y 0,5 AÜ), 779 (1Y skoru: 0:0, 1:0, 0:1, 1:1).

## Karar kuralları
- F1 marjinal devre marketleri (7, 9, 209, 14, 452, 599, 455, 457, 779): E1/E2 ile aynı ("bilgi taşıyor", "kalibre").
- F2 bağımlılık testi: birleşik marketler (801, 5, 48, 295, 296, 528, 529, 584, 585, 591, 592, 586, 587) için
  ortalama (gerçekleşen − tahmin) farkı tarih kümeli bootstrap %95 GA ile. GA 0'ı dışlarsa "devre bağımsızlığı
  reddedildi" → o seçenek için üretimde OLASILIK VERİLMEZ (hesaplanamaz); yalnızca marjinallerden Fréchet sınırları
  [max(0, p1+p2−1), min(p1, p2)] gösterilebilir. Ayrıca veride 1Y KG ile 2Y KG arasındaki gözlenen olasılık oranı
  (odds ratio) ile modelin ima ettiği oran karşılaştırılır.
- Olay sıklığı < %2 ya da > %98 olan seçenekte karar verilmez.
- MK-1: bahis oranı yok.
