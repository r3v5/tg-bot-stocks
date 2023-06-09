import asyncio
import logging
import os
import time
import requests
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
TELEGRAM_CHANNEL: str = '@warrenbaffetbot'

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

    def __init__(self, ticker: str, name: str, figi: str, length_of_df: int):
        self.ticker = ticker
        self.name = name
        self.figi = figi
        self.length_of_df = length_of_df
    
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

GAZP: Stock = Stock(ticker="GAZP", name="Газпром", figi="BBG004730RP0", length_of_df=61724)
VTBR: Stock = Stock(ticker="VTBR", name="ВТБ", figi="BBG004730ZJ9", length_of_df=58453)
LKOH: Stock = Stock(ticker="LKOH", name="Лукойл", figi="BBG004731032", length_of_df=55016)
YNDX: Stock = Stock(ticker="YNDX", name="ЯНДЕКС", figi="BBG006L8G4H1", length_of_df=55652)
MGNT: Stock = Stock(ticker="MGNT", name="Магнит", figi="BBG004RVFCY3", length_of_df=45114)
POLY: Stock = Stock(ticker="POLY", name="Polymetal International", figi="BBG004PYF2N3", length_of_df=56891)
SBERP: Stock = Stock(ticker="SBERP", name="Сбербанк России - привилегированные акции", figi="BBG0047315Y7", length_of_df=52157)
CHMF: Stock = Stock(ticker="CHMF", name="Северсталь", figi="BBG00475K6C3", length_of_df=46712)
ALRS: Stock = Stock(ticker="ALRS", name="АЛРОСА", figi="BBG004S68B31", length_of_df=39065)
MMK: Stock = Stock(ticker="MAGN", name="MMK", figi="BBG004S68507", length_of_df=49532)
PHOR: Stock = Stock(ticker="PHOR", name="ФосАгро", figi="BBG004S689R0", length_of_df=38268)
SNGS: Stock = Stock(ticker="SNGS", name="Сургутнефтегаз", figi="BBG0047315D0", length_of_df=35861)
SNGSP: Stock = Stock(ticker="SNGSP", name="Сургутнефтегаз - привилегированные акции", figi="BBG004S681M2", length_of_df=38350)
NLMK: Stock = Stock(ticker="NLMK", name="НЛМК", figi="BBG004S681B4", length_of_df=43048)
PLZL: Stock = Stock(ticker="PLZL", name="Полюс", figi="BBG000R607Y3", length_of_df=46937)
TATN: Stock = Stock(ticker="TATN", name="Татнефть", figi="BBG004RVFFC0", length_of_df=50691)
MTLR: Stock = Stock(ticker="MTLR", name="Мечел", figi="BBG004S68598", length_of_df=51040)
MTSS: Stock = Stock(ticker="MTSS", name="МТС", figi="BBG004S681W1", length_of_df=43312)
MOEX: Stock = Stock(ticker="MOEX", name="Московская Биржа", figi="BBG004730JJ5", length_of_df=47942)
RUAL: Stock = Stock(ticker="RUAL", name="ОК РУСАЛ", figi="BBG008F2T3T2", length_of_df=47438)
AFLT: Stock = Stock(ticker="AFLT", name="Аэрофлот", figi="BBG004S683W7", length_of_df=53529)
CBOM: Stock = Stock(ticker="CBOM", name="Московский кредитный банк", figi="BBG009GSYN76", length_of_df=28825)
OZON: Stock = Stock(ticker="OZON", name="Озон Холдингс", figi="BBG00Y91R9T3", length_of_df=42607)
AFKS: Stock = Stock(ticker="AFKS", name="АФК Система", figi="BBG004S68614", length_of_df=42938)
SMLT: Stock = Stock(ticker="SMLT", name="Группа компаний Самолет", figi="BBG00F6NKQX3", length_of_df=37732)
SPBE: Stock = Stock(ticker="SPBE", name="СПБ Биржа", figi="BBG002GHV6L9", length_of_df=18672)
PIKK: Stock = Stock(ticker="PIKK", name="ПИК-Специализированный застройщик", figi="BBG004S68BH6", length_of_df=32626)
IRAO: Stock = Stock(ticker="IRAO", name="ИНТЕР РАО", figi="BBG004S68473", length_of_df=47133)
SIBN: Stock = Stock(ticker="SIBN", name="Газпром нефть", figi="BBG004S684M6", length_of_df=39096)
RASP: Stock = Stock(ticker="RASP", name="Распадская", figi="BBG004S68696", length_of_df=23487)
SGZH: Stock = Stock(ticker="SGZH", name="Сегежа Групп", figi="BBG0100R9963", length_of_df=44001)
DSKY: Stock = Stock(ticker="DSKY", name="Детский мир", figi="BBG000BN56Q9", length_of_df=18411)
TRNFP: Stock = Stock(ticker="TRNFP", name="Транснефть - привилегированные акции", figi="BBG00475KHX6", length_of_df=13999)
RNFT: Stock = Stock(ticker="RNFT", name="РуссНефть", figi="BBG00F9XX7H4", length_of_df=26665)
FIVE: Stock = Stock(ticker="FIVE", name="X5 Retail Group", figi="BBG00JXPFBN0", length_of_df=36727)
BSPB: Stock = Stock(ticker="BSPB", name="Банк Санкт-Петербург", figi="BBG000QJW156", length_of_df=29351)
FLOT: Stock = Stock(ticker="FLOT", name="Совкомфлот", figi="BBG000R04X57", length_of_df=43706)
UWGN: Stock = Stock(ticker="UWGN", name="НПК ОВК", figi="BBG008HD3V85", length_of_df=21247)
MTLRP: Stock = Stock(ticker="MTLRP", name="Мечел - привилегированные акции", figi="BBG004S68FR6", length_of_df=28526)
ISKJ: Stock = Stock(ticker="ISKJ", name="Институт Стволовых Клеток Человека", figi="BBG000N16BP3", length_of_df=21446)
UPRO: Stock = Stock(ticker="UPRO", name="Юнипро", figi="BBG004S686W0", length_of_df=26409)

# threshold coefficient for detecting abnormal volumes and abnormal price changes
THRESHOLD: float = 5.0

gazp_volumes, gazp_lots, gazp_prices, gazp_time, gazp_close, gazp_high, gazp_low, gazp_bvp, gazp_svp = [], [], [], [], [], [], [], [], []
gazp_data = {"Объем": gazp_volumes, "Лоты": gazp_lots, "Цена": gazp_prices, "Время": gazp_time, "Закрытие": gazp_close, "Хай": gazp_high, "Лоу": gazp_low, "Покупка": gazp_bvp, "Продажа": gazp_svp}
gazp_db = []
gazp_candles = []

vtbr_volumes, vtbr_lots, vtbr_prices, vtbr_time, vtbr_close, vtbr_high, vtbr_low, vtbr_bvp, vtbr_svp = [], [], [], [], [], [], [], [], []
vtbr_data = {"Объем": vtbr_volumes, "Лоты": vtbr_lots, "Цена": vtbr_prices, "Время": vtbr_time, "Закрытие": vtbr_close, "Хай": vtbr_high, "Лоу": vtbr_low, "Покупка": vtbr_bvp, "Продажа": vtbr_svp}
vtbr_db = []

lkoh_volumes, lkoh_lots, lkoh_prices, lkoh_time, lkoh_close, lkoh_high, lkoh_low, lkoh_bvp, lkoh_svp = [], [], [], [], [], [], [], [], []
lkoh_data = {"Объем": lkoh_volumes, "Лоты": lkoh_lots, "Цена": lkoh_prices, "Время": lkoh_time, "Закрытие": lkoh_close, "Хай": lkoh_high, "Лоу": lkoh_low, "Покупка": lkoh_bvp, "Продажа": lkoh_svp}
lkoh_db = []

yndx_volumes, yndx_lots, yndx_prices, yndx_time, yndx_close, yndx_high, yndx_low, yndx_bvp, yndx_svp = [], [], [], [], [], [], [], [], []
yndx_data = {"Объем": yndx_volumes, "Лоты": yndx_lots, "Цена": yndx_prices, "Время": yndx_time, "Закрытие": yndx_close, "Хай": yndx_high, "Лоу": yndx_low, "Покупка": yndx_bvp, "Продажа": yndx_svp}
yndx_db = []

mgnt_volumes, mgnt_lots, mgnt_prices, mgnt_time, mgnt_close, mgnt_high, mgnt_low, mgnt_bvp, mgnt_svp = [], [], [], [], [], [], [], [], []
mgnt_data = {"Объем": mgnt_volumes, "Лоты": mgnt_lots, "Цена": mgnt_prices, "Время": mgnt_time, "Закрытие": mgnt_close, "Хай": mgnt_high, "Лоу": mgnt_low, "Покупка": mgnt_bvp, "Продажа": mgnt_svp}
mgnt_db = []

poly_volumes, poly_lots, poly_prices, poly_time, poly_close, poly_high, poly_low, poly_bvp, poly_svp = [], [], [], [], [], [], [], [], []
poly_data = {"Объем": poly_volumes, "Лоты": poly_lots, "Цена": poly_prices, "Время": poly_time, "Закрытие": poly_close, "Хай": poly_high, "Лоу": poly_low, "Покупка": poly_bvp, "Продажа": poly_svp}
poly_db = []

sberp_volumes, sberp_lots, sberp_prices, sberp_time, sberp_close, sberp_high, sberp_low, sberp_bvp, sberp_svp = [], [], [], [], [], [], [], [], []
sberp_data = {"Объем": sberp_volumes, "Лоты": sberp_lots, "Цена": sberp_prices, "Время": sberp_time, "Закрытие": sberp_close, "Хай": sberp_high, "Лоу": sberp_low, "Покупка": sberp_bvp, "Продажа": sberp_svp}
sberp_db = []

chmf_volumes, chmf_lots, chmf_prices, chmf_time, chmf_close, chmf_high, chmf_low, chmf_bvp, chmf_svp = [], [], [], [], [], [], [], [], []
chmf_data = {"Объем": chmf_volumes, "Лоты": chmf_lots, "Цена": chmf_prices, "Время": chmf_time, "Закрытие": chmf_close, "Хай": chmf_high, "Лоу": chmf_low, "Покупка": chmf_bvp, "Продажа": chmf_svp}
chmf_db = []

alrs_volumes, alrs_lots, alrs_prices, alrs_time, alrs_close, alrs_high, alrs_low, alrs_bvp, alrs_svp = [], [], [], [], [], [], [], [], []
alrs_data = {"Объем": alrs_volumes, "Лоты": alrs_lots, "Цена": alrs_prices, "Время": alrs_time, "Закрытие": alrs_close, "Хай": alrs_high, "Лоу": alrs_low, "Покупка": alrs_bvp, "Продажа": alrs_svp}
alrs_db = []

mmk_volumes, mmk_lots, mmk_prices, mmk_time, mmk_close, mmk_high, mmk_low, mmk_bvp, mmk_svp = [], [], [], [], [], [], [], [], []
mmk_data = {"Объем": mmk_volumes, "Лоты": mmk_lots, "Цена": mmk_prices, "Время": mmk_time, "Закрытие": mmk_close, "Хай": mmk_high, "Лоу": mmk_low, "Покупка": mmk_bvp, "Продажа": mmk_svp}
mmk_db = []

phor_volumes, phor_lots, phor_prices, phor_time, phor_close, phor_high, phor_low, phor_bvp, phor_svp = [], [], [], [], [], [], [], [], []
phor_data = {"Объем": phor_volumes, "Лоты": phor_lots, "Цена": phor_prices, "Время": phor_time, "Закрытие": phor_close, "Хай": phor_high, "Лоу": phor_low, "Покупка": phor_bvp, "Продажа": phor_svp}
phor_db = []

sngs_volumes, sngs_lots, sngs_prices, sngs_time, sngs_close, sngs_high, sngs_low, sngs_bvp, sngs_svp = [], [], [], [], [], [], [], [], []
sngs_data = {"Объем": sngs_volumes, "Лоты": sngs_lots, "Цена": sngs_prices, "Время": sngs_time, "Закрытие": sngs_close, "Хай": sngs_high, "Лоу": sngs_low, "Покупка": sngs_bvp, "Продажа": sngs_svp}
sngs_db = []

sngsp_volumes, sngsp_lots, sngsp_prices, sngsp_time, sngsp_close, sngsp_high, sngsp_low, sngsp_bvp, sngsp_svp = [], [], [], [], [], [], [], [], []
sngsp_data = {"Объем": sngsp_volumes, "Лоты": sngsp_lots, "Цена": sngsp_prices, "Время": sngsp_time, "Закрытие": sngsp_close, "Хай": sngsp_high, "Лоу": sngsp_low, "Покупка": sngsp_bvp, "Продажа": sngsp_svp}
sngsp_db = []

nlmk_volumes, nlmk_lots, nlmk_prices, nlmk_time, nlmk_close, nlmk_high, nlmk_low, nlmk_bvp, nlmk_svp = [], [], [], [], [], [], [], [], []
nlmk_data = {"Объем": nlmk_volumes, "Лоты": nlmk_lots, "Цена": nlmk_prices, "Время": nlmk_time, "Закрытие": nlmk_close, "Хай": nlmk_high, "Лоу": nlmk_low, "Покупка": nlmk_bvp, "Продажа": nlmk_svp}
nlmk_db = []

plzl_volumes, plzl_lots, plzl_prices, plzl_time, plzl_close, plzl_high, plzl_low, plzl_bvp, plzl_svp = [], [], [], [], [], [], [], [], []
plzl_data = {"Объем": plzl_volumes, "Лоты": plzl_lots, "Цена": plzl_prices, "Время": plzl_time, "Закрытие": plzl_close, "Хай": plzl_high, "Лоу": plzl_low, "Покупка": plzl_bvp, "Продажа": plzl_svp}
plzl_db = []

tatn_volumes, tatn_lots, tatn_prices, tatn_time, tatn_close, tatn_high, tatn_low, tatn_bvp, tatn_svp = [], [], [], [], [], [], [], [], []
tatn_data = {"Объем": tatn_volumes, "Лоты": tatn_lots, "Цена": tatn_prices, "Время": tatn_time, "Закрытие": tatn_close, "Хай": tatn_high, "Лоу": tatn_low, "Покупка": tatn_bvp, "Продажа": tatn_svp}
tatn_db = []

mtlr_volumes, mtlr_lots, mtlr_prices, mtlr_time, mtlr_close, mtlr_high, mtlr_low, mtlr_bvp, mtlr_svp = [], [], [], [], [], [], [], [], []
mtlr_data: dict[str, list] = {"Объем": mtlr_volumes, "Лоты": mtlr_lots, "Цена": mtlr_prices, "Время": mtlr_time, "Закрытие": mtlr_close, "Хай": mtlr_high, "Лоу": mtlr_low, "Покупка": mtlr_bvp, "Продажа": mtlr_svp}
mtlr_db: list = []

mtss_volumes, mtss_lots, mtss_prices, mtss_time, mtss_close, mtss_high, mtss_low, mtss_bvp, mtss_svp = [], [], [], [], [], [], [], [], []
mtss_data: dict[str, list] = {"Объем": mtss_volumes, "Лоты": mtss_lots, "Цена": mtss_prices, "Время": mtss_time, "Закрытие": mtss_close, "Хай": mtss_high, "Лоу": mtss_low, "Покупка": mtss_bvp, "Продажа": mtss_svp}
mtss_db: list = []

moex_volumes, moex_lots, moex_prices, moex_time, moex_close, moex_high, moex_low, moex_bvp, moex_svp = [], [], [], [], [], [], [], [], []
moex_data = {"Объем": moex_volumes, "Лоты": moex_lots, "Цена": moex_prices, "Время": moex_time, "Закрытие": moex_close, "Хай": moex_high, "Лоу": moex_low, "Покупка": moex_bvp, "Продажа": moex_svp}
moex_db = []

rual_volumes, rual_lots, rual_prices, rual_time, rual_close, rual_high, rual_low, rual_bvp, rual_svp = [], [], [], [], [], [], [], [], []
rual_data = {"Объем": rual_volumes, "Лоты": rual_lots, "Цена": rual_prices, "Время": rual_time, "Закрытие": rual_close, "Хай": rual_high, "Лоу": rual_low, "Покупка": rual_bvp, "Продажа": rual_svp}
rual_db = []

aflt_volumes, aflt_lots, aflt_prices, aflt_time, aflt_close, aflt_high, aflt_low, aflt_bvp, aflt_svp = [], [], [], [], [], [], [], [], []
aflt_data = {"Объем": aflt_volumes, "Лоты": aflt_lots, "Цена": aflt_prices, "Время": aflt_time, "Закрытие": aflt_close, "Хай": aflt_high, "Лоу": aflt_low, "Покупка": aflt_bvp, "Продажа": aflt_svp}
aflt_db = []

cbom_volumes, cbom_lots, cbom_prices, cbom_time, cbom_close, cbom_high, cbom_low, cbom_bvp, cbom_svp = [], [], [], [], [], [], [], [], []
cbom_data = {"Объем": cbom_volumes, "Лоты": cbom_lots, "Цена": cbom_prices, "Время": cbom_time, "Закрытие": cbom_close, "Хай": cbom_high, "Лоу": cbom_low, "Покупка": cbom_bvp, "Продажа": cbom_svp}
cbom_db = []

ozon_volumes, ozon_lots, ozon_prices, ozon_time, ozon_close, ozon_high, ozon_low, ozon_bvp, ozon_svp = [], [], [], [], [], [], [], [], []
ozon_data = {"Объем": ozon_volumes, "Лоты": ozon_lots, "Цена": ozon_prices, "Время": ozon_time, "Закрытие": ozon_close, "Хай": ozon_high, "Лоу": ozon_low, "Покупка": ozon_bvp, "Продажа": ozon_svp}
ozon_db = []

afks_volumes, afks_lots, afks_prices, afks_time, afks_close, afks_high, afks_low, afks_bvp, afks_svp = [], [], [], [], [], [], [], [], []
afks_data = {"Объем": afks_volumes, "Лоты": afks_lots, "Цена": afks_prices, "Время": afks_time, "Закрытие": afks_close, "Хай": afks_high, "Лоу": afks_low, "Покупка": afks_bvp, "Продажа": afks_svp}
afks_db = []

smlt_volumes, smlt_lots, smlt_prices, smlt_time, smlt_close, smlt_high, smlt_low, smlt_bvp, smlt_svp = [], [], [], [], [], [], [], [], []
smlt_data = {"Объем": smlt_volumes, "Лоты": smlt_lots, "Цена": smlt_prices, "Время": smlt_time, "Закрытие": smlt_close, "Хай": smlt_high, "Лоу": smlt_low, "Покупка": smlt_bvp, "Продажа": smlt_svp}
smlt_db = []

spbe_volumes, spbe_lots, spbe_prices, spbe_time, spbe_close, spbe_high, spbe_low, spbe_bvp, spbe_svp = [], [], [], [], [], [], [], [], []
spbe_data = {"Объем": spbe_volumes, "Лоты": spbe_lots, "Цена": spbe_prices, "Время": spbe_time, "Закрытие": spbe_close, "Хай": spbe_high, "Лоу": spbe_low, "Покупка": spbe_bvp, "Продажа": spbe_svp}
spbe_db = []

pikk_volumes, pikk_lots, pikk_prices, pikk_time, pikk_close, pikk_high, pikk_low, pikk_bvp, pikk_svp = [], [], [], [], [], [], [], [], []
pikk_data = {"Объем": pikk_volumes, "Лоты": pikk_lots, "Цена": pikk_prices, "Время": pikk_time, "Закрытие": pikk_close, "Хай": pikk_high, "Лоу": pikk_low, "Покупка": pikk_bvp, "Продажа": pikk_svp}
pikk_db = []

irao_volumes, irao_lots, irao_prices, irao_time, irao_close, irao_high, irao_low, irao_bvp, irao_svp = [], [], [], [], [], [], [], [], []
irao_data = {"Объем": irao_volumes, "Лоты": irao_lots, "Цена": irao_prices, "Время": irao_time, "Закрытие": irao_close, "Хай": irao_high, "Лоу": irao_low, "Покупка": irao_bvp, "Продажа": irao_svp}
irao_db = []

sibn_volumes, sibn_lots, sibn_prices, sibn_time, sibn_close, sibn_high, sibn_low, sibn_bvp, sibn_svp = [], [], [], [], [], [], [], [], []
sibn_data = {"Объем": sibn_volumes, "Лоты": sibn_lots, "Цена": sibn_prices, "Время": sibn_time, "Закрытие": sibn_close, "Хай": sibn_high, "Лоу": sibn_low, "Покупка": sibn_bvp, "Продажа": sibn_svp}
sibn_db = []

rasp_volumes, rasp_lots, rasp_prices, rasp_time, rasp_close, rasp_high, rasp_low, rasp_bvp, rasp_svp = [], [], [], [], [], [], [], [], []
rasp_data = {"Объем": rasp_volumes, "Лоты": rasp_lots, "Цена": rasp_prices, "Время": rasp_time, "Закрытие": rasp_close, "Хай": rasp_high, "Лоу": rasp_low, "Покупка": rasp_bvp, "Продажа": rasp_svp}
rasp_db = []

sgzh_volumes, sgzh_lots, sgzh_prices, sgzh_time, sgzh_close, sgzh_high, sgzh_low, sgzh_bvp, sgzh_svp = [], [], [], [], [], [], [], [], []
sgzh_data = {"Объем": sgzh_volumes, "Лоты": sgzh_lots, "Цена": sgzh_prices, "Время": sgzh_time, "Закрытие": sgzh_close, "Хай": sgzh_high, "Лоу": sgzh_low, "Покупка": sgzh_bvp, "Продажа": sgzh_svp}
sgzh_db = []

dsky_volumes, dsky_lots, dsky_prices, dsky_time, dsky_close, dsky_high, dsky_low, dsky_bvp, dsky_svp = [], [], [], [], [], [], [], [], []
dsky_data = {"Объем": dsky_volumes, "Лоты": dsky_lots, "Цена": dsky_prices, "Время": dsky_time, "Закрытие": dsky_close, "Хай": dsky_high, "Лоу": dsky_low, "Покупка": dsky_bvp, "Продажа": dsky_svp}
dsky_db = []

trnfp_volumes, trnfp_lots, trnfp_prices, trnfp_time, trnfp_close, trnfp_high, trnfp_low, trnfp_bvp, trnfp_svp = [], [], [], [], [], [], [], [], []
trnfp_data = {"Объем": trnfp_volumes, "Лоты": trnfp_lots, "Цена": trnfp_prices, "Время": trnfp_time, "Закрытие": trnfp_close, "Хай": trnfp_high, "Лоу": trnfp_low, "Покупка": trnfp_bvp, "Продажа": trnfp_svp}
trnfp_db = []

rnft_volumes, rnft_lots, rnft_prices, rnft_time, rnft_close, rnft_high, rnft_low, rnft_bvp, rnft_svp = [], [], [], [], [], [], [], [], []
rnft_data = {"Объем": rnft_volumes, "Лоты": rnft_lots, "Цена": rnft_prices, "Время": rnft_time, "Закрытие": rnft_close, "Хай": rnft_high, "Лоу": rnft_low, "Покупка": rnft_bvp, "Продажа": rnft_svp}
rnft_db = []

five_volumes, five_lots, five_prices, five_time, five_close, five_high, five_low, five_bvp, five_svp = [], [], [], [], [], [], [], [], []
five_data = {"Объем": five_volumes, "Лоты": five_lots, "Цена": five_prices, "Время": five_time, "Закрытие": five_close, "Хай": five_high, "Лоу": five_low, "Покупка": five_bvp, "Продажа": five_svp}
five_db = []

bspb_volumes, bspb_lots, bspb_prices, bspb_time, bspb_close, bspb_high, bspb_low, bspb_bvp, bspb_svp = [], [], [], [], [], [], [], [], []
bspb_data = {"Объем": bspb_volumes, "Лоты": bspb_lots, "Цена": bspb_prices, "Время": bspb_time, "Закрытие": bspb_close, "Хай": bspb_high, "Лоу": bspb_low, "Покупка": bspb_bvp, "Продажа": bspb_svp}
bspb_db = []

flot_volumes, flot_lots, flot_prices, flot_time, flot_close, flot_high, flot_low, flot_bvp, flot_svp = [], [], [], [], [], [], [], [], []
flot_data = {"Объем": flot_volumes, "Лоты": flot_lots, "Цена": flot_prices, "Время": flot_time, "Закрытие": flot_close, "Хай": flot_high, "Лоу": flot_low, "Покупка": flot_bvp, "Продажа": flot_svp}
flot_db = []

uwgn_volumes, uwgn_lots, uwgn_prices, uwgn_time, uwgn_close, uwgn_high, uwgn_low, uwgn_bvp, uwgn_svp = [], [], [], [], [], [], [], [], []
uwgn_data = {"Объем": uwgn_volumes, "Лоты": uwgn_lots, "Цена": uwgn_prices, "Время": uwgn_time, "Закрытие": uwgn_close, "Хай": uwgn_high, "Лоу": uwgn_low, "Покупка": uwgn_bvp, "Продажа": uwgn_svp}
uwgn_db = []

mtlrp_volumes, mtlrp_lots, mtlrp_prices, mtlrp_time, mtlrp_close, mtlrp_high, mtlrp_low, mtlrp_bvp, mtlrp_svp = [], [], [], [], [], [], [], [], []
mtlrp_data = {"Объем": mtlrp_volumes, "Лоты": mtlrp_lots, "Цена": mtlrp_prices, "Время": mtlrp_time, "Закрытие": mtlrp_close, "Хай": mtlrp_high, "Лоу": mtlrp_low, "Покупка": mtlrp_bvp, "Продажа": mtlrp_svp}
mtlrp_db = []

iskj_volumes, iskj_lots, iskj_prices, iskj_time, iskj_close, iskj_high, iskj_low, iskj_bvp, iskj_svp = [], [], [], [], [], [], [], [], []
iskj_data = {"Объем": iskj_volumes, "Лоты": iskj_lots, "Цена": iskj_prices, "Время": iskj_time, "Закрытие": iskj_close, "Хай": iskj_high, "Лоу": iskj_low, "Покупка": iskj_bvp, "Продажа": iskj_svp}
iskj_db = []

upro_volumes, upro_lots, upro_prices, upro_time, upro_close, upro_high, upro_low, upro_bvp, upro_svp = [], [], [], [], [], [], [], [], []
upro_data = {"Объем": upro_volumes, "Лоты": upro_lots, "Цена": upro_prices, "Время": upro_time, "Закрытие": upro_close, "Хай": upro_high, "Лоу": upro_low, "Покупка": upro_bvp, "Продажа": upro_svp}
upro_db = []

'''def check_abnormal_volumes_gazp():
    with Client(token=TINKOFF_TOKEN) as client:        
        # try to track abnormal volumes on Gazprom
        for candle in client.get_all_candles(
            figi=GAZP.figi,
            from_=now() - timedelta(days=1),
            interval=CandleInterval.CANDLE_INTERVAL_1_MIN,
        ):
            if quotation_to_decimal(candle.close) < 1:
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

                    final_stock_volume_rub = int(candle.volume * float(quotation_to_decimal(candle.close)))
                    gazp_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    gazp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    gazp_prices.append(float(quotation_to_decimal(candle.close)))
                    gazp_time.append(candle.time)
                    gazp_close.append(float(quotation_to_decimal(candle.close)))
                    gazp_high.append(float(quotation_to_decimal(candle.high)))
                    gazp_low.append(float(quotation_to_decimal(candle.low)))
                    gazp_bvp.append(BVP)
                    gazp_svp.append(SVP)

                    if len(gazp_volumes) > GAZP.length_of_df and len(gazp_lots) > GAZP.length_of_df and len(gazp_prices) > GAZP.length_of_df and len(gazp_time) > GAZP.length_of_df and len(gazp_close) > GAZP.length_of_df and len(gazp_high) > GAZP.length_of_df and len(gazp_low) > GAZP.length_of_df and len(gazp_bvp) > GAZP.length_of_df and len(gazp_svp) > GAZP.length_of_df:
                        del gazp_volumes[0]
                        del gazp_lots[0]
                        del gazp_prices[0]
                        del gazp_time[0]
                        del gazp_close[0]
                        del gazp_high[0]
                        del gazp_low[0]
                        del gazp_bvp[0]
                        del gazp_svp[0]

            else:
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
                
                    #final_stock_volume_rub = int(candle.volume * quotation_to_decimal(candle.close))
                    gazp_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    gazp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    gazp_prices.append(int(quotation_to_decimal(candle.close)))
                    gazp_time.append(candle.time)
                    gazp_close.append(float(quotation_to_decimal(candle.close)))
                    gazp_high.append(float(quotation_to_decimal(candle.high)))
                    gazp_low.append(float(quotation_to_decimal(candle.low)))
                    gazp_bvp.append(BVP)
                    gazp_svp.append(SVP)

                    if len(gazp_volumes) > GAZP.length_of_df and len(gazp_lots) > GAZP.length_of_df and len(gazp_prices) > GAZP.length_of_df and len(gazp_time) > GAZP.length_of_df and len(gazp_close) > GAZP.length_of_df and len(gazp_high) > GAZP.length_of_df and len(gazp_low) > GAZP.length_of_df and len(gazp_bvp) > GAZP.length_of_df and len(gazp_svp) > GAZP.length_of_df:
                        del gazp_volumes[0]
                        del gazp_lots[0]
                        del gazp_prices[0]
                        del gazp_time[0]
                        del gazp_close[0]
                        del gazp_high[0]
                        del gazp_low[0]
                        del gazp_bvp[0]
                        del gazp_svp[0]
        
        gazp_df = pd.DataFrame(gazp_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = gazp_df['Объем'].mean()
        volume_std = gazp_df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = gazp_df['Цена'].mean()
        prices_std = gazp_df['Цена'].std()
        
        abnormal_volume = (gazp_df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (gazp_df['Цена'].iloc[-1] - prices_mean) / prices_std
        
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
                if gazp_df["Покупка"].iloc[-1] > gazp_df["Продажа"].iloc[-1]:
                    if f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(gazp_df["Объем"].iloc[-1]))} ({gazp_df["Лоты"].iloc[-1]})\nПокупка: {gazp_df["Покупка"].iloc[-1]}% Продажа: {gazp_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(gazp_df["Время"].iloc[-1])}\nЦена: {gazp_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in gazp_db:
                        gazp_db.append(f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(gazp_df["Объем"].iloc[-1]))} ({gazp_df["Лоты"].iloc[-1]})\nПокупка: {gazp_df["Покупка"].iloc[-1]}% Продажа: {gazp_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(gazp_df["Время"].iloc[-1])}\nЦена: {gazp_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                        send_message(f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(gazp_df["Объем"].iloc[-1]))} ({gazp_df["Лоты"].iloc[-1]})\nПокупка: {gazp_df["Покупка"].iloc[-1]}% Продажа: {gazp_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(gazp_df["Время"].iloc[-1])}\nЦена: {gazp_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                        time.sleep(3)
                else:
                    if f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(gazp_df["Объем"].iloc[-1]))} ({gazp_df["Лоты"].iloc[-1]})\nПокупка: {gazp_df["Покупка"].iloc[-1]}% Продажа: {gazp_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(gazp_df["Время"].iloc[-1])}\nЦена: {gazp_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in gazp_db:
                        gazp_db.append(f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(gazp_df["Объем"].iloc[-1]))} ({gazp_df["Лоты"].iloc[-1]})\nПокупка: {gazp_df["Покупка"].iloc[-1]}% Продажа: {gazp_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(gazp_df["Время"].iloc[-1])}\nЦена: {gazp_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                        send_message(f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(gazp_df["Объем"].iloc[-1]))} ({gazp_df["Лоты"].iloc[-1]})\nПокупка: {gazp_df["Покупка"].iloc[-1]}% Продажа: {gazp_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(gazp_df["Время"].iloc[-1])}\nЦена: {gazp_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(gazp_df["Цена"].iloc[-1], gazp_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                        time.sleep(3)
    return 0                   

def check_abnormal_volumes_vtbr():
    with Client(token=TINKOFF_TOKEN) as client:        
        # try to track abnormal volumes on VTB Bank
        for candle in client.get_all_candles(
            figi=VTBR.figi,
            from_=now() - timedelta(days=2),
            interval=CandleInterval.CANDLE_INTERVAL_1_MIN,
        ):
            if quotation_to_decimal(candle.close) < 1:
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

                    final_stock_volume_rub = int(candle.volume * float(quotation_to_decimal(candle.close)))
                    vtbr_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    vtbr_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    vtbr_prices.append(float(quotation_to_decimal(candle.close)))
                    vtbr_time.append(candle.time)
                    vtbr_close.append(float(quotation_to_decimal(candle.close)))
                    vtbr_high.append(float(quotation_to_decimal(candle.high)))
                    vtbr_low.append(float(quotation_to_decimal(candle.low)))
                    vtbr_bvp.append(BVP)
                    vtbr_svp.append(SVP)

                    if len(vtbr_volumes) > VTBR.length_of_df and len(vtbr_lots) > VTBR.length_of_df and len(vtbr_prices) > VTBR.length_of_df and len(vtbr_time) > VTBR.length_of_df and len(vtbr_close) > VTBR.length_of_df and len(vtbr_high) > VTBR.length_of_df and len(vtbr_low) > VTBR.length_of_df and len(vtbr_bvp) > VTBR.length_of_df and len(vtbr_svp) > VTBR.length_of_df:
                        del vtbr_volumes[0]
                        del vtbr_lots[0]
                        del vtbr_prices[0]
                        del vtbr_time[0]
                        del vtbr_close[0]
                        del vtbr_high[0]
                        del vtbr_low[0]
                        del vtbr_bvp[0]
                        del vtbr_svp[0]

            else:
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
                
                    #final_stock_volume_rub = int(candle.volume * quotation_to_decimal(candle.close))
                    vtbr_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    vtbr_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    vtbr_prices.append(int(quotation_to_decimal(candle.close)))
                    vtbr_time.append(candle.time)
                    vtbr_close.append(float(quotation_to_decimal(candle.close)))
                    vtbr_high.append(float(quotation_to_decimal(candle.high)))
                    vtbr_low.append(float(quotation_to_decimal(candle.low)))
                    vtbr_bvp.append(BVP)
                    vtbr_svp.append(SVP)

                    if len(vtbr_volumes) > VTBR.length_of_df and len(vtbr_lots) > VTBR.length_of_df and len(vtbr_prices) > VTBR.length_of_df and len(vtbr_time) > VTBR.length_of_df and len(vtbr_close) > VTBR.length_of_df and len(vtbr_high) > VTBR.length_of_df and len(vtbr_low) > VTBR.length_of_df and len(vtbr_bvp) > VTBR.length_of_df and len(vtbr_svp) > VTBR.length_of_df:
                        del vtbr_volumes[0]
                        del vtbr_lots[0]
                        del vtbr_prices[0]
                        del vtbr_time[0]
                        del vtbr_close[0]
                        del vtbr_high[0]
                        del vtbr_low[0]
                        del vtbr_bvp[0]
                        del vtbr_svp[0]
        
        vtbr_df = pd.DataFrame(vtbr_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = vtbr_df['Объем'].mean()
        volume_std = vtbr_df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = vtbr_df['Цена'].mean()
        prices_std = vtbr_df['Цена'].std()
        
        abnormal_volume = (vtbr_df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (vtbr_df['Цена'].iloc[-1] - prices_mean) / prices_std

        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if vtbr_df["Покупка"].iloc[-1] > vtbr_df["Продажа"].iloc[-1]:
                if f'#{VTBR.ticker} {VTBR.name}\n🟩 Аномальный объем\n{calculate_net_change(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(vtbr_df["Объем"].iloc[-1])} ({vtbr_df["Лоты"].iloc[-1]})\nПокупка: {vtbr_df["Покупка"].iloc[-1]}% Продажа: {vtbr_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(vtbr_df["Время"].iloc[-1])}\nЦена: {vtbr_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in vtbr_db:
                    vtbr_db.append(f'#{VTBR.ticker} {VTBR.name}\n🟩 Аномальный объем\n{calculate_net_change(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(vtbr_df["Объем"].iloc[-1])} ({vtbr_df["Лоты"].iloc[-1]})\nПокупка: {vtbr_df["Покупка"].iloc[-1]}% Продажа: {vtbr_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(vtbr_df["Время"].iloc[-1])}\nЦена: {vtbr_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{VTBR.ticker} {VTBR.name}\n🟩 Аномальный объем\n{calculate_net_change(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(vtbr_df["Объем"].iloc[-1])} ({vtbr_df["Лоты"].iloc[-1]})\nПокупка: {vtbr_df["Покупка"].iloc[-1]}% Продажа: {vtbr_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(vtbr_df["Время"].iloc[-1])}\nЦена: {vtbr_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{VTBR.ticker} {VTBR.name}\n🔻 Аномальный объем\n{calculate_net_change(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(vtbr_df["Объем"].iloc[-1])} ({vtbr_df["Лоты"].iloc[-1]})\nПокупка: {vtbr_df["Покупка"].iloc[-1]}% Продажа: {vtbr_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(vtbr_df["Время"].iloc[-1])}\nЦена: {vtbr_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in vtbr_db:
                    vtbr_db.append(f'#{VTBR.ticker} {VTBR.name}\n🔻 Аномальный объем\n{calculate_net_change(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(vtbr_df["Объем"].iloc[-1])} ({vtbr_df["Лоты"].iloc[-1]})\nПокупка: {vtbr_df["Покупка"].iloc[-1]}% Продажа: {vtbr_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(vtbr_df["Время"].iloc[-1])}\nЦена: {vtbr_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{VTBR.ticker} {VTBR.name}\n🔻 Аномальный объем\n{calculate_net_change(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(vtbr_df["Объем"].iloc[-1])} ({vtbr_df["Лоты"].iloc[-1]})\nПокупка: {vtbr_df["Покупка"].iloc[-1]}% Продажа: {vtbr_df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(vtbr_df["Время"].iloc[-1])}\nЦена: {vtbr_df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(vtbr_df["Цена"].iloc[-1], vtbr_df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0'''

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
                    # and int(self.candles[-1].volume * quotation_to_decimal(self.candles[-1].close)) >= 700000
                    if self.figi == GAZP.figi:
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
                            #if f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(self.candles[-1].close)), int(quotation_to_decimal(self.candles[-1 - 1].close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(self.candles[-1].volume * quotation_to_decimal(self.candles[-1].close))))} ({get_final_lots(self.candles[-1].volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(self.candles[-1].time)}\nЦена: {int(quotation_to_decimal(self.candles[-1].close))} ₽\nЗаметил Баффет на Уораннах.' not in gazp_db:
                            #gazp_db.append(f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(self.candles[-1].close)), int(quotation_to_decimal(self.candles[-1 - 1].close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(self.candles[-1].volume * quotation_to_decimal(self.candles[-1].close))))} ({get_final_lots(self.candles[-1].volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(self.candles[-1].time)}\nЦена: {int(quotation_to_decimal(self.candles[-1].close))} ₽\nЗаметил Баффет на Уораннах.')
                            send_message(f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\nЗаметил Баффет на Уораннах.')
                            time.sleep(3)
                        else:
                            #if f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(self.candles[-1].close)), int(quotation_to_decimal(self.candles[-1 - 1].close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(self.candles[-1].volume * quotation_to_decimal(self.candles[-1].close))))} ({get_final_lots(self.candles[-1].volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(self.candles[-1].time)}\nЦена: {int(quotation_to_decimal(self.candles[-1].close))} ₽\nЗаметил Баффет на Уораннах.' not in gazp_db:
                            #gazp_db.append(f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(self.candles[-1].close)), int(quotation_to_decimal(self.candles[-1 - 1].close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(self.candles[-1].volume * quotation_to_decimal(self.candles[-1].close))))} ({get_final_lots(self.candles[-1].volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(self.candles[-1].time)}\nЦена: {int(quotation_to_decimal(self.candles[-1].close))} ₽\nЗаметил Баффет на Уораннах.')
                            send_message(f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(int(quotation_to_decimal(candle.close)), int(quotation_to_decimal(candle.close)))}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(int(candle.volume * quotation_to_decimal(candle.close))))} ({get_final_lots(candle.volume)})\nПокупка: {BVP}% Продажа: {SVP}%\nВремя: {convert_time_to_moscow(candle.time)}\nЦена: {int(quotation_to_decimal(candle.close))} ₽\nЗаметил Баффет на Уораннах.')
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
    portfolio = {GAZP.figi}
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