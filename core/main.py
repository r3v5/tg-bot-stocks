import asyncio
import logging
from termcolor import colored
import time
import requests
import telegram
from typing import List, Optional
from tinkoff.invest import AioRequestError, AsyncClient, CandleInterval, HistoricCandle, Quotation
from tinkoff.invest.async_services import AsyncServices
from datetime import timedelta
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from tinkoff.invest import CandleInterval, Client, HistoricCandle, Quotation, SubscriptionInterval
from tinkoff.invest.utils import now
import pytz

TINKOFF_TOKEN: str = 't.b7eKSJEp3fpSiiv4mVt4fWwKIxaMHM1lDMtpGsPTeyl850b9Y4MluXYv-EQrj1vEu7QfkNwqGqGPfTW9N6EvTg'
TELEGRAM_TOKEN: str = '6202414503:AAGmVIVsV_WluHKzeRXbF89gHuK4rfgVJj8'
bot = telegram.Bot(token=TELEGRAM_TOKEN)
TELEGRAM_CHANNEL: int = -1001935956578
#@warrenbaffetbot

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

__all__ = (
    "get_intervals",
    "quotation_to_decimal",
    "decimal_to_quotation",
    "candle_interval_to_subscription_interval",
    "now",
    "candle_interval_to_timedelta",
    "ceil_datetime",
    "floor_datetime",
    "dataclass_from_dict",
    "datetime_range_floor",
)

def send_message(text):
    res = requests.get('https://api.telegram.org/bot{}/sendMessage'.format(TELEGRAM_TOKEN), params=dict(
        chat_id=TELEGRAM_CHANNEL, text=text
    ))

class InstrumentTradingData:
    def __set_name__(self, owner, name):
        self.name = "_" + name
    
    def __get__(self, instance, owner):
        return instance.__dict__[self.name]
    
    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

class MoexStock:
    ticker: InstrumentTradingData = InstrumentTradingData()
    name: InstrumentTradingData = InstrumentTradingData()
    figi: InstrumentTradingData = InstrumentTradingData()
    length_of_df: InstrumentTradingData = InstrumentTradingData()
    threshold: InstrumentTradingData = InstrumentTradingData()

    def __init__(self, ticker: str, name: str, figi: str, length_of_df: int, threshold: int):
        self.ticker = ticker
        self.name = name
        self.figi = figi
        self.length_of_df = length_of_df
        self.threshold = threshold
    
    @staticmethod
    def quotation_to_decimal(quotation: Quotation) -> Decimal:
        #MoneyValue — используется для параметров, у которых есть денежный эквивалент. Возьмем для примера стоимость ценных бумаг — тип состоит из трех параметров:
        #1) currency — строковый ISO-код валюты, например RUB или USD;
        #2) units — целая часть суммы;
        #3) nano — дробная часть суммы, миллиардные доли единицы.
        # Quotation type = MoneyValue. We need to convert this to decimal in order to fetch price per share
        fractional = quotation.nano / Decimal("10e8")
        return Decimal(quotation.units) + fractional
    
    @staticmethod
    def get_stock_volumes(_input: int):
        return f'{_input:,} ₽'
    
    @staticmethod
    def get_final_float_stock_volumes(_input: int):
        return f'{_input:,} ₽'
    
    @staticmethod
    def get_final_lots(_lots: int):
        lots = f'{_lots:,} шт.'
        return colored(lots, "white", attrs=["bold"])
    
    @staticmethod
    def calculate_net_change(current_closing_price: int, prev_closing_price: int):
        return f'{colored("Изменение цены:", "white", attrs=["bold"])} {colored(str(round(((current_closing_price - prev_closing_price) / prev_closing_price * 100), 2)), "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}'
    
    @staticmethod
    def calculate_net_change_per_day(current_closing_price: int, yesterday_closing_price: int):
    # current price minus 840 indexes in order to fetch price index yesterday for 1 minute candle
        return f'Изменение за день: {round(((current_closing_price - yesterday_closing_price) / yesterday_closing_price * 100), 2)}%'
    
    @staticmethod
    def calculate_net_change_float(current_closing_price: float, prev_closing_price: float):
        return f'Изменение цены: {round(((current_closing_price - prev_closing_price) / prev_closing_price * 100), 2)}%'
    
    @staticmethod
    def calculate_net_change_per_day_float(current_closing_price: float, yesterday_closing_price: float):
    # current price minus 840 indexes in order to fetch price index yesterday for 1 minute candle
        return f'Изменение за день: {round(((current_closing_price - yesterday_closing_price) / yesterday_closing_price * 100), 2)}%'
    
    @staticmethod
    def make_million_volumes_on_float_stock_prices(price: int):
        price = str(price)
        price += '0000'
        return int(price)
    
    @staticmethod
    def make_million_volumes_on_int_stock_prices(price: int):
        price = str(price)
        price += '0'
        return int(price)
    
    @staticmethod
    def make_million_volumes_on_sngs(price: int):
        price = str(price)
        price += '000'
        return int(price)
    
    @staticmethod
    def make_million_volumes_on_sngsp(price: int):
        price = str(price)
        price += '00'
        return int(price)
    
    @staticmethod
    def make_million_volumes_on_cbom(price: int):
        price = str(price)
        price += '00'
        return int(price)
    
    @staticmethod
    def make_million_volumes_on_afks(price: int):
        price = str(price)
        price += '00'
        return int(price)
    
    @staticmethod
    def make_million_volumes_on_irao(price: int):
        price = str(price)
        price += '00'
        return int(price)
    
    @staticmethod
    def make_million_volumes_on_upro(price: int):
        price = str(price)
        price += '000'
        return int(price)
    
    @staticmethod
    def convert_time_to_moscow(input_date: str):
        datetime_utc = datetime.strptime(str(input_date), '%Y-%m-%d %H:%M:%S%z')
        utc_timezone = pytz.timezone('UTC')
        moscow_timezone = pytz.timezone('Europe/Moscow')
        datetime_moscow = datetime_utc.astimezone(moscow_timezone)
        datetime_moscow = datetime_moscow
        output_date = datetime_moscow.strftime('%Y-%m-%d %H:%M:%S')
        return output_date
    
    @staticmethod
    def convert_to_short(value: int):
        # Convert the value to a string
        value_str = str(value)
        
        # Remove commas from the string
        value_str = value_str.replace(',', '')
        
        # Convert the string to an integer
        value_int = int(value_str)
        
        # Define the suffixes for million, billion, trillion, etc.
        suffixes = ['K', 'M', 'B', 'T']
        
        # Determine the appropriate suffix based on the value
        suffix_index = 0
        while value_int >= 1000 and suffix_index < len(suffixes):
            value_int /= 1000
            suffix_index += 1
    
        # Format the value with the suffix
        formatted_value = f'{value_int:.0f}{suffixes[suffix_index-1]} ₽' if suffix_index > 0 else str(value_int)
        
        return formatted_value

ABRD: MoexStock = MoexStock(ticker="ABRD", name="Абрау-Дюрсо", figi="BBG002W2FT69", length_of_df=17470, threshold=15000000)
ROSN: MoexStock = MoexStock(ticker="ROSN", name="Роснефть", figi="BBG004731354", length_of_df=60319, threshold=20000000)
QIWI: MoexStock = MoexStock(ticker="QIWI", name="М видео", figi="BBG005D1WCQ1", length_of_df=23785, threshold=4000000)
MVID: MoexStock = MoexStock(ticker="MVID", name="М видео", figi="BBG004S68CP5", length_of_df=30872, threshold=4000000)
TCSG: MoexStock = MoexStock(ticker="TCSG", name="TCS Group", figi="BBG00QPYJ5H0", length_of_df=45456, threshold=18000000)
SBER: MoexStock = MoexStock(ticker="SBER", name="Сбербанк России", figi="BBG004730N88", length_of_df=62771, threshold=187000000)
BANEP: MoexStock = MoexStock(ticker="BANEP", name="Башнефть - привилегированные акции", figi="BBG004S686N0", length_of_df=24385, threshold=34000000) # 34,000,000
VKCO: MoexStock = MoexStock(ticker="VKCO", name="VK Company Ltd", figi="BBG00178PGX3", length_of_df=48954, threshold=15000000) # 15,000,000
GAZP: MoexStock = MoexStock(ticker="GAZP", name="Газпром", figi="BBG004730RP0", length_of_df=61724, threshold=109000000) # 109,000,000 milions
VTBR: MoexStock = MoexStock(ticker="VTBR", name="ВТБ", figi="BBG004730ZJ9", length_of_df=58453, threshold=67000000) # 67,000,000
LKOH: MoexStock = MoexStock(ticker="LKOH", name="Лукойл", figi="BBG004731032", length_of_df=55016, threshold=89000000) # 89,595,258
YNDX: MoexStock = MoexStock(ticker="YNDX", name="ЯНДЕКС", figi="BBG006L8G4H1", length_of_df=55652, threshold=41000000) # min abnormal 41,000,000
MGNT: MoexStock = MoexStock(ticker="MGNT", name="Магнит", figi="BBG004RVFCY3", length_of_df=45114, threshold=39000000) # 39,000,000
POLY: MoexStock = MoexStock(ticker="POLY", name="Polymetal International", figi="BBG004PYF2N3", length_of_df=56891, threshold=26000000) # 26,000,000
SBERP: MoexStock = MoexStock(ticker="SBERP", name="Сбербанк России - привилегированные акции", figi="BBG0047315Y7", length_of_df=52157, threshold=24000000) # 24,000,000
CHMF: MoexStock = MoexStock(ticker="CHMF", name="Северсталь", figi="BBG00475K6C3", length_of_df=46712, threshold=14000000) # 14,000,000
ALRS: MoexStock = MoexStock(ticker="ALRS", name="АЛРОСА", figi="BBG004S68B31", length_of_df=39065, threshold=21000000) # 21,000,000
MMK: MoexStock = MoexStock(ticker="MAGN", name="MMK", figi="BBG004S68507", length_of_df=49532, threshold=13000000) # 13,000,,000
PHOR: MoexStock = MoexStock(ticker="PHOR", name="ФосАгро", figi="BBG004S689R0", length_of_df=38268, threshold=13000000) # 13,000,000
SNGS: MoexStock = MoexStock(ticker="SNGS", name="Сургутнефтегаз", figi="BBG0047315D0", length_of_df=35861, threshold=178300000) # 178,370,000
SNGSP: MoexStock = MoexStock(ticker="SNGSP", name="Сургутнефтегаз - привилегированные акции", figi="BBG004S681M2", length_of_df=38350, threshold=34270000) # 34,270,000
NLMK: MoexStock = MoexStock(ticker="NLMK", name="НЛМК", figi="BBG004S681B4", length_of_df=43048, threshold=12700000) # 12,700,000
PLZL: MoexStock = MoexStock(ticker="PLZL", name="Полюс", figi="BBG000R607Y3", length_of_df=46937, threshold=44000000) # 44,000,000
TATN: MoexStock = MoexStock(ticker="TATN", name="Татнефть", figi="BBG004RVFFC0", length_of_df=50691, threshold=17600000) # 17,600,000
MTLR: MoexStock = MoexStock(ticker="MTLR", name="Мечел", figi="BBG004S68598", length_of_df=51040, threshold=25000000) # 25,000,000
MTSS: MoexStock = MoexStock(ticker="MTSS", name="МТС", figi="BBG004S681W1", length_of_df=43312, threshold=19800000) # 19,800,000
MOEX: MoexStock = MoexStock(ticker="MOEX", name="Московская Биржа", figi="BBG004730JJ5", length_of_df=47942, threshold=11300000) # 11,300,000
RUAL: MoexStock = MoexStock(ticker="RUAL", name="ОК РУСАЛ", figi="BBG008F2T3T2", length_of_df=47438, threshold=10000000) # 10,000,000
AFLT: MoexStock = MoexStock(ticker="AFLT", name="Аэрофлот", figi="BBG004S683W7", length_of_df=53529, threshold=19300000) # 19,300,000
CBOM: MoexStock = MoexStock(ticker="CBOM", name="Московский кредитный банк", figi="BBG009GSYN76", length_of_df=28825, threshold=14800000) # 14,800,000
OZON: MoexStock = MoexStock(ticker="OZON", name="Озон Холдингс", figi="BBG00Y91R9T3", length_of_df=42607, threshold=10600000) # 10,600,000
AFKS: MoexStock = MoexStock(ticker="AFKS", name="АФК Система", figi="BBG004S68614", length_of_df=42938, threshold=11200000) # 11,200,000
SMLT: MoexStock = MoexStock(ticker="SMLT", name="Группа компаний Самолет", figi="BBG00F6NKQX3", length_of_df=37732, threshold=25400000) # 25,400,000
SPBE: MoexStock = MoexStock(ticker="SPBE", name="СПБ Биржа", figi="BBG002GHV6L9", length_of_df=18672,threshold=22100000) # 22,100,000
PIKK: MoexStock = MoexStock(ticker="PIKK", name="ПИК-Специализированный застройщик", figi="BBG004S68BH6", length_of_df=32626, threshold=6000000) # 6,000,000
IRAO: MoexStock = MoexStock(ticker="IRAO", name="ИНТЕР РАО", figi="BBG004S68473", length_of_df=47133, threshold=8600000) # 8,600,000
SIBN: MoexStock = MoexStock(ticker="SIBN", name="Газпром нефть", figi="BBG004S684M6", length_of_df=39096, threshold=18300000) # 18,300,000
RASP: MoexStock = MoexStock(ticker="RASP", name="Распадская", figi="BBG004S68696", length_of_df=23487, threshold=16600000) # 16,600,000
SGZH: MoexStock = MoexStock(ticker="SGZH", name="Сегежа Групп", figi="BBG0100R9963", length_of_df=44001, threshold=7500000) # 7,500,000
DSKY: MoexStock = MoexStock(ticker="DSKY", name="Детский мир", figi="BBG000BN56Q9", length_of_df=18411, threshold=6200000) # 6,200,000
TRNFP: MoexStock = MoexStock(ticker="TRNFP", name="Транснефть - привилегированные акции", figi="BBG00475KHX6", length_of_df=13999, threshold=26300000) # 26,300,000
RNFT: MoexStock = MoexStock(ticker="RNFT", name="РуссНефть", figi="BBG00F9XX7H4", length_of_df=26665, threshold=32800000) # 32,800,000
FIVE: MoexStock = MoexStock(ticker="FIVE", name="X5 Retail Group", figi="BBG00JXPFBN0", length_of_df=36727, threshold=5200000) # 5,200,000
BSPB: MoexStock = MoexStock(ticker="BSPB", name="Банк Санкт-Петербург", figi="BBG000QJW156", length_of_df=29351, threshold=23400000) # 23,400,000
FLOT: MoexStock = MoexStock(ticker="FLOT", name="Совкомфлот", figi="BBG000R04X57", length_of_df=43706, threshold=29000000) # 29,000,000
UWGN: MoexStock = MoexStock(ticker="UWGN", name="НПК ОВК", figi="BBG008HD3V85", length_of_df=21247, threshold=22400000) # 22,400,000
MTLRP: MoexStock = MoexStock(ticker="MTLRP", name="Мечел - привилегированные акции", figi="BBG004S68FR6", length_of_df=28526, threshold=10600000) # 10,600,000
ISKJ: MoexStock = MoexStock(ticker="ISKJ", name="Институт Стволовых Клеток Человека", figi="BBG000N16BP3", length_of_df=21446,threshold=13800000) # 13,800,000
UPRO: MoexStock = MoexStock(ticker="UPRO", name="Юнипро", figi="BBG004S686W0", length_of_df=26409, threshold=15700000) # 15,700,000

class AbnormalVolumesStrategy:
    """This class is responsible for a strategy. You can put here
    your methods for your strategy."""

    def __init__(
        self,
        figi: str,
        timeframe: CandleInterval,
        minutes_back: int,
        check_interval: int,
        client: Optional[AsyncServices],
    ):
        self.account_id = None
        self.figi = figi
        self.timeframe = timeframe
        self.minutes_back = minutes_back
        self.check_interval = check_interval
        self.client = client
        self.candles: List[HistoricCandle] = []

    async def get_historical_data(self):
        async for candle in self.client.get_all_candles(
            figi=self.figi,
            from_=now() - timedelta(minutes=self.minutes_back),
            to=now(),
            interval=self.timeframe,
        ):
            if candle not in self.candles:
                if candle.is_complete:
                    self.candles.append(candle)
                    logger.debug("Found %s - figi=%s", candle, self.figi)
                    
                    if self.figi == GAZP.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > GAZP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{GAZP.ticker} {GAZP.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{GAZP.ticker} {GAZP.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == ABRD.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > ABRD.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{ABRD.ticker} {ABRD.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{ABRD.ticker} {ABRD.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == ROSN.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > ROSN.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{ROSN.ticker} {ROSN.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{ROSN.ticker} {ROSN.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == QIWI.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > QIWI.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{QIWI.ticker} {QIWI.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{QIWI.ticker} {QIWI.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == MVID.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > MVID.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{MVID.ticker} {MVID.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{MVID.ticker} {MVID.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == TCSG.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > TCSG.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{TCSG.ticker} {TCSG.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{TCSG.ticker} {TCSG.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == SBER.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > SBER.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{SBER.ticker} {SBER.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{SBER.ticker} {SBER.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == BANEP.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > BANEP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{BANEP.ticker} {BANEP.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{BANEP.ticker} {BANEP.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == VKCO.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > VKCO.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{VKCO.ticker} {VKCO.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{VKCO.ticker} {VKCO.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == VTBR.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > VTBR.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{VTBR.ticker} {VTBR.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{VTBR.ticker} {VTBR.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == LKOH.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > LKOH.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{LKOH.ticker} {LKOH.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{LKOH.ticker} {LKOH.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == YNDX.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > YNDX.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{YNDX.ticker} {YNDX.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{YNDX.ticker} {YNDX.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == MGNT.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > MGNT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{MGNT.ticker} {MGNT.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{MGNT.ticker} {MGNT.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == POLY.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > POLY.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{POLY.ticker} {POLY.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{POLY.ticker} {POLY.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == SBERP.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > SBERP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{SBERP.ticker} {SBERP.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{SBERP.ticker} {SBERP.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == CHMF.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > CHMF.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{CHMF.ticker} {CHMF.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{CHMF.ticker} {CHMF.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == ALRS.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > ALRS.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{ALRS.ticker} {ALRS.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{ALRS.ticker} {ALRS.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == MMK.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > MMK.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{MMK.ticker} {MMK.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{MMK.ticker} {MMK.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == PHOR.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > PHOR.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{PHOR.ticker} {PHOR.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{PHOR.ticker} {PHOR.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == SNGS.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > SNGS.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{SNGS.ticker} {SNGS.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_sngs(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{SNGS.ticker} {SNGS.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_sngs(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == SNGSP.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > SNGSP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{SNGSP.ticker} {SNGSP.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_sngsp(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{SNGSP.ticker} {SNGSP.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_sngsp(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == NLMK.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > NLMK.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{NLMK.ticker} {NLMK.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{NLMK.ticker} {NLMK.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == PLZL.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > PLZL.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{PLZL.ticker} {PLZL.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{PLZL.ticker} {PLZL.name}\n🔻 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == TATN.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > TATN.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{TATN.ticker} {TATN.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{TATN.ticker} {TATN.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == MTLR.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > MTLR.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{MTLR.ticker} {MTLR.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{MTLR.ticker} {MTLR.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == MTSS.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > MTSS.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{MTSS.ticker} {MTSS.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{MTSS.ticker} {MTSS.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == MOEX.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > MOEX.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{MOEX.ticker} {MOEX.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{MOEX.ticker} {MOEX.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == RUAL.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > RUAL.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{RUAL.ticker} {RUAL.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{RUAL.ticker} {RUAL.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == AFLT.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > AFLT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{AFLT.ticker} {AFLT.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{AFLT.ticker} {AFLT.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == CBOM.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > CBOM.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{CBOM.ticker} {CBOM.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_cbom(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{CBOM.ticker} {CBOM.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_cbom(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == OZON.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > OZON.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{OZON.ticker} {OZON.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{OZON.ticker} {OZON.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == AFKS.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > AFKS.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{AFKS.ticker} {AFKS.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_afks(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{AFKS.ticker} {AFKS.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_afks(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == SMLT.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > SMLT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{SMLT.ticker} {SMLT.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{SMLT.ticker} {SMLT.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == SPBE.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > SPBE.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{SPBE.ticker} {SPBE.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{SPBE.ticker} {SPBE.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == PIKK.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > PIKK.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{PIKK.ticker} {PIKK.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{PIKK.ticker} {PIKK.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == IRAO.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > IRAO.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{IRAO.ticker} {IRAO.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_irao(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{IRAO.ticker} {IRAO.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_irao(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == SIBN.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > SIBN.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{SIBN.ticker} {SIBN.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{SIBN.ticker} {SIBN.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == RASP.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > RASP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{RASP.ticker} {RASP.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{RASP.ticker} {RASP.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == SGZH.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > SGZH.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{SGZH.ticker} {SGZH.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{SGZH.ticker} {SGZH.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == DSKY.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > DSKY.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{DSKY.ticker} {DSKY.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{DSKY.ticker} {DSKY.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == TRNFP.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > TRNFP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{TRNFP.ticker} {TRNFP.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{TRNFP.ticker} {TRNFP.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == RNFT.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > RNFT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{RNFT.ticker} {RNFT.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{RNFT.ticker} {RNFT.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == FIVE.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > FIVE.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{FIVE.ticker} {FIVE.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{FIVE.ticker} {FIVE.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == BSPB.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > BSPB.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{BSPB.ticker} {BSPB.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{BSPB.ticker} {BSPB.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == FLOT.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > FLOT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{FLOT.ticker} {FLOT.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{FLOT.ticker} {FLOT.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == UWGN.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > UWGN.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{UWGN.ticker} {UWGN.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{UWGN.ticker} {UWGN.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(int(candle.volume * MoexStock.quotation_to_decimal(candle.close))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == MTLRP.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > MTLRP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{MTLRP.ticker} {MTLRP.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{MTLRP.ticker} {MTLRP.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == ISKJ.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > ISKJ.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{ISKJ.ticker} {ISKJ.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{ISKJ.ticker} {ISKJ.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_int_stock_prices(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                    
                    if self.figi == UPRO.figi and int(candle.volume * MoexStock.quotation_to_decimal(candle.close)) > UPRO.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.close)) - float(MoexStock.quotation_to_decimal(candle.low)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.close)))) / (float(MoexStock.quotation_to_decimal(candle.high)) - float(MoexStock.quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                            
                            if BVP > SVP:
                                send_message(f'#{UPRO.ticker} {UPRO.name}\n🟩 {colored("Аномальный объем", "green", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_upro(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)
                            else:
                                send_message(f'#{UPRO.ticker} {UPRO.name}\n🔻 {colored("Аномальный объем", "red", attrs=["bold"])}\n{MoexStock.calculate_net_change(int(MoexStock.quotation_to_decimal(candle.close)), int(MoexStock.quotation_to_decimal(candle.open)))}\n{colored(MoexStock.convert_to_short(MoexStock.make_million_volumes_on_upro(int(candle.volume * MoexStock.quotation_to_decimal(candle.close)))), "white", attrs=["bold"])} ({MoexStock.get_final_lots(candle.volume)})\n{colored("Покупка:")}{colored(BVP, "white", attrs=["bold"])}{colored("%")} {colored("Продажа:")} {colored(SVP, "white", attrs=["bold"])}{colored("%", "white", attrs=["bold"])}\n{colored("Время:", "white", attrs=["bold"])} {colored(MoexStock.convert_time_to_moscow(candle.time), "white", attrs=["bold"])}\n{colored("Цена:", "white", attrs=["bold"])} {colored(str(float(MoexStock.quotation_to_decimal(candle.close))))} {colored("₽", "white", attrs=["bold"])}\n \n{colored("Заметил Баффет на Уораннах.", "blue", attrs=["reverse", "blink"])}\n{colored("Подключить", "white", attrs=["bold"])} @J0anix')
                                time.sleep(3)

    async def ensure_market_open(self):
        """
        Ensure that the market is open. Loop until the instrument is available.
        :return: when instrument is available for trading
        """
        trading_status = await self.client.market_data.get_trading_status(
            figi=self.figi
        )
        while not (
            trading_status.market_order_available_flag
            and trading_status.api_trade_available_flag
        ):
            logger.debug("Waiting for the market to open. figi=%s", self.figi)
            await asyncio.sleep(60)
            trading_status = await self.client.market_data.get_trading_status(
                figi=self.figi
            )

    async def main_cycle(self):
        """Main cycle for live strategy."""
        while True:
            try:
                await self.ensure_market_open()
                await self.get_historical_data()

                # put your strategy code here for live
                # to generate signals for buying or selling tickers
                logger.debug(
                    "- live mode: run some strategy code to buy or sell - figi=%s",
                    self.figi,
                )

            except AioRequestError as are:
                logger.error("Client error %s", are)

            await asyncio.sleep(self.check_interval)

    async def start(self):
        """Strategy starts from this function."""
        if self.account_id is None:
            try:
                self.account_id = (
                    (await self.client.users.get_accounts()).accounts.pop().id
                )
            except AioRequestError as are:
                logger.error("Error taking account id. Stopping strategy. %s", are)
                return
        await self.main_cycle()


async def run_strategy(portfolio, timeframe, minutes_back, check_interval):
    """From this function we are starting
    strategy for every ticker from portfolio.
    """
    async with AsyncClient(token=TINKOFF_TOKEN, app_name="TinkoffApp") as client:
        strategy_tasks = []
        for instrument in portfolio:
            strategy = AbnormalVolumesStrategy(
                figi=instrument,
                timeframe=timeframe,
                minutes_back=minutes_back,
                check_interval=check_interval,
                client=client,
            )
            strategy_tasks.append(asyncio.create_task(strategy.start()))
        await asyncio.gather(*strategy_tasks)
    
if __name__ == "__main__":
    portfolio = {
        ABRD.figi,
        ROSN.figi,
        QIWI.figi,
        MVID.figi,
        TCSG.figi,
        SBER.figi,
        BANEP.figi,
        VKCO.figi,
        GAZP.figi, 
        VTBR.figi, 
        LKOH.figi, 
        YNDX.figi, 
        MGNT.figi, 
        POLY.figi, 
        SBERP.figi, 
        CHMF.figi, 
        ALRS.figi, 
        MMK.figi, 
        PHOR.figi, 
        SNGS.figi, 
        SNGSP.figi, 
        NLMK.figi, 
        PLZL.figi, 
        TATN.figi, 
        MTLR.figi, 
        MTSS.figi, 
        MOEX.figi, 
        RUAL.figi, 
        AFLT.figi,
        CBOM.figi,
        OZON.figi,
        AFKS.figi,
        SMLT.figi,
        SPBE.figi,
        PIKK.figi,
        IRAO.figi,
        SIBN.figi,
        RASP.figi,
        SGZH.figi,
        DSKY.figi,
        TRNFP.figi,
        RNFT.figi,
        FIVE.figi,
        BSPB.figi,
        FLOT.figi,
        UWGN.figi,
        MTLRP.figi,
        ISKJ.figi,
        UPRO.figi
    }
    timeframe = CandleInterval.CANDLE_INTERVAL_1_MIN
    minutes_back = 2
    check_interval = 30  # seconds to check interval for new completed candle

    loop = asyncio.get_event_loop()
    task = loop.create_task(
        run_strategy(
            portfolio=portfolio,
            timeframe=timeframe,
            minutes_back=minutes_back,
            check_interval=check_interval,
        )
    )
    loop.run_until_complete(task)