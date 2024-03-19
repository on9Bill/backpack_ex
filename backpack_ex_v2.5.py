import time
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import requests
import json
import random
import math
import sys

debug = True
debugTs = 0
window = 5000

api_key = ""
api_secret = ""
private_key: ed25519.Ed25519PrivateKey
private_key = ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(api_secret))

def get_balance():
    return requests.get(url=f'https://api.backpack.exchange/api/v1/capital',headers=sign('balanceQuery', {}))

# print(private_key)
def fillHistoryQuery(orderId: int):
    params = {"orderId": orderId, "offset": 0}
    instruction = "fillHistoryQueryAll"
    return requests.get("https://api.backpack.exchange/wapi/v1/history/fills", params=params,
                        headers=sign(instruction, params))

def fillHistoryQuery_all():
    params = {"offset": 0}
    instruction = "fillHistoryQueryAll"
    return requests.get("https://api.backpack.exchange/wapi/v1/history/fills", params=params,
                        headers=sign(instruction, params))

def build_sign(instruction: str, ts: int, params):
    sign_str = f"instruction={instruction}" if instruction else ""
    if params is None:
        params = {}
    if 'postOnly' in params:
        params = params.copy()
        params['postOnly'] = str(params['postOnly']).lower()
    sorted_params = "&".join(
        f"{key}={value}" for key, value in sorted(params.items())
    )
    if sorted_params:
        sign_str += "&" + sorted_params
    if  debug and  debugTs > 0:
        ts =  debugTs
    sign_str += f"&timestamp={ts}&window={ window}"
    signature_bytes =  private_key.sign(sign_str.encode())
    encoded_signature = base64.b64encode(signature_bytes).decode()
    # if  debug:
        # print(f'Waiting Sign Str: {sign_str}')
        # print(f"Signature: {encoded_signature}")
    return encoded_signature

def sign(instruction: str, params):
    ts = int(time.time() * 1e3)
    encoded_signature =  build_sign(instruction, ts, params)
    headers = {
        "X-API-Key":  api_key,
        "X-Signature": encoded_signature,
        "X-Timestamp": str(ts),
        "X-Window": str( window),
        "Content-Type": "application/json; charset=utf-8",
    }
    return headers

def get_ticker(symbol):
    url = f"https://api.backpack.exchange/api/v1/ticker"
    params = {"symbol": symbol}
    res = requests.get(url, params)
    last_price = (res.json()["lastPrice"])
    return last_price

def get_orderbook(symbol):
    url = f"https://api.backpack.exchange/api/v1/depth"
    params = {"symbol": symbol}
    res = requests.get(url, params)
    order_book = (res.json())
    return order_book

def place_order(pair, side, orderType,price, quantity):
    # Example usage:
    instruction = 'orderExecute'
    # Example body parameters, replace these with actual order details
    params = {
                'symbol': pair,
                'side': side,
                'orderType': orderType,
                'price':    price,
                'quantity': quantity,
            }

    # Convert body parameters to a string in JSON format
    headers = sign(instruction, params)
    # POST request to the API endpoint
    response = requests.post(
        "https://api.backpack.exchange/api/v1/order",
        headers=headers,
        data= json.dumps(params)
    )
    # Check the response
    if response.status_code == 200:
        print("Order executed successfully.")
        print(response.json())
    else:
        # print("Failed to execute order.")
        # print(f"Status Code: {response.status_code}")
        print(response.text)

    return response.json()

def round_down(number, decimals=0):
    if decimals < 0:
        raise ValueError("Decimal places must be non-negative")
    factor = 10 ** decimals
    return math.floor(number * factor) / factor
# balance = get_balance()
# print(balance.json()["WIF"]["available"])
# # order = fillHistoryQuery("112058557730783233")
# # print(order.json()[0]["price"])
# # price = fillHistoryQuery_all()
# # print(price.text)
# sys.exit()

if __name__ == '__main__':


    # initial_cap = 900
    ################### #EDIT HERE #######################

    asset = "JUP_USDC"
    profit_goal = 0.005
    temp_cond = False

    ################### #EDIT HERE #######################
    split_pair = asset.split("_")

    token = split_pair[0]
    print(token)
    base = split_pair[1]


    last_qty = 0
    open_price = 0
    # last_capital = initial_cap

    while True:
        qty_cond = last_qty == 0
        last_price = get_ticker(asset)
        # qty = round(initial_cap/float(last_price),2)
        # place_order(asset, "Bid", "Market", str(qty))
        order_book = get_orderbook(asset)
        bid = order_book["bids"]
        ask = order_book["asks"]
        top_up = 3
        print("Last traded price is $", last_price)

        if not qty_cond and (float(last_price) > open_price*(1+profit_goal) or temp_cond):
            # place_order(asset, "Ask", "Limit", str(bid[top_up*-1][0]),str(last_qty))
            balance = get_balance()
            last_token_balance = float(balance.json()[token]["available"])

            ################### #EDIT HERE #######################
            last_token_balance = round_down(last_token_balance, 0)
            ################### #EDIT HERE #######################

            print("Last Token Balance: ", last_token_balance)
            trade_data = place_order(asset, "Ask", "Limit", str(bid[-1*top_up][0]),str(int(last_token_balance)))
            time.sleep(random.randint(20, 30))
            order_id = trade_data["id"]
            balance = get_balance()
            last_capital = balance.json()["USDC"]["available"]

            print("Last Balance is ", last_capital)
            # if trade_data["status"] == "Filled":
            #     last_capital = float(trade_data["executedQuoteQuantity"])
            last_qty = 0
                # last_capital = balance.json()["USDC"]["available"]
                # time.sleep(random.randint(1, 4))

        elif qty_cond:
            balance = get_balance()
            last_capital = balance.json()["USDC"]["available"]
            balance = 0
            print("Last Balance is ", last_capital)
            last_qty = math.floor((float(last_capital) / float(ask[top_up][0])))
            # place_order(asset, "Bid", "Limit", str(ask[top_up][0]), str(qty))
            trade_data = place_order(asset, "Bid", "Limit", str(ask[top_up][0]), str(last_qty))
            time.sleep(random.randint(20, 30))

            order_id = trade_data["id"]
            open_price = float(trade_data["price"])
            # order = fillHistoryQuery(order_id)
            # Normal way to get open_price:
            # open_price = float((fillHistoryQuery(int(order_id)).json()[0]["price"]))
            print("last open price is ", open_price)

            time.sleep(random.randint(2, 10))


