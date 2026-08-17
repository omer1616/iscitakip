# İşçi Dosya Takip Paneli

Django Admin ve Django Unfold üzerinde çalışan, işçi dosyaları için rol bazlı ve dinamik süreç takip uygulaması.

## Özellikler

- İşçi, karşı taraf, sorumlu avukat ve dosya bilgilerinin ayrı ve ilişkisel yönetimi
- Yönetilebilir süreç aşamaları ve izin verilen aşama geçişleri
- Her aşama değişikliğinde kullanıcı, zaman ve açıklama içeren salt okunur geçmiş
- Avukatların varsayılan olarak yalnızca kendilerine atanan dosyaları görmesi
- Finansal bilgileri görüntüleme ve değiştirme için birbirinden ayrı izinler
- Dosya içinden not ve belge ekleme
- Unfold dashboard, renkli durum göstergeleri, filtreler ve Kanban görünümü
- Başlangıç workflow'u ve tekrar çalıştırılabilir rol kurulum komutu

## Yerel kurulum

Proje güncel Django Unfold sürümü nedeniyle Python 3.12 veya üstünü gerektirir.

```bash
cd /Users/omer/worker_case_tracker
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_roles
python manage.py createsuperuser
python manage.py runserver
```

Ardından `http://127.0.0.1:8000/admin/` adresini açın.

## ngrok ile geçici paylaşım

Geliştirme ayarları `*.ngrok-free.app` ve `*.ngrok-free.dev` alan adlarını kabul eder. ngrok hesabınızı bir kez bağladıktan sonra:

```bash
ngrok config add-authtoken YOUR_TOKEN
ngrok http 8000
```

Ngrok'un gösterdiği HTTPS adresinin sonuna `/admin/` ekleyin. Bu adres bilgisayarınızdaki geliştirme sunucusuna doğrudan erişim verdiğinden yalnızca gerektiği süre boyunca açık bırakın ve güçlü bir admin parolası kullanın.

## Roller

- **Avukat:** Dosya/işçi/taraf/not/belge işlemleri ve aşama değiştirme. Dosya listesi kendisine atanmış kayıtlarla sınırlıdır.
- **Finans Yetkilisi:** Finansal alanları görme ve değiştirme. Genellikle Avukat rolüyle birlikte atanır.
- **Dosya Yöneticisi:** Tüm avukatların dosyalarını ve finansal alanları görür; dosya süreçlerini yönetir.
- **Superuser:** Aşama ve geçiş tanımları dahil bütün yönetim alanlarına erişir.

Standart Django grup izinleri üzerinden roller daha ayrıntılı biçimde özelleştirilebilir. `Finans Yetkilisi` grubundan `change_financial_data` izni kaldırılırsa kullanıcı finansal alanları görür ama değiştiremez.

## Workflow davranışı

İlk migration sekiz örnek aşamayı ve ardışık geçişleri oluşturur. Yönetici **Süreç Aşamaları** ekranından yeni aşama ekleyebilir, sıralayabilir, renklendirebilir veya pasife alabilir. **Süreç Geçişleri** ekranı hangi aşamadan hangisine gidilebildiğini belirler. Sistemde hiç geçiş kuralı yoksa tüm aktif aşamalar seçilebilir.

## Testler

```bash
python manage.py test
python manage.py check
```

Üretimde `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS` ve veritabanı ayarlarını ortam değişkenleriyle yapılandırın; ayrıca medya dosyalarını özel/depolama yetkileri kontrollü bir servis üzerinden sunun.
