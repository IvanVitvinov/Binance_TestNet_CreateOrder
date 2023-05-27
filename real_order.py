import requests
import random
import hmac
import hashlib
import time
from urllib.parse import urlencode

from data.config import API_KEY_REAL, API_SECRET_REAL


class BinanceTrader:
    def __init__(self, API_KEY_REAL, API_SECRET_REAL):
        self.API_KEY_REAL = API_KEY_REAL
        self.API_SECRET_REAL = API_SECRET_REAL
        self.url = "https://testnet.binance.vision/api/v3/"
        self.headers = {"X-MBX-APIKEY": self.API_KEY_REAL}

    # Метод создания подписи для ордеров
    def create_signature(self, params):
        query_string = urlencode(params)
        return hmac.new(self.API_SECRET_REAL.encode(), query_string.encode(), hashlib.sha256).hexdigest()

    # Метод для проверки текущего баланса всех активов тестового счета  
    def check_account_balance(self):
        
        params = {
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000 
        }
        params['signature'] = self.create_signature(params)
        response = requests.get(self.url + "account", headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"Ошибка при получении информации об аккаунте: {response.content}")
        else:
            print(f"Информация об аккаунте: {response.json()}")

    # Метод для проверки текущего баланса определенного актива
    def get_balance(self, symbol):
        params = {
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000
        }
        params['signature'] = self.create_signature(params)
        response = requests.get(self.url + "account", headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"Ошибка при получении информации об аккаунте: {response.content}")
            return None
        else:
            balances = response.json()['balances']
            for balance in balances:
                if balance['asset'] == symbol:
                    return float(balance['free'])
        return None

    # Метод для отмены всех активных ордеров
    def cancel_all_orders(self, symbol):
        params = {
            "symbol": f"{symbol}USDT",
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000 
        }
        params['signature'] = self.create_signature(params)
        try:
            response = requests.get(self.url + "openOrders", headers=self.headers, params=params)
            response.raise_for_status()
            open_orders = response.json()
            num_open_orders = len(open_orders)
            
            response = requests.delete(self.url + "openOrders", headers=self.headers, params=params)
            response.raise_for_status()
            
            print(f"Все заказы успешно отменены. Количество отмененных ордеров: {num_open_orders}")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400 and response.json()['code'] == -2011:
                print("Нет открытых ордеров, нечего отменять.")
            else:
                print(f"Ошибка при отмене заказов: {response.content}")

    #  Метод создания ордеров
    def create_orders(self, data, symbol):
        # Выводим баланс до размещения ордеров
        if data['side'] == 'SELL':
            print(f"Баланс {symbol} до сделки: {self.get_balance(f'{symbol}')}")
        else:
            print(f"Баланс USDT до сделки: {self.get_balance('USDT')}")

        # Расчитываем объем ордеров
        volume_per_order = data['volume'] / data['number']
        # Переменные для вывода результатов
        total_spent = 0
        prices = []
        orders_created = 0
        # Переменные для проверки условий баланса 
        usdt_balance = self.get_balance('USDT')
        coin_balance = self.get_balance('BTC')
        required_coin = data['volume'] / data['priceMin']  
        required_usdt = data['volume']


        # Проверяем хватает ли нам баланса для создания ордеров
        if data['side'] == 'SELL' and (coin_balance is None or required_coin > coin_balance):
            print(f"Недостаточный баланс для создания ордеров")
        elif data['side'] == 'BUY' and (usdt_balance is None or required_usdt > usdt_balance):
            print(f"Недостаточный баланс для создания ордеров")
        else:
            # Если баланса хватает, переходим в цикл создания ордеров.
            for i in range(data['number']):
                try:
                    while True:
                        # Проверяем соединение с серверами Бинанса, если все ок, начинаем размещать ордера.
                        try:
                            response = self.get_balance(symbol)
                            if response is None:
                                raise Exception("Ошибка соединения с сервером.")
                        except Exception as e:
                            print(f"{str(e)}. Повторная попытка...")
                            continue
                        break
                    # Устанавливаем объем для ордеров. Объем последнего ордера проверяем отдельно, чтобы отклонение от общего объема не превышало заданное в условиях отклонение
                    if i < data['number'] - 1:
                        amount_in_usdt = volume_per_order + random.uniform(-data['amountDif'], data['amountDif'])
                    else:
                        amount_in_usdt = data['volume'] - total_spent
                        amount_in_usdt += random.uniform(-data['amountDif'], data['amountDif'])

                    # Округляем значения до правильных значений, установленных биржей.
                    price = round(random.uniform(data['priceMin'], data['priceMax']), 2) 
                    amount_in_coin = round(amount_in_usdt / price, 6)
                    
                    # Обновляем переменные, для выдачи результата наших действий. 
                    prices.append(price)
                    total_spent += amount_in_usdt

                    # Подготавливаем и отправляем запрос
                    params = {
                        "symbol": f"{symbol}USDT",
                        "side": data['side'],
                        "type": "LIMIT",
                        "timeInForce": "GTC",
                        "quantity": amount_in_coin,
                        "price": "{:.2f}".format(price),
                        "timestamp": int(time.time() * 1000),
                        "recvWindow": 5000 
                    }
                    params['signature'] = self.create_signature(params)
                    response = requests.post(self.url + "order", headers=self.headers, params=params)
                    response.raise_for_status()
                    orders_created += 1

                except requests.exceptions.HTTPError as e:
                    print(f"Ошибка создания ордера: {response.content}")
                    self.cancel_all_orders(symbol)
                    return

            # Принтим среднюю цену покупки и объем, и количество ордеров
            avg_price = sum(prices) / len(prices)
            print(f"Ордера успешно размещены: {orders_created}/{data['number']}")
            print(f"Средняя цена: {avg_price}")
            print(f"Всего потрачено: {total_spent}")
            # Выводим баланс в зависимости от сделки 
            if data['side'] == 'SELL':
                print(f"Баланс {symbol} после сделки: {self.get_balance(f'{symbol}')}")
            else:
                print(f"Баланс USDT после сделки: {self.get_balance('USDT')}")


def main():

    COIN = 'BTC'

    data = {
            "volume": 10000.0,
            "number": 4,
            "amountDif": 50.0,
            "side": "BUY",
            "priceMin": 25200.0,
            "priceMax": 25300.0
        }


    trader = BinanceTrader(API_KEY_REAL, API_SECRET_REAL)
    trader.cancel_all_orders(COIN)
    trader.create_orders(data, COIN)
    


if __name__ == "__main__":
    main()