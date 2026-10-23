# Kino bot

## O'rnatish

```bash
cd /root/kino_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` faylini ochib, `BOT_TOKEN=` ga BotFather'dan olingan yangi tokenni yozing.
`ADMIN_IDS` allaqachon `8744554062` ga o'rnatilgan.

## Ishga tushirish

```bash
python bot.py
```

## Muhim

- Majburiy obuna kanallarida bot **admin** bo'lishi shart, aks holda a'zolikni tekshira olmaydi.
- Kino videolari Telegram serverida `file_id` orqali saqlanadi, shuning uchun bot video faylini o'zida saqlamaydi.
- Ma'lumotlar `kino.db` (SQLite) faylida saqlanadi.

## Buyruqlar

Foydalanuvchi: kino kodini yuboradi.

Admin:
- `/add_movie`: video yuborib, kod va nom kiritish
- `/movies`: kinolar ro'yxati
- `/del_movie KOD`: kinoni o'chirish
- `/add_channel`: kanal qo'shish (forward yoki @username)
- `/channels`: kanallar ro'yxati va o'chirish
- `/cancel`: joriy amalni bekor qilish
