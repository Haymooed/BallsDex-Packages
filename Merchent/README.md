# 🛍️ Merchant – BallsDex Package

The **Merchant** package adds a rotating in-game shop to your BallsDex bot.  
Players can earn and spend tokens to purchase rare, time-limited Balls from a curated selection that refreshes daily.

This package is designed to be fully modular, configurable, and ready to plug into any BallsDex project, including custom forks like **MarketDex**, **FruitDex**, or others.

---

## ✨ Features

- 🪙 **Daily Token System** — Players can claim daily tokens to spend in the shop.  
- 🏪 **Rotating Merchant Shop** — 5 random Balls appear every 24 hours.  
- 💸 **Dynamic Pricing** — Prices scale with rarity (T5 costs more, T200 costs less).  
- 👑 **Admin Controls** — Admins can grant tokens manually with `/merchant give`.  
- ⚙️ **Fully Configurable** — Modify rarity limits, admin roles, and currency name in `config.toml`.

---

## ⚙️ Setup

1. **Drop the package** into your BallsDex bot directory:
ballsdex/packages/merchant/

2. **Ensure these two files exist:**
- `cog.py` — the core merchant logic.
- `__init__.py` — registers the cog.
- `config.toml` — your shop and currency settings.

3. **Add this to `config.toml`:**
```toml
# Currency used for purchases
currency_name = "Market Tokens"

# Minimum & maximum rarity allowed in the daily shop
min_rarity = 1
max_rarity = 200

# Role IDs allowed to use /merchant give and /merchant refresh
admin_roles = [
    123456789012345678
]

# Channel ID where all purchases are logged
transaction_log_channel = 987654321098765432

```
---

### To improve/bugs
- Other people can interact with `/merchant view` and buy from your merchant
- Make embed smoother

***If you want to help please open a pull request***
