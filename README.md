# Türkiye Market Atlası

Türkiye genelinde **A101, BİM, ŞOK ve Migros/MJet** mağazalarını gezilebilir pinlerle inceleyen, tarayıcıda çalışan bir harita. Özellikle küçük yerleşimleri keşfetmek için marka, il, bölge ve yerleşim yakınlığı filtreleri sunar.

**[Haritayı aç](https://gardolapfuat.github.io/turkiye-market-atlasi/)** · [Kaynaklar ve veri sınırları](DATA_SOURCES.md) · [Eksik mağaza bildir](https://github.com/GardolapFuat/turkiye-market-atlasi/issues/new?template=missing-store.yml)

## Kapsam

17 Ekim 2026 anlık görüntüsü: **81 il, 7 bölge ve 21.185 konum kaydı.**

| Marka | Pin | Kaynak |
|---|---:|---|
| A101 | 3.672 | Kısmi resmî konum verisi + OpenStreetMap |
| BİM | 3.137 | OpenStreetMap; eksik kapsam |
| ŞOK | 11.042 | Resmî mağaza bulucu koordinatları |
| Migros/MJet | 3.334 | Resmî mağaza bulucu koordinatları |

**Bu sayılar zincirlerin toplam şube sayısı değildir. Pin görünmemesi mağaza olmadığı anlamına gelmez.** A101 ve BİM kapsamı özellikle eksik olabilir. Kaynak koordinatı, bağımsız saha doğrulaması anlamına gelmez. Her mağazanın kartında kaynak türü ve doğrudan kaynak bağlantısı bulunur.

Karabiga örneği üzerine A101’in resmî konum servisi de araştırıldı. Kaynak servisten 451 benzersiz kayıt alınabildi; erişim reddi (HTTP 403) görüldüğünde toplama durduruldu. Ulusal taramanın tamamlandığı iddia edilmez. Karabiga mağazası `a101-I274` resmî kaydıyla haritadadır. Tamamlanan resmî sorgular ve OSM verileri il poligonuyla süzülüp olası mükerrerler çıkarıldığı için uygulama sayıları ham kaynak sayılarından farklıdır.

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
