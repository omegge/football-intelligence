---
name: bulten-tara
description: Nesine bültenindeki bütün maçları tarayıp yüksek oranlı ama sportif gerekçesi araştırılabilecek adayları, favorinin zorlanabileceği maçları ve beklenen senaryoya uyan yüksek fiyatlı özel marketleri önceliklendirir; en ilginç adayları kısa web araştırmasıyla eler ve sohbette aday biçiminde raporlar. Kullanıcı "bültenden yüksek oranlı gerekçeli ihtimalleri bul", "bütün maçları tara", "favorilerin zorlanabileceği maçları araştır", "yüksek fiyatlı özel marketleri bul" dediğinde kullan.
---

# Bülten taraması → aday seçimi → derin inceleme

**Asıl soru (her analizde):** "Bu bahis sonucunun gerçekleşmesini destekleyen somut kanıtlar nelerdir, karşıt kanıtlar nelerdir ve bu ihtimal neden araştırmaya değerdir?" Amaç yüksek oranı haklı çıkarmak değil; iki yönü de araştırıp en güçlü gerekçeli seçenekleri bulmaktır. Nesine oranları şirket marjı içerir ve gerçek olasılık değildir. Oranlar yalnızca marketleri keşfetmek, piyasa görüşünü anlamak ve (geçerli model varsa) fiyat karşılaştırmak için kullanılır. EV ya da fiyat avantajı ZORUNLU değildir: yalnızca kalibre bir bağımsız olasılık varsa ve belirsizliğiyle birlikte gösterilir.

**Oran tarafsızlığı (kullanıcı kuralı):**
- Oran bir eleme ölçütü değildir; araştırma ve fiyat değerlendirmesi için bilgidir.
- Yüksek oran otomatik "riskli", düşük oran otomatik "güvenli" sayılmaz. 1,20'lik bir seçenek de kötü fiyatlanmış olabilir; 5,00 ya da 15,00'lik bir seçenek de gerçekçi olabilir.
- Favori sonuçları ve sürprizler aynı titizlikle incelenir. Yüksek oranlı seçenek sırf yüksek olduğu için elenmez, düşük oranlı seçenek sırf düşük olduğu için önerilmez.
- Olayın gerçekleşme olasılığı (yalnızca bağımsız model) ile fiyatın cazibesi AYRI değerlendirilir.
- Gerekçesi güçlü ama doğrulanmış olasılığı olmayan seçenekler de araştırma adayı olarak korunur, "hesaplanamaz" etiketiyle.
- Amaç: sportif kanıtla en iyi açıklanabilen ve fiyat açısından incelenmeye değer ihtimalleri bulmak.

**Temel ilke:** Oranın tek başına anlamı yoktur; ne yüksek ne düşük oran bir karar sebebidir.
- Bu tarama araştırılabilecek maç ve seçenekleri bulur.
- Favori ve sürpriz adayı oranla BELİRLENMEZ (MK-1). Favori yalnızca bağımsız modelden ya da bağımsız sezon verisinden belirlenir.
- Oranlar hiçbir modele girmez.

## Görev düzeni
CLAUDE.md "Araştırma görevi düzeni" önceliklidir: aday seçimi ve önceliklendirme kullanıcıya sorulmadan içeride yapılır; Türkiye ligleri varsayılan olarak hariç (kullanıcı isterse ayrı bölüm); Türkiye dışı en fazla 10 maç; yöntem CLAUDE.md "Araştırma yöntemi"; yalnızca nihai sonuçlar sunulur.

## 0. Kapsam (kullanıcı kuralı, 27.11)
- Bütün bülten ön taramadan geçer. Yalnızca modeli olan maçlara odaklanılmaz.
- Modeli olmayan maçlarda da haber, istatistik, sakatlık, taktik, yerel basın, tahmin siteleri, analistler, Reddit ve başka bahis sitelerinin oranları araştırılır.
- Varsayılan fiyat süzgeci YOK; yalnızca kullanıcı isterse uygulanır.
- Hem beklenmedik sürprizler hem de beklenen sonuçla uyumlu ama yüksek fiyatlı özel marketler incelenir.
- **Başka bahis sitelerinin oranları:** yalnızca piyasa görüşü. Kaynak, zaman ve site adıyla verilir; marj içerir; ASLA olasılık ya da model girdisi değildir. Bulunamazsa "veri yok".
- **Güncellik:** her bilginin yayın zamanı doğrulanır. Tarihsiz ya da eski sezon sonucu güncel bilgi gibi kullanılmaz (27.11 testinde arama sonuçlarının çoğu eski sezondandı).
- **Dil:** yerel kaynaklar ülkenin dilinde aranır: Almanca (Kicker, Bild, kulüp sitesi), İtalyanca (Gazzetta, Corriere dello Sport, TuttoMercatoWeb), İspanyolca (Marca, AS, Mundo Deportivo, yerel gazete), Fransızca (L'Équipe, Ouest-France, Le Parisien), Hollandaca (VI, Dagblad van het Noorden, Brabants Dagblad), Portekizce (Record, A Bola, O Jogo), Türkçe ve diğerleri. Aramada maçın TARİHİ ve takım adları birlikte kullanılır.
- **Hafıza:** önce `sohbet hafiza` ile aynı takımlar hakkındaki önceki araştırmalara bakılır (`output/arastirma/genis_pilot/`, `output/hafiza/`). Eski bulgu yeni gibi sunulmaz.

## 1. Bülten
- Bugünün ya da istenen günün başarılı bülteni yoksa ya da eskiyse önce `PYTHONPATH=lib python3 -m uygulama.sohbet bulten --gun YYYY-AA-GG` çalıştır.
- Bülten yaşını raporda HER ZAMAN göster.

## 2. Geniş tarama (bütün maçlar)
`tara --gun G --min-oran X --maks-oran Y [--market METİN] [--lig METİN] [--sinir N]`
- Varsayılan olarak fiyat süzgeci YOKTUR. Kullanıcı bir oran aralığı, market türü ya da lig isterse aynen uygulanır.
- Özel marketler için `--market` örnekleri: "Handikap", "İlk Yarı", "Korner", "Kart", "Kombine", "Skor", "Gol Atar", "Yarı".
- Tarama başlamış maçları ve oynanabilir olmayan seçenekleri dışarıda bırakır.

## 3. Önceliklendirme (oran sırası değil, araştırılabilirlik)
Puan verilir; puanın kaynağı oran değil, aşağıdakilerdir:
- (a) **Bağımsız model kapsamı:** `mac`'ta "hazırlanabilir" ise fiyat karşılaştırması mümkündür. En yüksek öncelik.
- (b) **Bağımsız veri:** football-data.org kapsamındaki lig (PL, ELC, BL1, SA, PD, FL1, DED, PPL, CL). Son 10 maç ve sezon gücü var.
- (c) **Haber bulunabilirliği:** büyük ve orta lig. Yerel basın erişilebilir.
- (d) **Sportif soru netliği:**
  - bağımsız favoride kilit eksik ya da yoğun fikstür;
  - rakibin form ve stil uyumu;
  - beklenen senaryoyla uyumlu özel market (ör. "favori kazanır ama ilk yarı berabere").

Önceliklendirmeyi açıkça yaz:
- 5–10 aday seç.
- Kısa liste: maç, seçenek, oran, neden.
- "Bağımsız verisi olmayan maçlar yalnızca nitel incelenir" diye belirt.

## 4. Hızlı eleme (aday başına 2–4 web araması)
Kadro haberi, form, teknik direktör ve önizleme gerekçeleri aranır. Doğrulanmış, doğrulanmamış ve çelişkili bulgular ayrılır. Sonuç: güçlü araştırma adayı / daha fazla doğrulama gerekli / pas geç.

## 5. Derin inceleme
En ilginç 1–3 aday için `mac-analizi` becerisini uygula:
- dondur;
- haber;
- uzmanlar;
- konsey;
- karşılaştır;
- marketler.

## 6. Rapor
Her aday için `.claude/skills/mac-analizi/protokol/rapor.md` A biçimi kullanılır. Raporun sonunda:
- araştırma kapsamı (taranan maç ve seçenek sayısı, web araması sayısı);
- incelenmeyen adaylar;
- "bu bir araştırma çıktısıdır; kupon değildir" notu.
