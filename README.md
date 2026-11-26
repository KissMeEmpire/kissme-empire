# KissMe Empire 2.0

Starter MVP: dark-gold Telegram Mini App, tap-to-earn, city/island/palace businesses, unlockable regions, upgrades, XP/levels, daily reward, RU/EN toggle, SQLite save data and Telegram initData validation.

## Render
Build command: `pip install -r requirements.txt`
Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`

Set `BOT_TOKEN` in Render Environment. Never paste it into chat or commit it to GitHub.
Optional: attach a persistent disk and set `DB_PATH=/var/data/kissme_empire.db` so SQLite data survives redeploys. Local Render filesystems may be ephemeral.

This is a playable MVP starter, not a finished commercial game. It does not yet include clans, PvP, anti-cheat throttling, payments, blockchain, or a complete story campaign. KME is an in-game points balance, not cryptocurrency. Back up the existing app/database before replacing a live deployment.
