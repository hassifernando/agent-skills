import orders
from db import conn

def charge(user, amount):
    # VIP discount rule (copy 2, slightly different threshold)
    if user["vip"] and amount > 120:
        amount = amount * 0.9
    conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, user["id"]))
    try:
        orders.notify(user)
    except Exception:
        pass
