from database import get_today_trades

def calculate_daily_stats(user_id):
    trades = get_today_trades(user_id)

    if not trades:
        return "📊 Сегодня ещё не было сделок."

    total_profit_pct = 0
    total_trades = len(trades)
    profitable = 0
    losing = 0

    report_lines = []

    for trade in trades:
        entry = float(trade["entry"])
        exit_price = trade.get("exit")
        if exit_price is None:
            continue  # сделка ещё не закрыта

        exit_price = float(exit_price)
        side = trade["side"]
        symbol = trade["symbol"]

        if side == "Buy":
            profit_pct = ((exit_price - entry) / entry) * 100
        else:
            profit_pct = ((entry - exit_price) / entry) * 100

        total_profit_pct += profit_pct

        if profit_pct >= 0:
            profitable += 1
        else:
            losing += 1

        report_lines.append(f"{symbol}: {profit_pct:.2f}%")

    avg_profit = total_profit_pct / total_trades if total_trades else 0

    summary = (
        f"📈 *Статистика за сегодня:*\n"
        f"Всего сделок: {total_trades}\n"
        f"✅ Профитных: {profitable}\n"
        f"❌ Убыточных: {losing}\n"
        f"📊 Средний результат: {avg_profit:.2f}%\n\n"
        + "\n".join(report_lines)
    )

    return summary
