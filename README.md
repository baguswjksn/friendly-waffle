# sprite builder

Script Python untuk menggabungkan banyak gambar jadi satu sprite sheet, lalu membuat CSS untuk menampilkan tiap gambar dari sheet tersebut. Tidak perlu JavaScript.

Tekniknya sama dengan yang dipakai katalog McMaster-Carr. Semua gambar dimuat lewat satu request. Tiap elemen punya ukuran tetap dan hanya menampilkan potongan miliknya lewat `background-position`. Karena ukurannya sudah tetap sejak awal, halaman tidak bergeser saat gambar selesai dimuat.

## Kebutuhan

- Python 3.8 atau lebih baru
- Pillow: `pip install pillow`

## Mulai cepat

```
python sprite_builder.py glob --cell 576x324 --fit cover --quality 80
```

Sprite sheet (`sprite.webp`) ditulis ke folder tempat perintah dijalankan, yaitu root project. CSS dan cara pakai semua gambar tampil di terminal. Tempel CSS-nya ke `<style>` di halamanmu, lalu pakai `<span>` yang dibutuhkan. Hanya sheet yang ditulis ke disk. Tidak ada file CSS terpisah.

## Memanggil gambar

Tempel CSS dari terminal ke `<style>` di halaman (lihat [Output di terminal](#output-di-terminal)), lalu panggil gambarnya:

```html
<span class="spr spr-images3" role="img" aria-label="Deskripsi gambar"></span>
```

Mengatur ukuran:

```html
<span class="spr spr-images3" style="width:48px"></span>               <!-- lebar 48px, tinggi ikut -->
<span class="spr spr-images3" style="height:32px;width:auto"></span>   <!-- tinggi 32px, lebar ikut -->
<span class="spr spr-images3" aria-hidden="true"></span>               <!-- dekoratif -->
```

Isi `width` atau `height` saja, jangan keduanya dengan angka. Sisi yang lain otomatis mengikuti `aspect-ratio`. Kalau keduanya diisi angka, gambar jadi tidak proporsional.

Agar gambar selebar kolom teks:

```css
.figure .spr { display: block; width: 100%; }
```

Supaya sheet mulai diunduh lebih awal, tambahkan preload di `<head>` (tidak wajib):

```html
<link rel="preload" as="image" href="sprite.webp">
```

## Output di terminal

Setelah build, terminal menampilkan dua bagian:

```
== CSS: tempel ke <style> ==
.spr{display:inline-block;vertical-align:middle;max-width:100%;background-repeat:no-repeat}

.spr-images3,
.spr-images{background-image:url("sprite.webp")}

.spr-images3{width:576px;aspect-ratio:576/324;background-size:...;background-position:...}
.spr-images{width:576px;aspect-ratio:576/324;background-size:...;background-position:...}

== HTML: cara pakai (taruh sprite.webp satu folder dengan file HTML; ...) ==
<span class="spr spr-images3" role="img" aria-label="images3"></span>
<span class="spr spr-images" role="img" aria-label="images"></span>
```

## Opsi

Lihat juga `python sprite_builder.py -h`.

| Opsi | Default | Keterangan |
|---|---|---|
| `inputs` | | Folder dan/atau file gambar. Boleh lebih dari satu. Subfolder tidak ikut dipindai. |
| `--cell` | `96` | Ukuran sel tiap gambar dalam px, misalnya `96` atau `576x324`. |
| `--fit` | `contain` | `contain`: gambar dimuat utuh (tidak diperbesar). `cover`: crop bagian tengah sampai sel penuh. |
| `--quality` | `85` | Kualitas WebP, 1 sampai 100. `100` berarti lossless. |

## Cara kerja crop

Sheet berisi `n` gambar yang ditumpuk vertikal. Gambar ke-`i` (mulai dari 0) ada di `y = i × tinggi sel`. Tiap class mengatur dua nilai dalam persen:

```
background-size     = 100%  (n × 100)%
background-position = 0     (i / (n − 1) × 100)%
```

Contohnya, untuk 5 gambar posisinya 0%, 25%, 50%, 75%, dan 100%. Kedua nilai itu relatif terhadap ukuran elemen. Jadi saat `width` elemen diubah, sheet ikut membesar atau mengecil dengan perbandingan yang sama, dan potongannya tetap tepat di ukuran berapa pun.

## Masalah umum

| Gejala | Penyebab dan solusi |
|---|---|
| Gambar tidak muncul | Halaman belum memuat CSS sprite. Tempel CSS dari terminal ke `<style>`. |
| Gambar tidak muncul setelah CSS ditempel | File sheet tidak berada di folder yang sama dengan HTML. Pindahkan file sheet, atau ubah path di `url(...)`. |
| Gambar tidak muncul, CSS sudah ada | Nama class salah. Cek nama yang benar di output terminal. |
| Gambar berubah setelah build ulang | Build ulang menimpa `sprite.webp`. Kalau jumlah atau urutan gambar berubah, posisinya ikut berubah, jadi tempel ulang CSS-nya. |
| Ada garis tipis dari gambar tetangga di tepi gambar | Sheet tidak memakai jarak antar gambar. Di uji project ini tidak terlihat, bahkan saat diperkecil ke 300px. Kalau muncul, tampilkan gambar dengan ukuran yang lebih dekat ke `--cell`. |
| `[error] sheet ... melebihi batas WebP 16383px` | Tinggi sheet (jumlah gambar × tinggi sel) melewati batas format WebP. Kecilkan `--cell` atau kurangi jumlah gambar. |
| `[lewati] ...` | File rusak atau bukan gambar. File itu dilewati, gambar lain tetap diproses. |

## Batasan

- Semua gambar dimuat ke sel berukuran sama (`--cell`). Gambar dengan rasio berbeda diberi ruang kosong (`contain`) atau dipotong (`cover`).
- Tinggi sheet maksimal 16383px (batas WebP). Jadi jumlah gambar maksimal adalah 16383 dibagi tinggi sel, misalnya 25 gambar untuk sel 1152×648, 50 untuk 576×324, atau 170 untuk 96×96.
- GIF animasi: hanya frame pertama yang dipakai.
