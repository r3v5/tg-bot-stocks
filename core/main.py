import asyncio
import logging
import os
import time
import requests
import telegram
from typing import List, Optional
from tinkoff.invest import AioRequestError, AsyncClient, CandleInterval, HistoricCandle, Quotation
from tinkoff.invest.async_services import AsyncServices
import pandas as pd
import numpy as np
from datetime import timedelta
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from tinkoff.invest import CandleInterval, Client, HistoricCandle, Quotation, SubscriptionInterval
from tinkoff.invest.utils import now
import pytz
from threading import Thread

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

'''MoneyValue — используется для параметров, у которых есть денежный эквивалент. Возьмем для примера стоимость ценных бумаг — тип состоит из трех параметров:
1) currency — строковый ISO-код валюты, например RUB или USD;
2) units — целая часть суммы;
3) nano — дробная часть суммы, миллиардные доли единицы.
'''
# Quotation type = MoneyValue. We need to convert this to decimal in order to fetch price per share
def quotation_to_decimal(quotation: Quotation) -> Decimal:
    fractional = quotation.nano / Decimal("10e8")
    return Decimal(quotation.units) + fractional

def get_stock_volumes(_input: int):
    return f'{_input:,} ₽'

def get_final_float_stock_volumes(_input: int):
    return f'{_input:,} ₽'

def get_final_lots(_lots: int):
    return f'{_lots:,} шт.'

def calculate_net_change(current_closing_price: int, prev_closing_price: int):
    return f'Изменение цены: {round(((current_closing_price - prev_closing_price) / prev_closing_price * 100), 2)}%'

def calculate_net_change_per_day(current_closing_price: int, yesterday_closing_price: int):
    # current price minus 840 indexes in order to fetch price index yesterday for 1 minute candle
    return f'Изменение за день: {round(((current_closing_price - yesterday_closing_price) / yesterday_closing_price * 100), 2)}%'

def calculate_net_change_float(current_closing_price: float, prev_closing_price: float):
    return f'Изменение цены: {round(((current_closing_price - prev_closing_price) / prev_closing_price * 100), 2)}%'

def calculate_net_change_per_day_float(current_closing_price: float, yesterday_closing_price: float):
    # current price minus 840 indexes in order to fetch price index yesterday for 1 minute candle
    return f'Изменение за день: {round(((current_closing_price - yesterday_closing_price) / yesterday_closing_price * 100), 2)}%'

def make_million_volumes_on_float_stock_prices(price: int):
    price = str(price)
    price += '0000'
    return int(price)

def make_million_volumes_on_int_stock_prices(price: int):
    price = str(price)
    price += '0'
    return int(price)

def make_million_volumes_on_sngs(price: int):
    price = str(price)
    price += '000'
    return int(price)

def make_million_volumes_on_sngsp(price: int):
    price = str(price)
    price += '00'
    return int(price)

def make_million_volumes_on_cbom(price: int):
    price = str(price)
    price += '00'
    return int(price)

def make_million_volumes_on_afks(price: int):
    price = str(price)
    price += '00'
    return int(price)

def make_million_volumes_on_irao(price: int):
    price = str(price)
    price += '00'
    return int(price)

def make_million_volumes_on_upro(price: int):
    price = str(price)
    price += '000'
    return int(price)

def convert_time_to_moscow(input_date: str):
    datetime_utc = datetime.strptime(str(input_date), '%Y-%m-%d %H:%M:%S%z')
    utc_timezone = pytz.timezone('UTC')
    moscow_timezone = pytz.timezone('Europe/Moscow')
    datetime_moscow = datetime_utc.astimezone(moscow_timezone)
    datetime_moscow = datetime_moscow
    output_date = datetime_moscow.strftime('%Y-%m-%d %H:%M:%S')
    return output_date

class Stock:

    def __init__(self, ticker: str, name: str, figi: str, length_of_df: int, threshold: int):
        self.ticker = ticker
        self.name = name
        self.figi = figi
        self.length_of_df = length_of_df
        self.threshold = threshold
    
    @property
    def ticker(self):
        return self._ticker
    
    @property
    def name(self):
        return self._name
    
    @property
    def figi(self):
        return self._figi
    
    @property
    def length_of_df(self):
        return self._length_of_df
    
    @property
    def threshold(self):
        return self._threshold
    
    @ticker.setter
    def ticker(self, ticker_value):
        self._ticker = ticker_value
    
    @name.setter
    def name(self, name_value):
        self._name = name_value
    
    @figi.setter
    def figi(self, figi_value):
        self._figi = figi_value
    
    @length_of_df.setter
    def length_of_df(self, length_of_df_value):
        self._length_of_df = length_of_df_value
    
    @threshold.setter
    def threshold(self, threshold_value):
        self._threshold = threshold_value

GAZP: Stock = Stock(ticker="GAZP", name="Газпром", figi="BBG004730RP0", length_of_df=61724, threshold=10900000) # 109,000,000 milions
VTBR: Stock = Stock(ticker="VTBR", name="ВТБ", figi="BBG004730ZJ9", length_of_df=58453, threshold=6700000) # 67,000,000
LKOH: Stock = Stock(ticker="LKOH", name="Лукойл", figi="BBG004731032", length_of_df=55016, threshold=8900000) # 89,595,258
YNDX: Stock = Stock(ticker="YNDX", name="ЯНДЕКС", figi="BBG006L8G4H1", length_of_df=55652, threshold=4100000) # min abnormal 41,000,000
MGNT: Stock = Stock(ticker="MGNT", name="Магнит", figi="BBG004RVFCY3", length_of_df=45114, threshold=3900000) # 39,000,000
POLY: Stock = Stock(ticker="POLY", name="Polymetal International", figi="BBG004PYF2N3", length_of_df=56891, threshold=2600000) # 26,000,000
SBERP: Stock = Stock(ticker="SBERP", name="Сбербанк России - привилегированные акции", figi="BBG0047315Y7", length_of_df=52157, threshold=2400000) # 24,000,000
CHMF: Stock = Stock(ticker="CHMF", name="Северсталь", figi="BBG00475K6C3", length_of_df=46712, threshold=1400000) # 14,000,000
ALRS: Stock = Stock(ticker="ALRS", name="АЛРОСА", figi="BBG004S68B31", length_of_df=39065, threshold=2100000) # 21,000,000
MMK: Stock = Stock(ticker="MAGN", name="MMK", figi="BBG004S68507", length_of_df=49532, threshold=1300000) # 13,000,,000
PHOR: Stock = Stock(ticker="PHOR", name="ФосАгро", figi="BBG004S689R0", length_of_df=38268, threshold=1300000) # 13,000,000
SNGS: Stock = Stock(ticker="SNGS", name="Сургутнефтегаз", figi="BBG0047315D0", length_of_df=35861, threshold=17830000) # 178,370,000
SNGSP: Stock = Stock(ticker="SNGSP", name="Сургутнефтегаз - привилегированные акции", figi="BBG004S681M2", length_of_df=38350, threshold=3427000) # 34,270,000
NLMK: Stock = Stock(ticker="NLMK", name="НЛМК", figi="BBG004S681B4", length_of_df=43048, threshold=1270000) # 12,700,000
PLZL: Stock = Stock(ticker="PLZL", name="Полюс", figi="BBG000R607Y3", length_of_df=46937, threshold=4400000) # 44,000,000
TATN: Stock = Stock(ticker="TATN", name="Татнефть", figi="BBG004RVFFC0", length_of_df=50691, threshold=1760000) # 17,600,000
MTLR: Stock = Stock(ticker="MTLR", name="Мечел", figi="BBG004S68598", length_of_df=51040, threshold=2500000) # 25,000,000
MTSS: Stock = Stock(ticker="MTSS", name="МТС", figi="BBG004S681W1", length_of_df=43312, threshold=1980000) # 19,800,000
MOEX: Stock = Stock(ticker="MOEX", name="Московская Биржа", figi="BBG004730JJ5", length_of_df=47942, threshold=1130000) # 11,300,000
RUAL: Stock = Stock(ticker="RUAL", name="ОК РУСАЛ", figi="BBG008F2T3T2", length_of_df=47438, threshold=980000) # 9,800,000
AFLT: Stock = Stock(ticker="AFLT", name="Аэрофлот", figi="BBG004S683W7", length_of_df=53529, threshold=1930000) # 19,300,000
CBOM: Stock = Stock(ticker="CBOM", name="Московский кредитный банк", figi="BBG009GSYN76", length_of_df=28825, threshold=1480000) # 14,800,000
OZON: Stock = Stock(ticker="OZON", name="Озон Холдингс", figi="BBG00Y91R9T3", length_of_df=42607, threshold=1060000) # 10,600,000
AFKS: Stock = Stock(ticker="AFKS", name="АФК Система", figi="BBG004S68614", length_of_df=42938, threshold=1120000) # 11,200,000
SMLT: Stock = Stock(ticker="SMLT", name="Группа компаний Самолет", figi="BBG00F6NKQX3", length_of_df=37732, threshold=2540000) # 25,400,000
SPBE: Stock = Stock(ticker="SPBE", name="СПБ Биржа", figi="BBG002GHV6L9", length_of_df=18672,threshold=2210000) # 22,100,000
PIKK: Stock = Stock(ticker="PIKK", name="ПИК-Специализированный застройщик", figi="BBG004S68BH6", length_of_df=32626, threshold=600000) # 6,000,000
IRAO: Stock = Stock(ticker="IRAO", name="ИНТЕР РАО", figi="BBG004S68473", length_of_df=47133, threshold=860000) # 8,600,000
SIBN: Stock = Stock(ticker="SIBN", name="Газпром нефть", figi="BBG004S684M6", length_of_df=39096, threshold=1830000) # 18,300,000
RASP: Stock = Stock(ticker="RASP", name="Распадская", figi="BBG004S68696", length_of_df=23487, threshold=1660000) # 16,600,000
SGZH: Stock = Stock(ticker="SGZH", name="Сегежа Групп", figi="BBG0100R9963", length_of_df=44001, threshold=750000) # 7,500,000
DSKY: Stock = Stock(ticker="DSKY", name="Детский мир", figi="BBG000BN56Q9", length_of_df=18411, threshold=620000) # 6,200,000
TRNFP: Stock = Stock(ticker="TRNFP", name="Транснефть - привилегированные акции", figi="BBG00475KHX6", length_of_df=13999, threshold=2630000) # 26,300,000
RNFT: Stock = Stock(ticker="RNFT", name="РуссНефть", figi="BBG00F9XX7H4", length_of_df=26665, threshold=3280000) # 32,800,000
FIVE: Stock = Stock(ticker="FIVE", name="X5 Retail Group", figi="BBG00JXPFBN0", length_of_df=36727, threshold=520000) # 5,200,000
BSPB: Stock = Stock(ticker="BSPB", name="Банк Санкт-Петербург", figi="BBG000QJW156", length_of_df=29351, threshold=2340000) # 23,400,000
FLOT: Stock = Stock(ticker="FLOT", name="Совкомфлот", figi="BBG000R04X57", length_of_df=43706, threshold=2900000) # 29,000,000
UWGN: Stock = Stock(ticker="UWGN", name="НПК ОВК", figi="BBG008HD3V85", length_of_df=21247, threshold=2240000) # 22,400,000
MTLRP: Stock = Stock(ticker="MTLRP", name="Мечел - привилегированные акции", figi="BBG004S68FR6", length_of_df=28526, threshold=1060000) # 10,600,000
ISKJ: Stock = Stock(ticker="ISKJ", name="Институт Стволовых Клеток Человека", figi="BBG000N16BP3", length_of_df=21446,threshold=1380000) # 13,800,000
UPRO: Stock = Stock(ticker="UPRO", name="Юнипро", figi="BBG004S686W0", length_of_df=26409, threshold=1570000) # 15,700,000

# threshold coefficient for detecting abnormal volumes and abnormal price changes
THRESHOLD: float = 5.0

class LogOnlyCandlesStrategy:
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
                    
                    if self.figi == GAZP.figi and int(candle.volume * quotation_to_decimal(candle.close)) > GAZP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == VTBR.figi and int(candle.volume * quotation_to_decimal(candle.close)) > VTBR.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{VTBR.ticker} {VTBR.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{VTBR.ticker} {VTBR.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == LKOH.figi and int(candle.volume * quotation_to_decimal(candle.close)) > LKOH.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{LKOH.ticker} {LKOH.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{LKOH.ticker} {LKOH.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == YNDX.figi and int(candle.volume * quotation_to_decimal(candle.close)) > YNDX.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{YNDX.ticker} {YNDX.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{YNDX.ticker} {YNDX.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == MGNT.figi and int(candle.volume * quotation_to_decimal(candle.close)) > MGNT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{MGNT.ticker} {MGNT.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{MGNT.ticker} {MGNT.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == POLY.figi and int(candle.volume * quotation_to_decimal(candle.close)) > POLY.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{POLY.ticker} {POLY.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{POLY.ticker} {POLY.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == SBERP.figi and int(candle.volume * quotation_to_decimal(candle.close)) > SBERP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{SBERP.ticker} {SBERP.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{SBERP.ticker} {SBERP.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == CHMF.figi and int(candle.volume * quotation_to_decimal(candle.close)) > CHMF.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{CHMF.ticker} {CHMF.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{CHMF.ticker} {CHMF.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == ALRS.figi and int(candle.volume * quotation_to_decimal(candle.close)) > ALRS.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{ALRS.ticker} {ALRS.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{ALRS.ticker} {ALRS.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == MMK.figi and int(candle.volume * quotation_to_decimal(candle.close)) > MMK.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{MMK.ticker} {MMK.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{MMK.ticker} {MMK.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == PHOR.figi and int(candle.volume * quotation_to_decimal(candle.close)) > PHOR.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{PHOR.ticker} {PHOR.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{PHOR.ticker} {PHOR.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == SNGS.figi and int(candle.volume * quotation_to_decimal(candle.close)) > SNGS.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{SNGS.ticker} {SNGS.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_sngs(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{SNGS.ticker} {SNGS.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_sngs(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == SNGSP.figi and int(candle.volume * quotation_to_decimal(candle.close)) > SNGSP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{SNGSP.ticker} {SNGSP.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_sngsp(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{SNGSP.ticker} {SNGSP.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_sngsp(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == NLMK.figi and int(candle.volume * quotation_to_decimal(candle.close)) > NLMK.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{NLMK.ticker} {NLMK.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{NLMK.ticker} {NLMK.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == PLZL.figi and int(candle.volume * quotation_to_decimal(candle.close)) > PLZL.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{PLZL.ticker} {PLZL.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{PLZL.ticker} {PLZL.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == TATN.figi and int(candle.volume * quotation_to_decimal(candle.close)) > TATN.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{TATN.ticker} {TATN.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{TATN.ticker} {TATN.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == MTLR.figi and int(candle.volume * quotation_to_decimal(candle.close)) > MTLR.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{MTLR.ticker} {MTLR.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{MTLR.ticker} {MTLR.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == MTSS.figi and int(candle.volume * quotation_to_decimal(candle.close)) > MTSS.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{MTSS.ticker} {MTSS.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{MTSS.ticker} {MTSS.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == MOEX.figi and int(candle.volume * quotation_to_decimal(candle.close)) > MOEX.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{MOEX.ticker} {MOEX.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{MOEX.ticker} {MOEX.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == RUAL.figi and int(candle.volume * quotation_to_decimal(candle.close)) > RUAL.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{RUAL.ticker} {RUAL.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{RUAL.ticker} {RUAL.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == AFLT.figi and int(candle.volume * quotation_to_decimal(candle.close)) > AFLT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{AFLT.ticker} {AFLT.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{AFLT.ticker} {AFLT.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == CBOM.figi and int(candle.volume * quotation_to_decimal(candle.close)) > CBOM.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{CBOM.ticker} {CBOM.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_cbom(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{CBOM.ticker} {CBOM.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_cbom(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == OZON.figi and int(candle.volume * quotation_to_decimal(candle.close)) > OZON.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{OZON.ticker} {OZON.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{OZON.ticker} {OZON.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == AFKS.figi and int(candle.volume * quotation_to_decimal(candle.close)) > AFKS.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{AFKS.ticker} {AFKS.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_afks(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{AFKS.ticker} {AFKS.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_afks(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == SMLT.figi and int(candle.volume * quotation_to_decimal(candle.close)) > SMLT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{SMLT.ticker} {SMLT.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{SMLT.ticker} {SMLT.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == SPBE.figi and int(candle.volume * quotation_to_decimal(candle.close)) > SPBE.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{SPBE.ticker} {SPBE.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{SPBE.ticker} {SPBE.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == PIKK.figi and int(candle.volume * quotation_to_decimal(candle.close)) > PIKK.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{PIKK.ticker} {PIKK.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{PIKK.ticker} {PIKK.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == IRAO.figi and int(candle.volume * quotation_to_decimal(candle.close)) > IRAO.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{IRAO.ticker} {IRAO.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_irao(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{IRAO.ticker} {IRAO.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_irao(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == SIBN.figi and int(candle.volume * quotation_to_decimal(candle.close)) > SIBN.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{SIBN.ticker} {SIBN.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{SIBN.ticker} {SIBN.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == RASP.figi and int(candle.volume * quotation_to_decimal(candle.close)) > RASP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{RASP.ticker} {RASP.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{RASP.ticker} {RASP.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == SGZH.figi and int(candle.volume * quotation_to_decimal(candle.close)) > SGZH.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{SGZH.ticker} {SGZH.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close)))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{SGZH.ticker} {SGZH.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close)))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == DSKY.figi and int(candle.volume * quotation_to_decimal(candle.close)) > DSKY.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{DSKY.ticker} {DSKY.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{DSKY.ticker} {DSKY.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == TRNFP.figi and int(candle.volume * quotation_to_decimal(candle.close)) > TRNFP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{TRNFP.ticker} {TRNFP.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{TRNFP.ticker} {TRNFP.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == RNFT.figi and int(candle.volume * quotation_to_decimal(candle.close)) > RNFT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{RNFT.ticker} {RNFT.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{RNFT.ticker} {RNFT.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == FIVE.figi and int(candle.volume * quotation_to_decimal(candle.close)) > FIVE.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{FIVE.ticker} {FIVE.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{FIVE.ticker} {FIVE.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == BSPB.figi and int(candle.volume * quotation_to_decimal(candle.close)) > BSPB.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{BSPB.ticker} {BSPB.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{BSPB.ticker} {BSPB.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == FLOT.figi and int(candle.volume * quotation_to_decimal(candle.close)) > FLOT.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{FLOT.ticker} {FLOT.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{FLOT.ticker} {FLOT.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == UWGN.figi and int(candle.volume * quotation_to_decimal(candle.close)) > UWGN.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{UWGN.ticker} {UWGN.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{UWGN.ticker} {UWGN.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(int(candle.volume * quotation_to_decimal(candle.close)))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == MTLRP.figi and int(candle.volume * quotation_to_decimal(candle.close)) > MTLRP.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{MTLRP.ticker} {MTLRP.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{MTLRP.ticker} {MTLRP.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == ISKJ.figi and int(candle.volume * quotation_to_decimal(candle.close)) > ISKJ.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{ISKJ.ticker} {ISKJ.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{ISKJ.ticker} {ISKJ.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                    
                    if self.figi == UPRO.figi and int(candle.volume * quotation_to_decimal(candle.close)) > UPRO.threshold:
                        # BUYING VOLUME AND SELLING VOLUME
                        if candle.high == candle.low:
                            BV = 0
                            SV = 0
                        else:
                            BV = (float(candle.volume) * (float(quotation_to_decimal(candle.close)) - float(quotation_to_decimal(candle.low)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            SV = (float(candle.volume) * (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.close)))) / (float(quotation_to_decimal(candle.high)) - float(quotation_to_decimal(candle.low)))
                            TP = BV + SV
                            BVP = round((BV / TP) * 100)
                            SVP = round((SV / TP) * 100)
                
                        if BVP > SVP:
                            send_message(f'#{UPRO.ticker} {UPRO.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_upro(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            send_message(f'#{UPRO.ticker} {UPRO.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_upro(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\n \nЗаметил Бот Баффет на Уораннах.')
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
            strategy = LogOnlyCandlesStrategy(
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
    check_interval = 10  # seconds to check interval for new completed candle

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