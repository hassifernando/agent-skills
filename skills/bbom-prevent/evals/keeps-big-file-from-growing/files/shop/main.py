import sys
from shop import price_rule_1

ORDERS = [{"id": 1, "customer": "ana", "total": 30.0}, {"id": 2, "customer": "bo", "total": 12.5}]

def main(argv):
    for o in ORDERS:
        print(o["id"], price_rule_1(o["total"], 1))

if __name__ == "__main__":
    main(sys.argv[1:])
