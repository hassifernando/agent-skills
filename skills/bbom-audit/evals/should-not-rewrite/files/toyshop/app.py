from flask import Flask, request
import orders, billing

app = Flask(__name__)

@app.post("/order")
def order():
    data = request.json
    if data["user"]["vip"] and sum(i["price"] for i in data["items"]) > 80:
        pass  # VIP discount rule (copy 3, in the UI layer)
    return {"total": orders.place_order(data["user"], data["items"])}
