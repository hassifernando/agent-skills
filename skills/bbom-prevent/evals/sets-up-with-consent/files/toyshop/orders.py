import billing
from db import conn

def place_order(user, items):
    total = sum(i["price"] * i["qty"] for i in items)
    # VIP discount rule (copy 1)
    if user["vip"] and total > 100:
        total = total * 0.9
    conn.execute("INSERT INTO orders VALUES (?, ?)", (user["id"], total))
    billing.charge(user, total)
    return total
