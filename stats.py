from collections import defaultdict
from database import history
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def calculate_full_stats(user_id):
    trades = list(history.find({"user_id": user_id}).sort("timestamp", 1))

    if not trades:
        return "📊 У вас ещё не было сделок."

    total_trades = 0
    profitable = 0
    losing = 0
    breakeven = 0
    total_profit_pct = 0
    max_profit = float("-inf")
    max_loss = float("inf")

    symbol_stats = defaultdict(lambda: {
        "count": 0,
        "profitable": 0,
        "losing": 0,
        "breakeven": 0,
        "total_pct": 0
    })

    for trade in trades:
        entry = float(trade.get("entry", 0))
        exit_price = trade.get("exit", 0)
        side = trade.get("side")
        symbol = trade.get("symbol", "UNKNOWN")

        if entry == 0 or exit_price == 0:
            continue  # сделка не закрыта

        # расчёт прибыли
        if side == "Buy":
            profit_pct = ((exit_price - entry) / entry) * 100
        else:
            profit_pct = ((entry - exit_price) / entry) * 100

        total_profit_pct += profit_pct
        total_trades += 1
        max_profit = max(max_profit, profit_pct)
        max_loss = min(max_loss, profit_pct)

        if profit_pct > 0:
            profitable += 1
            symbol_stats[symbol]["profitable"] += 1
        elif profit_pct < 0:
            losing += 1
            symbol_stats[symbol]["losing"] += 1
        else:
            breakeven += 1
            symbol_stats[symbol]["breakeven"] += 1

        symbol_stats[symbol]["count"] += 1
        symbol_stats[symbol]["total_pct"] += profit_pct

    if total_trades == 0:
        return (
            "📊 Ваша история без завершённых сделок.\n\n"
            "👇 Нажмите кнопку ниже, чтобы вернуться в главное меню."
        )

    avg_profit_pct = total_profit_pct / total_trades
    winrate = (profitable / total_trades) * 100

    summary = (
        f"📈 *Полная статистика:*\n"
        f"Всего завершённых сделок: {total_trades}\n"
        f"✅ Профитных: {profitable}\n"
        f"❌ Убыточных: {losing}\n"
        f"➖ Безубыточных: {breakeven}\n"
        f"📊 Средний результат: {avg_profit_pct:.2f}%\n"
        f"🏆 Максимальная прибыль: {max_profit:.2f}%\n"
        f"📉 Максимальный убыток: {max_loss:.2f}%\n"
        f"🎯 Winrate: {winrate:.2f}%\n\n"
        f"📌 *По монетам:*\n"
    )

    for symbol, stats in symbol_stats.items():
        if stats["count"] == 0:
            continue

        avg_symbol = stats["total_pct"] / stats["count"]
        win_symbol = (stats["profitable"] / stats["count"]) * 100
        summary += (
            f"🔸 {symbol}: {stats['count']} сделок | "
            f"📈 {stats['profitable']} / ❌ {stats['losing']} / ➖ {stats['breakeven']} | "
            f"📊 Ср. результат: {avg_symbol:.2f}% | "
            f"🎯 Winrate: {win_symbol:.2f}%\n"
        )

    return summary