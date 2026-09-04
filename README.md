# YolGuard AI

**YolGuard AI**, klasik navigasyon uygulaması değil; rota öncesi karar destek uygulamasıdır. Başlangıç ve varış adresine göre rota süresi/mesafesi, hava durumu, güneş kamaşması, araç tipi, sürücü tecrübesi, yolcu profili ve masraf varsayımlarını birlikte değerlendirir. Sonuçta 0–100 arasında risk skoru, en uygun çıkış saati, hazırlık listesi ve yapay zekâ destekli yolculuk raporu üretir.

## 1. Proje kapsamı

Uygulama şunları yapar:

- Başlangıç ve varış adresini koordinata çevirir.
- Rota mesafesi ve tahmini süre hesaplar.
- Seçilen çıkış saatlerini tek tek karşılaştırır.
- Rota orta noktasındaki saatlik hava tahminini alır.
- Güneşin rota yönüne göre sürücüyü rahatsız etme riskini hesaplar.
- Araç türü, sürücü tecrübesi, bebek/çocuk/evcil hayvan gibi değişkenleri hesaba katar.
- Elektrikli araç seçilirse menzil riskini hesaba katar.
- Yaklaşık yakıt/enerji, yemek ve konaklama maliyeti hesaplar.
- Risk bileşenlerini grafikle gösterir.
- Harita üzerinde rotayı gösterir.
- Sonucu CSV'ye kaydeder.
- İstenirse Google Sheets'e de kaydedebilir.
- Gemini API anahtarı verilirse AI raporu üretir; anahtar yoksa yerel şablonlu rapor üretir.

## 2. Kullanılan servisler

Bu proje mümkün olduğunca ücretsiz/anahtarsız kaynaklarla çalışacak şekilde tasarlandı:

- **Nominatim / OpenStreetMap:** adres → koordinat
- **OSRM public demo server:** sürüş rotası, mesafe ve süre
- **Open‑Meteo:** saatlik hava tahmini
- **Astral:** güneş azimutu ve yükseklik açısı
- **Gemini API:** opsiyonel yapay zekâ raporu
- **Google Sheets:** opsiyonel kayıt entegrasyonu

> Not: Nominatim ve OSRM kamu servisleri yoğun/ticari kullanım için uygun değildir. Ödev demosu için yeterlidir. Gerçek ürünleşmede Google Maps Platform, OpenRouteService veya self-host OSRM daha doğru olur.

## 3. Klasör yapısı

```text
YolGuardAI/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .streamlit/
│   └── config.toml
├── data/
│   └── demo_roadworks.csv
├── docs/
│   └── teslim_dokumani_taslak.md
├── modules/
│   ├── ai_advisor.py
│   ├── checklist.py
│   ├── config.py
│   ├── expenses.py
│   ├── geocoding.py
│   ├── risk_model.py
│   ├── roadworks.py
│   ├── routing.py
│   ├── sheets_logger.py
│   ├── sun.py
│   ├── utils.py
│   └── weather.py
└── tests/
    └── test_risk_model.py
```

## 4. Kurulum - VS Code

### 4.1. Projeyi açın

1. ZIP dosyasını çıkarın.
2. VS Code'u açın.
3. **File > Open Folder** yoluyla `YolGuardAI` klasörünü seçin.

### 4.2. Terminal açın

VS Code içinde:

```bash
Terminal > New Terminal
```

### 4.3. Sanal ortam oluşturun

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows'ta izin hatası alırsanız PowerShell'i yönetici olarak açmadan şu komut yardımcı olabilir:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 4.4. Paketleri yükleyin

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.5. Ortam değişkenlerini hazırlayın

`.env.example` dosyasını kopyalayıp `.env` yapın.

macOS / Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
copy .env.example .env
```

Gemini kullanmayacaksanız `.env` dosyasını boş bırakabilirsiniz. Uygulama yine çalışır.

### 4.6. Uygulamayı çalıştırın

```bash
streamlit run app.py
```

Tarayıcıda genelde şu adres açılır:

```text
http://localhost:8501
```

## 5. Kurulum - PyCharm

1. PyCharm'ı açın.
2. **Open** ile `YolGuardAI` klasörünü seçin.
3. Sağ alt veya ayarlar kısmından Python interpreter seçin.
4. Yeni sanal ortam oluşturun: `.venv`.
5. PyCharm terminalinde şunu çalıştırın:

```bash
pip install -r requirements.txt
```

6. Terminalden uygulamayı başlatın:

```bash
streamlit run app.py
```

PyCharm'da doğrudan `Run app.py` yapmak yerine terminalden `streamlit run app.py` çalıştırmak gerekir. Çünkü Streamlit uygulamaları normal Python script gibi başlatılmaz.

## 6. Gemini API ayarı

Gemini API zorunlu değildir. Ama yapay zekâ entegrasyonunu göstermek için önerilir.

1. Google AI Studio üzerinden API key alın.
2. `.env` dosyasında şu satırı doldurun:

```env
GEMINI_API_KEY=buraya_api_key_yazin
GEMINI_MODEL=gemini-2.5-flash
```

3. Uygulamayı yeniden başlatın:

```bash
streamlit run app.py
```

API anahtarı yoksa uygulama şablonlu rapor üretir. Bu sayede demo günü anahtar sorunu olsa bile proje çalışır.

## 7. Google Sheets entegrasyonu

Bu bölüm opsiyoneldir. Ödev metninde “mümkünse Google Sheets entegrasyonu” dendiği için uygulamada destek vardır.

Genel adımlar:

1. Google Cloud Console'dan bir proje oluşturun.
2. Google Sheets API ve Google Drive API'yi etkinleştirin.
3. Service Account oluşturun.
4. JSON anahtar dosyasını indirin.
5. JSON dosyasını proje klasörüne koyun. Örnek: `service_account.json`
6. `.env` dosyasına şunu yazın:

```env
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
GOOGLE_SHEET_NAME=YolGuardAI_Logs
```

7. Uygulamayı tekrar çalıştırın.

Uygulama analiz sonuçlarını hem yerel CSV'ye hem de Google Sheets'e kaydetmeye çalışır. Google Sheets ayarlanmazsa yerel CSV kaydı devam eder.

## 8. Test çalıştırma

Kurulumdan sonra:

```bash
pytest
```

Sadece syntax kontrolü için:

```bash
python -m py_compile app.py modules/*.py
```

## 9. Demo senaryosu

Örnek giriş:

- Başlangıç: `Gebze, Kocaeli`
- Varış: `Ağrı Merkez`
- Araç tipi: `Motosiklet`
- Sürücü tecrübesi: `Acemi`
- Toplam kişi sayısı: `1` veya risk testi için `4`
- Çıkış saatleri: `06:00, 08:00, 10:00, 12:00, 16:00`
- Günlük sürüş limiti: `6 saat`
- Yakıt fiyatı: `45 TL/L`
- Tüketim: `3.5 L/100 km`

Beklenen çıktı:

- En düşük riskli çıkış saati
- Risk skoru ve kategorisi
- Hava/güneş/araç/sürücü kaynaklı risk gerekçeleri
- Harita
- AI yolculuk raporu
- Hazırlık listesi
- Tahmini maliyet
- CSV / opsiyonel Sheets kaydı

## 10. Risk skoru mantığı

Toplam skor 0–100 aralığındadır. Temel bileşenler:

- Hava durumu: %25
- Rota/süre: %25
- Sürücü/araç profili: %35
- Güneş kamaşması: %10
- Elektrikli araç/ek faktör: %5
- Güvenlik/kapasite uyumu: Gerektiğinde minimum risk eşiği uygulayan kural tabanlı düzeltme

v6 sürümünde risk modeli daha katı hale getirilmiştir. Motosiklet için toplam 2 kişi, otomobil/elektrikli otomobil için toplam 5 kişi demo güvenlik kapasitesi kabul edilir. Kapasite aşımı, acemi motosiklet sürücüsüyle uzun rota, bebek/çocuk/evcil hayvan ile motosiklet kombinasyonu ve günlük sürüş limitinin ciddi aşılması durumlarında ağırlıklı ortalama tek başına kullanılmaz; minimum risk eşiği uygulanır.

Risk kategorileri:

- 0–34: Düşük
- 35–54: Orta
- 55–74: Yüksek
- 75–100: Çok yüksek

Model kesin güvenlik garantisi vermez; karar destek amacı taşır.

## 11. Sunumda nasıl anlatılır?

Kısa anlatım:

> YolGuard AI, kullanıcının yolculuk öncesi daha güvenli ve bilinçli karar verebilmesi için geliştirilmiş web tabanlı bir karar destek sistemidir. Uygulama, rota, hava durumu, güneş kamaşması, araç tipi, sürücü tecrübesi, yolcu profili ve masraf bilgilerini birlikte değerlendirerek risk skoru üretir. En uygun çıkış saatini önerir ve yapay zekâ destekli kişisel yolculuk raporu hazırlar.

Google Maps farkı:

> Google Maps çoğunlukla navigasyon ve rota süresi verir. YolGuard AI ise rota öncesi risk, hazırlık, güneş etkisi, sürücü profili, bebek/çocuk durumu ve maliyet gibi unsurları birleştirerek karar desteği sunar.

## 12. Sınırlılıklar

- OSRM demo server gerçek zamanlı trafik içermez.
- Demo yol çalışmaları CSV'den gelir; gerçek zamanlı resmi API değildir.
- Hava durumu tahmini kesinlik taşımaz.
- Risk skoru akademik/demo amaçlı ağırlıklandırma modelidir.
- Gerçek ürünleşmede güvenlik, veri doğrulama, resmi trafik/yol çalışması verileri ve profesyonel harita API'leri gerekir.

## 403 Forbidden / Nominatim adres çözümleme hatası

Nominatim kamu sunucusu bazen `403 Forbidden` döndürebilir. Bunun en yaygın nedeni, isteğin uygulamayı tanıtan uygun `User-Agent` başlığı taşımaması veya kamu servisi kullanım politikasına takılmasıdır. Bu sürümde geocoding modülü güncellendi: önce Nominatim denenir, hata alınırsa Komoot Photon yedek geocoder olarak kullanılır. Yine de `.env` dosyanıza kendi iletişim bilginizi içeren bir `NOMINATIM_USER_AGENT` yazmanız önerilir:

```env
NOMINATIM_USER_AGENT=YolGuardAI-StudentProject/1.0 (adiniz@ornek.com)
```

Uygulamayı yeniden başlatmadan `.env` değişikliği aktif olmaz.

## 11. Adres çözümleme hata notu

Nominatim bazen `403 Forbidden`, Photon ise bazı sorgularda `400 Bad Request` döndürebilir. Bu v3 sürümünde uygulama önce Türkiye şehir/ilçe adlarını yerel demo koordinat tabanından çözmeye çalışır. Bu yüzden `Gebze, Kocaeli`, `Ağrı Merkez`, `İzmir`, `Bahçeşehir` gibi demo sorguları dış servis engeline takılmadan çalışır.

Tam adres çözümlenemezse şu iki pratik yöntemden biri kullanılabilir:

1. Adresi şehir/ilçe düzeyinde yazın: `Gebze, Kocaeli`, `Bahçeşehir, İstanbul`, `Ağrı Merkez`.
2. Doğrudan koordinat girin: `40.8028, 29.4307`.

Bu uygulama navigasyon hassasiyeti değil, yolculuk öncesi risk ve karar destek demosu amaçladığı için şehir/ilçe merkezi koordinatları final gösterimi için yeterlidir.

## Streamlit grafik/Altair hatası hakkında

Bazı Python 3.14 + Streamlit + Altair kurulumlarında `st.bar_chart` çağrısı `unexpected keyword argument 'closed'` hatasına yol açabiliyor. Bu proje sürümünde risk bileşenleri grafiği Altair kullanmadan HTML/CSS bar görünümüyle çizildi. Bu nedenle ek bir grafik paketi kurmanız gerekmez.
