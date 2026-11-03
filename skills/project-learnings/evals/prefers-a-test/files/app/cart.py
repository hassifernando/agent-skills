def total_cents(items, discount=1.0):
    return round(sum(i["cents"] for i in items) * discount)
