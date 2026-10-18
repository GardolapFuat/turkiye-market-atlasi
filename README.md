# Türkiye Market Atlası

Türkiye genelinde **A101, BİM, ŞOK ve Migros/MJet** mağazalarını gezilebilir pinlerle inceleyen, tarayıcıda çalışan bir harita. Özellikle küçük yerleşimleri keşfetmek için marka, il, bölge ve yerleşim yakınlığı filtreleri sunar.

**[Haritayı aç](https://gardolapfuat.github.io/turkiye-market-atlasi/)** · [Kaynaklar ve veri sınırları](DATA_SOURCES.md) · [Eksik mağaza bildir](https://github.com/GardolapFuat/turkiye-market-atlasi/issues/new?template=missing-store.yml)

## Kapsam

17 Ekim anlık görüntüsü üzerine 18 Ekim 2026 altı il güncellemesi: **81 il, 7 bölge ve 23.320 kaynaklı konum kaydı.** Açılış görünümü yalnızca Balıkesir, Çanakkale, İzmir, Muğla, Aydın ve Bursa’yı gösterir. Diğer illerde veri genişletilmedi.

| Marka | Pin | Kaynak |
|---|---:|---|
| A101 | 5.106 | Kısmi resmî konum verisi + OpenStreetMap + altı ilde ek dizin |
| BİM | 3.838 | OpenStreetMap + altı ilde ek dizin; eksik kapsam |
| ŞOK | 11.042 | Resmî mağaza bulucu koordinatları |
| Migros/MJet | 3.334 | Resmî mağaza bulucu koordinatları |

**Bu sayılar zincirlerin toplam şube sayısı değildir. Pin görünmemesi mağaza olmadığı anlamına gelmez.** A101 ve BİM kapsamı özellikle eksik olabilir. Kaynak koordinatı, bağımsız saha doğrulaması anlamına gelmez. Her mağazanın kartında kaynak türü ve doğrudan kaynak bağlantısı bulunur.

Karabiga örneği üzerine A101’in resmî konum servisi de araştırıldı. Kaynak servisten 451 benzersiz kayıt alınabildi; erişim reddi (HTTP 403) görüldüğünde toplama durduruldu. Ulusal taramanın tamamlandığı iddia edilmez. Karabiga mağazası `a101-I274` resmî kaydıyla haritadadır. Tamamlanan resmî sorgular ve OSM verileri il poligonuyla süzülüp olası mükerrerler çıkarıldığı için uygulama sayıları ham kaynak sayılarından farklıdır.

## Altı ilde kapsam genişletme · 18 Ekim 2026

Yalnızca **Balıkesir, Çanakkale, İzmir, Muğla, Aydın ve Bursa** için A101/BİM kaynak karşılaştırması yapıldı. [En Yakın Şubesi](https://enyakinsubesi.com) dizininin 12 herkese açık il sayfasında 3.589 koordinatlı kayıt bulundu; 491 koordinatsız kayıt pine çevrilmedi. Kaynak, A101 listesini resmî listeden derlediğini belirtir; bu proje bu kaynağı **doğrudan resmî veri veya bağımsız saha doğrulaması olarak sunmaz**. Google Maps/Places toplu verisi kullanılmaz.

Sonuç: **2.135 ek dizin pini**, 1.272 mevcut konumla kaynak eşleşmesi; 182 kayıt olası mükerrer veya il sınırı uyuşmazlığı nedeniyle eklenmedi. Aynı markanın 70 m içindeki kayıtları mevcut pinle eşleştirilir; 70–180 m arası kayıtlar incelemeye ayrılır. Bu eşikler hata ve mükerrer olasılığını tamamen kaldırmaz. Eski kaynaklar güncel olmayan mağazalar içerebilir.

| İl | Eklenen A101 | Eklenen BİM | Toplam ek pin |
|---|---:|---:|---:|
| Balıkesir | 142 | 95 | 237 |
| Çanakkale | 16 | 15 | 31 |
| İzmir | 564 | 289 | 853 |
| Muğla | 140 | 59 | 199 |
| Aydın | 148 | 68 | 216 |
| Bursa | 424 | 175 | 599 |

Selimiye/Milas A101, kaynakta yayımlanan **37.399960, 27.654283** koordinatıyla eklendi. Kullanıcının gösterdiği Google Maps işletme konumuyla yaklaşık 15 metre fark vardır; kaynak adresi Google kaydındaki kapı numarasından farklıdır. Pin kartı dizin adresini ve kaynak türünü korur; resmî doğrulanmış adres iddia edilmez.

- [Altı ilin mağaza tablosu](docs/focus-markets.csv)
- [Yerleşimlere göre mağaza ve marka listesi](docs/focus-localities.csv): OSM köy/kasaba/mezra merkezlerinin 2 km çevresindeki kayıtlar; resmî idari sınıflandırma veya gelişim puanı değildir.
- [Karşılaştırma ve incelemeye ayrılan kayıtlar](data/focus-report.json)
- [Kaynak anlık görüntüsü](data/focus-source-snapshot.json)

Kaynağı yeniden almak isteğe bağlıdır: `python scripts/collect_focus.py`. Toplayıcı yalnızca 12 açık il sayfasını okur; `/api/`, arama uç noktaları veya hesap kullanılmaz. 403/429 halinde durur. Normal veri yenileme kayıtlı anlık görüntüyü kullanır; diğer iller bu çalışma kapsamında taranmaz.

## Kullanım

- Yakınlaştırınca kümeler mağaza pinlerine ayrılır. Bir pine veya sol listedeki mağazaya tıklayın.
- Marka kutularıyla katmanları açıp kapatın; il ve bölge seçin; yerleşim veya adres arayın.
- **Köy/kasaba kayıtlarına yakın noktalar**, OSM `village/town/hamlet` merkezlerinin 2 km çevresini gösterir. Bu filtre bugünkü resmî köy statüsü veya nüfus filtresi değildir.
- **Görünümü paylaş**, mevcut harita alanını ve filtreleri bağlantıya ekler.
- JSON ve CSV dışa aktarma, uygulamadaki **Kaynaklar ve kapsam** bölümündedir.

Pin verisi önceden hazırlanmıştır; normal kullanım sırasında Overpass veya mağaza servislerine canlı sorgu yapılmaz. Harita ve isteğe bağlı uydu tabanı internet bağlantısı gerektirir. Hesap, API anahtarı veya ücretli harita API’si gerekmez.

## Yerelde çalıştırma

Bu depo paket kurulumu ve derleme gerektirmez. `docs/index.html` dosyasını tarayıcıda açın veya Python 3.10+ ile:

```sh
python -m http.server 8080 --directory docs
```

Ardından `http://localhost:8080` adresini açın.

## Veriyi yeniden hazırlama

Toplayıcılar Python standart kütüphanesini kullanır. Ağ istekleri yalnızca açık kaynak uç noktalarına yapılır; hesap çerezi veya gizli anahtar kullanılmaz.

```sh
python scripts/update_data.py --repo-url https://github.com/GardolapFuat/turkiye-market-atlasi
python scripts/validate.py
```

Ham yanıtlar ve ara dosyalar `.cache/` altında kalır ve Git’e eklenmez. Güncelleme sırasıyla resmî ŞOK/Migros verisini, OSM mağaza/yerleşim verisini ve coğrafi referansları alır; hatalı yanıtla eski verinin üstüne boş harita yazmaz. Kaynak servislerin hızı ve erişilebilirliği değişebilir. Hata veya HTTP 403 durumunda erişim kontrolünü aşmaya çalışmayın.

A101’in kısmi resmî anlık görüntüsü `data/a101-source-snapshot.json` içindedir; varsayılan güncelleme büyük bir A101 taramasını yeniden başlatmaz. `scripts/collect_a101.py` araştırma amaçlı isteğe bağlı toplayıcıdır ve ilk HTTP 403 yanıtında durur. Kaynak kapsamı ve son kontrol tarihleri korunur.

Sadece mevcut önbellekten yeniden oluşturmak için:

```sh
python scripts/build_data.py --repo-url https://github.com/GardolapFuat/turkiye-market-atlasi
```

## Yayınlama

Statik sunucuya `docs/` içeriği yüklenebilir. GitHub Pages için bu depoda **Settings → Pages → Source → GitHub Actions** seçin; `Publish map` iş akışı `docs/` içeriğini yayınlar. Veri toplama kendiliğinden zamanlanmaz; güncellediğiniz çıktıları inceleyip commit etmeniz gerekir.

## Katkı ve lisans

[Katkı rehberi](CONTRIBUTING.md) kaynak bağlantısı olan eksik/hatalı mağaza bildirimlerini açıklar. Tahminî koordinatlı düzeltmeler kabul edilmemelidir.

Uygulama ve özgün toplayıcı kodu [MIT](LICENSE) lisanslıdır. Üçüncü taraf veriler ve kütüphaneler kendi koşullarına tabidir; [DATA_SOURCES.md](DATA_SOURCES.md) ve [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) dosyalarını inceleyin. Proje market zincirleriyle bağlantılı değildir.
