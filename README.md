# Webrepl
Bu çalışma, https://github.com/kost/webrepl-python çalışması düzenlenerek oluşturulmuştur.

Bu modül herhangi bir bağımlılık gerektirmez.
Linkteki daha gelişmiş bir modül; https://github.com/Carglglz/upydev , fakat bağımlılıkları mevcut.


### Kullanım
```
import webrepl

wr = Webrepl(host="192.168.1.38", password="123456")
wr.send("import os;os.listdir()")
wr.get_version()
```
Basitçe başka Thread'de çalıştırılabilir.
```
wr = Webrepl(host="192.168.1.38", password="123456")
wr.start_with_thread()

# Veri alışverişi şöyle yapılır;

# Veriyi gönderiyoruz ve bir kod döndürüyor bize
read_code = wr.send("os.listdir()")

# Arada cevapları kontrol ediyoruz. Bizim kodumuz cevapların içinde varsa,
if read_code in wr.messages:
  # Kodu ve cevabı alabiliyoruz
  code, resp = dev.messages.pop(i)

```

### Metodlar
* connect
* disconnect
* login
* send              -> Cevabı geri döndürür
* read
* get_version       -> (1, 3, 0) gibi... döndürür
* put_file          -> local_file: Bizdeki dosya yolu, remote_file: Karşıda oluşturulacak dosya
* put_file_content  -> file_content: Dosya içeriği, remote_file: Karşıda oluşturulacak dosya
* get_file_content  -> remote_file: Karşıdaki dosya
* get_file          -> remote_file: Karşıdaki dosya, local_file: Bizdeki oluşturulacak dosya
* listdir
* remove_file
* mkdir
* rmdir
* setup_files       -> Bağlantı kurulduğunda karşıya otomatik yüklenmesini istediğim dosyalar. Henüz dosyaları ayarlamadım
* reset
* baudrate          -> Henüz ayarlanmadı
