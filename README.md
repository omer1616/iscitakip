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

## Docker ile canlıya alma

Kurulum Postgres + Gunicorn + WhiteNoise ile çalışır. Statik dosyalar imaj derlenirken toplanır; migration, rol kurulumu ve ilk superuser konteyner her açıldığında otomatik çalışır.

```bash
cd /Users/omer/worker_case_tracker
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # DJANGO_SECRET_KEY için
# .env dosyasını düzenleyin (SECRET_KEY, DB_PASSWORD, superuser bilgileri, alan adı)
docker compose up -d --build
docker compose logs -f web
```

Ardından `http://SUNUCU_ADRESI:8000/admin/` adresini açın ve `.env` dosyasındaki superuser bilgileriyle giriş yapın.

### .env içinde mutlaka değiştirilecekler

| Değişken | Açıklama |
| --- | --- |
| `DJANGO_SECRET_KEY` | Rastgele ve gizli olmalı |
| `DJANGO_ALLOWED_HOSTS` | Sunucunun alan adı / IP'si (virgülle ayrılır) |
| `DB_PASSWORD` | Postgres parolası |
| `DJANGO_SUPERUSER_USERNAME` / `_PASSWORD` | İlk yönetici hesabı |

`DJANGO_DEBUG=0` bırakın.

### HTTPS

`.env` içindeki `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SESSION_COOKIE_SECURE` ve `DJANGO_CSRF_COOKIE_SECURE` varsayılan olarak `0`'dır; çünkü compose uygulamayı doğrudan HTTP üzerinde 8000 portundan yayınlar. Önüne TLS sonlandıran bir reverse proxy (nginx, Caddy, Traefik) koyduğunuzda:

1. Bu üç değeri `1` yapın.
2. `DJANGO_CSRF_TRUSTED_ORIGINS=https://alanadiniz.com` ekleyin.
3. Proxy'nin `X-Forwarded-Proto` başlığını ilettiğinden emin olun.
4. Alan adı kalıcı olarak HTTPS'e geçtikten sonra `DJANGO_SECURE_HSTS_SECONDS=31536000` yapın.

Proxy yokken bunları `1` bırakırsanız tarayıcı sonsuz yönlendirme döngüsüne girer.

### Superuser

İlk superuser `ensure_superuser` komutu ile `.env` içindeki değerlerden oluşturulur ve komut idempotenttir: kullanıcı zaten varsa parolasına dokunmaz. Parolayı `.env`'deki değere göre sıfırlamak isterseniz `DJANGO_SUPERUSER_UPDATE_PASSWORD=1` yapıp konteyneri yeniden başlatın. Kullanıcı adı/parola boş bırakılırsa bu adım atlanır ve elle oluşturabilirsiniz:

```bash
docker compose exec web python manage.py createsuperuser
```

### Sık kullanılan komutlar

```bash
docker compose ps                                        # servis durumu
docker compose logs -f web                               # loglar
docker compose exec web python manage.py shell           # Django shell
docker compose exec web python manage.py setup_roles     # rolleri güncelle
docker compose down                                      # durdur (veriler kalır)
docker compose up -d --build                             # kod güncelledikten sonra
```

Veriler `postgres_data` (veritabanı) ve `media_data` (yüklenen belgeler) adlı Docker volume'larında tutulur; `docker compose down` bunları silmez. Yedek almak için:

```bash
docker compose exec db pg_dump -U worker worker_case_tracker > yedek.sql
```

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
