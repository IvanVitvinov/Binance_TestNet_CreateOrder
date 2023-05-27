import unittest
from unittest.mock import patch, Mock
from real_order import BinanceTrader
from requests.exceptions import RequestException
from unittest.mock import patch


class TestBinanceTrader(unittest.TestCase):

    @patch('real_order.requests.post')
    @patch('real_order.requests.get')
    def test_create_orders(self, mock_get, mock_post):
        # Имитация успешного ответа от API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'balances': [{'asset': 'USDT', 'free': '100000'}, {'asset': 'BTC', 'free': '10'}]}
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response

        trader = BinanceTrader('test_key', 'test_secret')

        COIN = 'BTC'

        data = {
            "volume": 10000.0,
            "number": 4,
            "amountDif": 50.0,
            "side": "BUY",
            "priceMin": 25200.0,
            "priceMax": 25300.0
        }

        # Проверяем успешное создание ордеров
        try:
            trader.create_orders(data, COIN)
        except Exception as e:
            self.fail(f"test_create_orders failed with {str(e)}")
        
        # Проверяем, что методы requests были вызваны с правильными аргументами
        mock_get.assert_called_with(trader.url + "account", headers=trader.headers, params=unittest.mock.ANY)
        mock_post.assert_called_with(trader.url + "order", headers=trader.headers, params=unittest.mock.ANY)

    @patch('real_order.requests.post')
    @patch('real_order.requests.get')
    def test_create_orders_no_internet(self, mock_get, mock_post):
        # Имитация отсутствия интернет соединения
        mock_get.side_effect = RequestException()
        mock_post.side_effect = RequestException()

        trader = BinanceTrader('test_key', 'test_secret')

        COIN = 'BTC'

        data = {
            "volume": 10000.0,
            "number": 4,
            "amountDif": 50.0,
            "side": "BUY",
            "priceMin": 25200.0,
            "priceMax": 25300.0
        }

        # Проверяем, что при отсутствии интернет соединения метод create_orders выбрасывает исключение
        with self.assertRaises(RequestException):
            trader.create_orders(data, COIN)


    @patch('builtins.print')
    @patch('real_order.requests.post')
    def test_create_orders_insufficient_balance(self, mock_post, mock_print):
        # Имитация ответа от API с балансом меньше 5000
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'balances': [{'asset': 'USDT', 'free': '4999'}, {'asset': 'BTC', 'free': '10'}]}
        mock_post.return_value = mock_response

        COIN = 'BTC'

        data = {
            "volume": 10000.0,
            "number": 4,
            "amountDif": 50.0,
            "side": "BUY",
            "priceMin": 25200.0,
            "priceMax": 25300.0
        }
        
        trader = BinanceTrader('test_key', 'test_secret')

        trader.create_orders(data, COIN)

        # Проверяем, что при недостаточном балансе метод create_orders выбрасывает исключение
        mock_print.assert_called_with(f"Недостаточный баланс для создания ордеров")

if __name__ == "__main__":
    unittest.main()
