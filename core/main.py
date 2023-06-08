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

TOKEN: str = 't.b7eKSJEp3fpSiiv4mVt4fWwKIxaMHM1lDMtpGsPTeyl850b9Y4MluXYv-EQrj1vEu7QfkNwqGqGPfTW9N6EvTg'
TELEGRAM_TOKEN: str = '6202414503:AAGmVIVsV_WluHKzeRXbF89gHuK4rfgVJj8'
TELEGRAM_CHANNEL: str = '@warrenbaffetbot'


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


logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
mtlr_data = {"Объем": mtlr_volumes, "Лоты": mtlr_lots, "Цена": mtlr_prices, "Время": mtlr_time, "Закрытие": mtlr_close, "Хай": mtlr_high, "Лоу": mtlr_low, "Покупка": mtlr_bvp, "Продажа": mtlr_svp}
mtlr_db = []

mtss_volumes, mtss_lots, mtss_prices, mtss_time, mtss_close, mtss_high, mtss_low, mtss_bvp, mtss_svp = [], [], [], [], [], [], [], [], []
mtss_data = {"Объем": mtss_volumes, "Лоты": mtss_lots, "Цена": mtss_prices, "Время": mtss_time, "Закрытие": mtss_close, "Хай": mtss_high, "Лоу": mtss_low, "Покупка": mtss_bvp, "Продажа": mtss_svp}
mtss_db = []

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

def check_abnormal_volume_gazp():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Gazprom
        for candle in client.get_all_candles(
            figi=GAZP.figi,
            from_=now() - timedelta(days=90),
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
        
        df = pd.DataFrame(gazp_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in gazp_db:
                    gazp_db.append(f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{GAZP.ticker} {GAZP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in gazp_db:
                    gazp_db.append(f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{GAZP.ticker} {GAZP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_vtbr():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on VTB Bank
        for candle in client.get_all_candles(
            figi=VTBR.figi,
            from_=now() - timedelta(days=90),
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
        
        df = pd.DataFrame(vtbr_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{VTBR.ticker} {VTBR.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in vtbr_db:
                    vtbr_db.append(f'#{VTBR.ticker} {VTBR.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{VTBR.ticker} {VTBR.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{VTBR.ticker} {VTBR.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in vtbr_db:
                    vtbr_db.append(f'#{VTBR.ticker} {VTBR.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{VTBR.ticker} {VTBR.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_lkoh():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on LUKOIL
        for candle in client.get_all_candles(
            figi=LKOH.figi,
            from_=now() - timedelta(days=90),
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
                    lkoh_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    lkoh_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    lkoh_prices.append(float(quotation_to_decimal(candle.close)))
                    lkoh_time.append(candle.time)
                    lkoh_close.append(float(quotation_to_decimal(candle.close)))
                    lkoh_high.append(float(quotation_to_decimal(candle.high)))
                    lkoh_low.append(float(quotation_to_decimal(candle.low)))
                    lkoh_bvp.append(BVP)
                    lkoh_svp.append(SVP)

                    if len(lkoh_volumes) > LKOH.length_of_df and len(lkoh_lots) > LKOH.length_of_df and len(lkoh_prices) > LKOH.length_of_df and len(lkoh_time) > LKOH.length_of_df and len(lkoh_close) > LKOH.length_of_df and len(lkoh_high) > LKOH.length_of_df and len(lkoh_low) > LKOH.length_of_df and len(lkoh_bvp) > LKOH.length_of_df and len(lkoh_svp) > LKOH.length_of_df:
                        del lkoh_volumes[0]
                        del lkoh_lots[0]
                        del lkoh_prices[0]
                        del lkoh_time[0]
                        del lkoh_close[0]
                        del lkoh_high[0]
                        del lkoh_low[0]
                        del lkoh_bvp[0]
                        del lkoh_svp[0]

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
                    lkoh_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    lkoh_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    lkoh_prices.append(int(quotation_to_decimal(candle.close)))
                    lkoh_time.append(candle.time)
                    lkoh_close.append(float(quotation_to_decimal(candle.close)))
                    lkoh_high.append(float(quotation_to_decimal(candle.high)))
                    lkoh_low.append(float(quotation_to_decimal(candle.low)))
                    lkoh_bvp.append(BVP)
                    lkoh_svp.append(SVP)

                    if len(lkoh_volumes) > LKOH.length_of_df and len(lkoh_lots) > LKOH.length_of_df and len(lkoh_prices) > LKOH.length_of_df and len(lkoh_time) > LKOH.length_of_df and len(lkoh_close) > LKOH.length_of_df and len(lkoh_high) > LKOH.length_of_df and len(lkoh_low) > LKOH.length_of_df and len(lkoh_bvp) > LKOH.length_of_df and len(lkoh_svp) > LKOH.length_of_df:
                        del lkoh_volumes[0]
                        del lkoh_lots[0]
                        del lkoh_prices[0]
                        del lkoh_time[0]
                        del lkoh_close[0]
                        del lkoh_high[0]
                        del lkoh_low[0]
                        del lkoh_bvp[0]
                        del lkoh_svp[0]
        
        df = pd.DataFrame(lkoh_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{LKOH.ticker} {LKOH.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in lkoh_db:
                    lkoh_db.append(f'#{LKOH.ticker} {LKOH.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{LKOH.ticker} {LKOH.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{LKOH.ticker} {LKOH.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in lkoh_db:
                    lkoh_db.append(f'#{LKOH.ticker} {LKOH.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{LKOH.ticker} {LKOH.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_yndx():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Yandex Inc.
        for candle in client.get_all_candles(
            figi=YNDX.figi,
            from_=now() - timedelta(days=90),
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
                    yndx_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    yndx_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    yndx_prices.append(float(quotation_to_decimal(candle.close)))
                    yndx_time.append(candle.time)
                    yndx_close.append(float(quotation_to_decimal(candle.close)))
                    yndx_high.append(float(quotation_to_decimal(candle.high)))
                    yndx_low.append(float(quotation_to_decimal(candle.low)))
                    yndx_bvp.append(BVP)
                    yndx_svp.append(SVP)

                    if len(yndx_volumes) > YNDX.length_of_df and len(yndx_lots) > YNDX.length_of_df and len(yndx_prices) > YNDX.length_of_df and len(yndx_time) > YNDX.length_of_df and len(yndx_close) > YNDX.length_of_df and len(yndx_high) > YNDX.length_of_df and len(yndx_low) > YNDX.length_of_df and len(yndx_bvp) > YNDX.length_of_df and len(yndx_svp) > YNDX.length_of_df:
                        del yndx_volumes[0]
                        del yndx_lots[0]
                        del yndx_prices[0]
                        del yndx_time[0]
                        del yndx_close[0]
                        del yndx_high[0]
                        del yndx_low[0]
                        del yndx_bvp[0]
                        del yndx_svp[0]

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
                    yndx_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    yndx_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    yndx_prices.append(int(quotation_to_decimal(candle.close)))
                    yndx_time.append(candle.time)
                    yndx_close.append(float(quotation_to_decimal(candle.close)))
                    yndx_high.append(float(quotation_to_decimal(candle.high)))
                    yndx_low.append(float(quotation_to_decimal(candle.low)))
                    yndx_bvp.append(BVP)
                    yndx_svp.append(SVP)

                    if len(yndx_volumes) > YNDX.length_of_df and len(yndx_lots) > YNDX.length_of_df and len(yndx_prices) > YNDX.length_of_df and len(yndx_time) > YNDX.length_of_df and len(yndx_close) > YNDX.length_of_df and len(yndx_high) > YNDX.length_of_df and len(yndx_low) > YNDX.length_of_df and len(yndx_bvp) > YNDX.length_of_df and len(yndx_svp) > YNDX.length_of_df:
                        del yndx_volumes[0]
                        del yndx_lots[0]
                        del yndx_prices[0]
                        del yndx_time[0]
                        del yndx_close[0]
                        del yndx_high[0]
                        del yndx_low[0]
                        del yndx_bvp[0]
                        del yndx_svp[0]
        
        df = pd.DataFrame(yndx_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{YNDX.ticker} {YNDX.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in yndx_db:
                    yndx_db.append(f'#{YNDX.ticker} {YNDX.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{YNDX.ticker} {YNDX.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{YNDX.ticker} {YNDX.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in yndx_db:
                    yndx_db.append(f'#{YNDX.ticker} {YNDX.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{YNDX.ticker} {YNDX.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_mgnt():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Magnit
        for candle in client.get_all_candles(
            figi=MGNT.figi,
            from_=now() - timedelta(days=90),
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
                    mgnt_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    mgnt_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mgnt_prices.append(float(quotation_to_decimal(candle.close)))
                    mgnt_time.append(candle.time)
                    mgnt_close.append(float(quotation_to_decimal(candle.close)))
                    mgnt_high.append(float(quotation_to_decimal(candle.high)))
                    mgnt_low.append(float(quotation_to_decimal(candle.low)))
                    mgnt_bvp.append(BVP)
                    mgnt_svp.append(SVP)

                    if len(mgnt_volumes) > MGNT.length_of_df and len(mgnt_lots) > MGNT.length_of_df and len(mgnt_prices) > MGNT.length_of_df and len(mgnt_time) > MGNT.length_of_df and len(mgnt_close) > MGNT.length_of_df and len(mgnt_high) > MGNT.length_of_df and len(mgnt_low) > MGNT.length_of_df and len(mgnt_bvp) > MGNT.length_of_df and len(mgnt_svp) > MGNT.length_of_df:
                        del mgnt_volumes[0]
                        del mgnt_lots[0]
                        del mgnt_prices[0]
                        del mgnt_time[0]
                        del mgnt_close[0]
                        del mgnt_high[0]
                        del mgnt_low[0]
                        del mgnt_bvp[0]
                        del mgnt_svp[0]

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
                    mgnt_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    mgnt_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mgnt_prices.append(int(quotation_to_decimal(candle.close)))
                    mgnt_time.append(candle.time)
                    mgnt_close.append(float(quotation_to_decimal(candle.close)))
                    mgnt_high.append(float(quotation_to_decimal(candle.high)))
                    mgnt_low.append(float(quotation_to_decimal(candle.low)))
                    mgnt_bvp.append(BVP)
                    mgnt_svp.append(SVP)

                    if len(mgnt_volumes) > MGNT.length_of_df and len(mgnt_lots) > MGNT.length_of_df and len(mgnt_prices) > MGNT.length_of_df and len(mgnt_time) > MGNT.length_of_df and len(mgnt_close) > MGNT.length_of_df and len(mgnt_high) > MGNT.length_of_df and len(mgnt_low) > MGNT.length_of_df and len(mgnt_bvp) > MGNT.length_of_df and len(mgnt_svp) > MGNT.length_of_df:
                        del mgnt_volumes[0]
                        del mgnt_lots[0]
                        del mgnt_prices[0]
                        del mgnt_time[0]
                        del mgnt_close[0]
                        del mgnt_high[0]
                        del mgnt_low[0]
                        del mgnt_bvp[0]
                        del mgnt_svp[0]
        
        df = pd.DataFrame(mgnt_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{MGNT.ticker} {MGNT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in mgnt_db:
                    mgnt_db.append(f'#{MGNT.ticker} {MGNT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MGNT.ticker} {MGNT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{MGNT.ticker} {MGNT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in mgnt_db:
                    mgnt_db.append(f'#{MGNT.ticker} {MGNT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MGNT.ticker} {MGNT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_poly():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Polymetall
        for candle in client.get_all_candles(
            figi=POLY.figi,
            from_=now() - timedelta(days=90),
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
                    poly_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    poly_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    poly_prices.append(float(quotation_to_decimal(candle.close)))
                    poly_time.append(candle.time)
                    poly_close.append(float(quotation_to_decimal(candle.close)))
                    poly_high.append(float(quotation_to_decimal(candle.high)))
                    poly_low.append(float(quotation_to_decimal(candle.low)))
                    poly_bvp.append(BVP)
                    poly_svp.append(SVP)

                    if len(poly_volumes) > POLY.length_of_df and len(poly_lots) > POLY.length_of_df and len(poly_prices) > POLY.length_of_df and len(poly_time) > POLY.length_of_df and len(poly_close) > POLY.length_of_df and len(poly_high) > POLY.length_of_df and len(poly_low) > POLY.length_of_df and len(poly_bvp) > POLY.length_of_df and len(poly_svp) > POLY.length_of_df:
                        del poly_volumes[0]
                        del poly_lots[0]
                        del poly_prices[0]
                        del poly_time[0]
                        del poly_close[0]
                        del poly_high[0]
                        del poly_low[0]
                        del poly_bvp[0]
                        del poly_svp[0]

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
                    poly_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    poly_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    poly_prices.append(int(quotation_to_decimal(candle.close)))
                    poly_time.append(candle.time)
                    poly_close.append(float(quotation_to_decimal(candle.close)))
                    poly_high.append(float(quotation_to_decimal(candle.high)))
                    poly_low.append(float(quotation_to_decimal(candle.low)))
                    poly_bvp.append(BVP)
                    poly_svp.append(SVP)

                    if len(poly_volumes) > POLY.length_of_df and len(poly_lots) > POLY.length_of_df and len(poly_prices) > POLY.length_of_df and len(poly_time) > POLY.length_of_df and len(poly_close) > POLY.length_of_df and len(poly_high) > POLY.length_of_df and len(poly_low) > POLY.length_of_df and len(poly_bvp) > POLY.length_of_df and len(poly_svp) > POLY.length_of_df:
                        del poly_volumes[0]
                        del poly_lots[0]
                        del poly_prices[0]
                        del poly_time[0]
                        del poly_close[0]
                        del poly_high[0]
                        del poly_low[0]
                        del poly_bvp[0]
                        del poly_svp[0]
        
        df = pd.DataFrame(poly_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{POLY.ticker} {POLY.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in poly_db:
                    poly_db.append(f'#{POLY.ticker} {POLY.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{POLY.ticker} {POLY.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{POLY.ticker} {POLY.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in poly_db:
                    poly_db.append(f'#{POLY.ticker} {POLY.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{POLY.ticker} {POLY.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_sberp():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Sber bank prevs
        for candle in client.get_all_candles(
            figi=SBERP.figi,
            from_=now() - timedelta(days=90),
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
                    sberp_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    sberp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sberp_prices.append(float(quotation_to_decimal(candle.close)))
                    sberp_time.append(candle.time)
                    sberp_close.append(float(quotation_to_decimal(candle.close)))
                    sberp_high.append(float(quotation_to_decimal(candle.high)))
                    sberp_low.append(float(quotation_to_decimal(candle.low)))
                    sberp_bvp.append(BVP)
                    sberp_svp.append(SVP)

                    if len(sberp_volumes) > SBERP.length_of_df and len(sberp_lots) > SBERP.length_of_df and len(sberp_prices) > SBERP.length_of_df and len(sberp_time) > SBERP.length_of_df and len(sberp_close) > SBERP.length_of_df and len(sberp_high) > SBERP.length_of_df and len(sberp_low) > SBERP.length_of_df and len(sberp_bvp) > SBERP.length_of_df and len(sberp_svp) > SBERP.length_of_df:
                        del sberp_volumes[0]
                        del sberp_lots[0]
                        del sberp_prices[0]
                        del sberp_time[0]
                        del sberp_close[0]
                        del sberp_high[0]
                        del sberp_low[0]
                        del sberp_bvp[0]
                        del sberp_svp[0]

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
                    sberp_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    sberp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sberp_prices.append(int(quotation_to_decimal(candle.close)))
                    sberp_time.append(candle.time)
                    sberp_close.append(float(quotation_to_decimal(candle.close)))
                    sberp_high.append(float(quotation_to_decimal(candle.high)))
                    sberp_low.append(float(quotation_to_decimal(candle.low)))
                    sberp_bvp.append(BVP)
                    sberp_svp.append(SVP)

                    if len(sberp_volumes) > SBERP.length_of_df and len(sberp_lots) > SBERP.length_of_df and len(sberp_prices) > SBERP.length_of_df and len(sberp_time) > SBERP.length_of_df and len(sberp_close) > SBERP.length_of_df and len(sberp_high) > SBERP.length_of_df and len(sberp_low) > SBERP.length_of_df and len(sberp_bvp) > SBERP.length_of_df and len(sberp_svp) > SBERP.length_of_df:
                        del sberp_volumes[0]
                        del sberp_lots[0]
                        del sberp_prices[0]
                        del sberp_time[0]
                        del sberp_close[0]
                        del sberp_high[0]
                        del sberp_low[0]
                        del sberp_bvp[0]
                        del sberp_svp[0]
        
        df = pd.DataFrame(sberp_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{SBERP.ticker} {SBERP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sberp_db:
                    sberp_db.append(f'#{SBERP.ticker} {SBERP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SBERP.ticker} {SBERP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{SBERP.ticker} {SBERP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sberp_db:
                    sberp_db.append(f'#{SBERP.ticker} {SBERP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SBERP.ticker} {SBERP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_chmf():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Severstal
        for candle in client.get_all_candles(
            figi=CHMF.figi,
            from_=now() - timedelta(days=90),
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
                    chmf_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    chmf_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    chmf_prices.append(float(quotation_to_decimal(candle.close)))
                    chmf_time.append(candle.time)
                    chmf_close.append(float(quotation_to_decimal(candle.close)))
                    chmf_high.append(float(quotation_to_decimal(candle.high)))
                    chmf_low.append(float(quotation_to_decimal(candle.low)))
                    chmf_bvp.append(BVP)
                    chmf_svp.append(SVP)

                    if len(chmf_volumes) > CHMF.length_of_df and len(chmf_lots) > CHMF.length_of_df and len(chmf_prices) > CHMF.length_of_df and len(chmf_time) > CHMF.length_of_df and len(chmf_close) > CHMF.length_of_df and len(chmf_high) > CHMF.length_of_df and len(chmf_low) > CHMF.length_of_df and len(chmf_bvp) > CHMF.length_of_df and len(chmf_svp) > CHMF.length_of_df:
                        del chmf_volumes[0]
                        del chmf_lots[0]
                        del chmf_prices[0]
                        del chmf_time[0]
                        del chmf_close[0]
                        del chmf_high[0]
                        del chmf_low[0]
                        del chmf_bvp[0]
                        del chmf_svp[0]

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
                    chmf_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    chmf_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    chmf_prices.append(int(quotation_to_decimal(candle.close)))
                    chmf_time.append(candle.time)
                    chmf_close.append(float(quotation_to_decimal(candle.close)))
                    chmf_high.append(float(quotation_to_decimal(candle.high)))
                    chmf_low.append(float(quotation_to_decimal(candle.low)))
                    chmf_bvp.append(BVP)
                    chmf_svp.append(SVP)

                    if len(chmf_volumes) > CHMF.length_of_df and len(chmf_lots) > CHMF.length_of_df and len(chmf_prices) > CHMF.length_of_df and len(chmf_time) > CHMF.length_of_df and len(chmf_close) > CHMF.length_of_df and len(chmf_high) > CHMF.length_of_df and len(chmf_low) > CHMF.length_of_df and len(chmf_bvp) > CHMF.length_of_df and len(chmf_svp) > CHMF.length_of_df:
                        del chmf_volumes[0]
                        del chmf_lots[0]
                        del chmf_prices[0]
                        del chmf_time[0]
                        del chmf_close[0]
                        del chmf_high[0]
                        del chmf_low[0]
                        del chmf_bvp[0]
                        del chmf_svp[0]
        
        df = pd.DataFrame(chmf_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{CHMF.ticker} {CHMF.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in chmf_db:
                    chmf_db.append(f'#{CHMF.ticker} {CHMF.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{CHMF.ticker} {CHMF.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{CHMF.ticker} {CHMF.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in chmf_db:
                    chmf_db.append(f'#{CHMF.ticker} {CHMF.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{CHMF.ticker} {CHMF.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_alrs():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=ALRS.figi,
            from_=now() - timedelta(days=90),
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
                    alrs_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    alrs_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    alrs_prices.append(float(quotation_to_decimal(candle.close)))
                    alrs_time.append(candle.time)
                    alrs_close.append(float(quotation_to_decimal(candle.close)))
                    alrs_high.append(float(quotation_to_decimal(candle.high)))
                    alrs_low.append(float(quotation_to_decimal(candle.low)))
                    alrs_bvp.append(BVP)
                    alrs_svp.append(SVP)

                    if len(alrs_volumes) > ALRS.length_of_df and len(alrs_lots) > ALRS.length_of_df and len(alrs_prices) > ALRS.length_of_df and len(alrs_time) > ALRS.length_of_df and len(alrs_close) > ALRS.length_of_df and len(alrs_high) > ALRS.length_of_df and len(alrs_low) > ALRS.length_of_df and len(alrs_bvp) > ALRS.length_of_df and len(alrs_svp) > ALRS.length_of_df:
                        del alrs_volumes[0]
                        del alrs_lots[0]
                        del alrs_prices[0]
                        del alrs_time[0]
                        del alrs_close[0]
                        del alrs_high[0]
                        del alrs_low[0]
                        del alrs_bvp[0]
                        del alrs_svp[0]

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
                    alrs_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    alrs_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    alrs_prices.append(int(quotation_to_decimal(candle.close)))
                    alrs_time.append(candle.time)
                    alrs_close.append(float(quotation_to_decimal(candle.close)))
                    alrs_high.append(float(quotation_to_decimal(candle.high)))
                    alrs_low.append(float(quotation_to_decimal(candle.low)))
                    alrs_bvp.append(BVP)
                    alrs_svp.append(SVP)

                    if len(alrs_volumes) > ALRS.length_of_df and len(alrs_lots) > ALRS.length_of_df and len(alrs_prices) > ALRS.length_of_df and len(alrs_time) > ALRS.length_of_df and len(alrs_close) > ALRS.length_of_df and len(alrs_high) > ALRS.length_of_df and len(alrs_low) > ALRS.length_of_df and len(alrs_bvp) > ALRS.length_of_df and len(alrs_svp) > ALRS.length_of_df:
                        del alrs_volumes[0]
                        del alrs_lots[0]
                        del alrs_prices[0]
                        del alrs_time[0]
                        del alrs_close[0]
                        del alrs_high[0]
                        del alrs_low[0]
                        del alrs_bvp[0]
                        del alrs_svp[0]
        
        df = pd.DataFrame(alrs_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{ALRS.ticker} {ALRS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in alrs_db:
                    alrs_db.append(f'#{ALRS.ticker} {ALRS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{ALRS.ticker} {ALRS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{ALRS.ticker} {ALRS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in alrs_db:
                    alrs_db.append(f'#{ALRS.ticker} {ALRS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{ALRS.ticker} {ALRS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_mmk():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=MMK.figi,
            from_=now() - timedelta(days=90),
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
                    mmk_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    mmk_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mmk_prices.append(float(quotation_to_decimal(candle.close)))
                    mmk_time.append(candle.time)
                    mmk_close.append(float(quotation_to_decimal(candle.close)))
                    mmk_high.append(float(quotation_to_decimal(candle.high)))
                    mmk_low.append(float(quotation_to_decimal(candle.low)))
                    mmk_bvp.append(BVP)
                    mmk_svp.append(SVP)

                    if len(mmk_volumes) > MMK.length_of_df and len(mmk_lots) > MMK.length_of_df and len(mmk_prices) > MMK.length_of_df and len(mmk_time) > MMK.length_of_df and len(mmk_close) > MMK.length_of_df and len(mmk_high) > MMK.length_of_df and len(mmk_low) > MMK.length_of_df and len(mmk_bvp) > MMK.length_of_df and len(mmk_svp) > MMK.length_of_df:
                        del mmk_volumes[0]
                        del mmk_lots[0]
                        del mmk_prices[0]
                        del mmk_time[0]
                        del mmk_close[0]
                        del mmk_high[0]
                        del mmk_low[0]
                        del mmk_bvp[0]
                        del mmk_svp[0]

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
                    mmk_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    mmk_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mmk_prices.append(int(quotation_to_decimal(candle.close)))
                    mmk_time.append(candle.time)
                    mmk_close.append(float(quotation_to_decimal(candle.close)))
                    mmk_high.append(float(quotation_to_decimal(candle.high)))
                    mmk_low.append(float(quotation_to_decimal(candle.low)))
                    mmk_bvp.append(BVP)
                    mmk_svp.append(SVP)

                    if len(mmk_volumes) > MMK.length_of_df and len(mmk_lots) > MMK.length_of_df and len(mmk_prices) > MMK.length_of_df and len(mmk_time) > MMK.length_of_df and len(mmk_close) > MMK.length_of_df and len(mmk_high) > MMK.length_of_df and len(mmk_low) > MMK.length_of_df and len(mmk_bvp) > MMK.length_of_df and len(mmk_svp) > MMK.length_of_df:
                        del mmk_volumes[0]
                        del mmk_lots[0]
                        del mmk_prices[0]
                        del mmk_time[0]
                        del mmk_close[0]
                        del mmk_high[0]
                        del mmk_low[0]
                        del mmk_bvp[0]
                        del mmk_svp[0]
        
        df = pd.DataFrame(mmk_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{MMK.ticker} {MMK.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in mmk_db:
                    mmk_db.append(f'#{MMK.ticker} {MMK.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MMK.ticker} {MMK.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{MMK.ticker} {MMK.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in mmk_db:
                    mmk_db.append(f'#{MMK.ticker} {MMK.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MMK.ticker} {MMK.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_phor():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=PHOR.figi,
            from_=now() - timedelta(days=90),
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
                    phor_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    phor_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    phor_prices.append(float(quotation_to_decimal(candle.close)))
                    phor_time.append(candle.time)
                    phor_close.append(float(quotation_to_decimal(candle.close)))
                    phor_high.append(float(quotation_to_decimal(candle.high)))
                    phor_low.append(float(quotation_to_decimal(candle.low)))
                    phor_bvp.append(BVP)
                    phor_svp.append(SVP)

                    if len(phor_volumes) > PHOR.length_of_df and len(phor_lots) > PHOR.length_of_df and len(phor_prices) > PHOR.length_of_df and len(phor_time) > PHOR.length_of_df and len(phor_close) > PHOR.length_of_df and len(phor_high) > PHOR.length_of_df and len(phor_low) > PHOR.length_of_df and len(phor_bvp) > PHOR.length_of_df and len(phor_svp) > PHOR.length_of_df:
                        del phor_volumes[0]
                        del phor_lots[0]
                        del phor_prices[0]
                        del phor_time[0]
                        del phor_close[0]
                        del phor_high[0]
                        del phor_low[0]
                        del phor_bvp[0]
                        del phor_svp[0]

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
                    phor_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    phor_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    phor_prices.append(int(quotation_to_decimal(candle.close)))
                    phor_time.append(candle.time)
                    phor_close.append(float(quotation_to_decimal(candle.close)))
                    phor_high.append(float(quotation_to_decimal(candle.high)))
                    phor_low.append(float(quotation_to_decimal(candle.low)))
                    phor_bvp.append(BVP)
                    phor_svp.append(SVP)

                    if len(phor_volumes) > PHOR.length_of_df and len(phor_lots) > PHOR.length_of_df and len(phor_prices) > PHOR.length_of_df and len(phor_time) > PHOR.length_of_df and len(phor_close) > PHOR.length_of_df and len(phor_high) > PHOR.length_of_df and len(phor_low) > PHOR.length_of_df and len(phor_bvp) > PHOR.length_of_df and len(phor_svp) > PHOR.length_of_df:
                        del phor_volumes[0]
                        del phor_lots[0]
                        del phor_prices[0]
                        del phor_time[0]
                        del phor_close[0]
                        del phor_high[0]
                        del phor_low[0]
                        del phor_bvp[0]
                        del phor_svp[0]
        
        df = pd.DataFrame(phor_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{PHOR.ticker} {PHOR.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in phor_data:
                    phor_db.append(f'#{PHOR.ticker} {PHOR.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{PHOR.ticker} {PHOR.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{PHOR.ticker} {PHOR.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in phor_data:
                    phor_db.append(f'#{PHOR.ticker} {PHOR.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{PHOR.ticker} {PHOR.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_sngs():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=SNGS.figi,
            from_=now() - timedelta(days=90),
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
                    sngs_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    sngs_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sngs_prices.append(float(quotation_to_decimal(candle.close)))
                    sngs_time.append(candle.time)
                    sngs_close.append(float(quotation_to_decimal(candle.close)))
                    sngs_high.append(float(quotation_to_decimal(candle.high)))
                    sngs_low.append(float(quotation_to_decimal(candle.low)))
                    sngs_bvp.append(BVP)
                    sngs_svp.append(SVP)

                    if len(sngs_volumes) > SNGS.length_of_df and len(sngs_lots) > SNGS.length_of_df and len(sngs_prices) > SNGS.length_of_df and len(sngs_time) > SNGS.length_of_df and len(sngs_close) > SNGS.length_of_df and len(sngs_high) > SNGS.length_of_df and len(sngs_low) > SNGS.length_of_df and len(sngs_bvp) > SNGS.length_of_df and len(sngs_svp) > SNGS.length_of_df:
                        del sngs_volumes[0]
                        del sngs_lots[0]
                        del sngs_prices[0]
                        del sngs_time[0]
                        del sngs_close[0]
                        del sngs_high[0]
                        del sngs_low[0]
                        del sngs_bvp[0]
                        del sngs_svp[0]

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
                    sngs_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    sngs_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sngs_prices.append(int(quotation_to_decimal(candle.close)))
                    sngs_time.append(candle.time)
                    sngs_close.append(float(quotation_to_decimal(candle.close)))
                    sngs_high.append(float(quotation_to_decimal(candle.high)))
                    sngs_low.append(float(quotation_to_decimal(candle.low)))
                    sngs_bvp.append(BVP)
                    sngs_svp.append(SVP)

                    if len(sngs_volumes) > SNGS.length_of_df and len(sngs_lots) > SNGS.length_of_df and len(sngs_prices) > SNGS.length_of_df and len(sngs_time) > SNGS.length_of_df and len(sngs_close) > SNGS.length_of_df and len(sngs_high) > SNGS.length_of_df and len(sngs_low) > SNGS.length_of_df and len(sngs_bvp) > SNGS.length_of_df and len(sngs_svp) > SNGS.length_of_df:
                        del sngs_volumes[0]
                        del sngs_lots[0]
                        del sngs_prices[0]
                        del sngs_time[0]
                        del sngs_close[0]
                        del sngs_high[0]
                        del sngs_low[0]
                        del sngs_bvp[0]
                        del sngs_svp[0]
        
        df = pd.DataFrame(sngs_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{SNGS.ticker} {SNGS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sngs_db:
                    sngs_db.append(f'#{SNGS.ticker} {SNGS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SNGS.ticker} {SNGS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{SNGS.ticker} {SNGS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sngs_db:
                    sngs_db.append(f'#{SNGS.ticker} {SNGS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SNGS.ticker} {SNGS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_sngsp():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=SNGSP.figi,
            from_=now() - timedelta(days=90),
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
                    sngsp_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    sngsp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sngsp_prices.append(float(quotation_to_decimal(candle.close)))
                    sngsp_time.append(candle.time)
                    sngsp_close.append(float(quotation_to_decimal(candle.close)))
                    sngsp_high.append(float(quotation_to_decimal(candle.high)))
                    sngsp_low.append(float(quotation_to_decimal(candle.low)))
                    sngsp_bvp.append(BVP)
                    sngsp_svp.append(SVP)

                    if len(sngsp_volumes) > SNGSP.length_of_df and len(sngsp_lots) > SNGSP.length_of_df and len(sngsp_prices) > SNGSP.length_of_df and len(sngsp_time) > SNGSP.length_of_df and len(sngsp_close) > SNGSP.length_of_df and len(sngsp_high) > SNGSP.length_of_df and len(sngsp_low) > SNGSP.length_of_df and len(sngsp_bvp) > SNGSP.length_of_df and len(sngsp_svp) > SNGSP.length_of_df:
                        del sngsp_volumes[0]
                        del sngsp_lots[0]
                        del sngsp_prices[0]
                        del sngsp_time[0]
                        del sngsp_close[0]
                        del sngsp_high[0]
                        del sngsp_low[0]
                        del sngsp_bvp[0]
                        del sngsp_svp[0]

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
                    sngsp_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    sngsp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sngsp_prices.append(int(quotation_to_decimal(candle.close)))
                    sngsp_time.append(candle.time)
                    sngsp_close.append(float(quotation_to_decimal(candle.close)))
                    sngsp_high.append(float(quotation_to_decimal(candle.high)))
                    sngsp_low.append(float(quotation_to_decimal(candle.low)))
                    sngsp_bvp.append(BVP)
                    sngsp_svp.append(SVP)

                    if len(sngsp_volumes) > SNGSP.length_of_df and len(sngsp_lots) > SNGSP.length_of_df and len(sngsp_prices) > SNGSP.length_of_df and len(sngsp_time) > SNGSP.length_of_df and len(sngsp_close) > SNGSP.length_of_df and len(sngsp_high) > SNGSP.length_of_df and len(sngsp_low) > SNGSP.length_of_df and len(sngsp_bvp) > SNGSP.length_of_df and len(sngsp_svp) > SNGSP.length_of_df:
                        del sngsp_volumes[0]
                        del sngsp_lots[0]
                        del sngsp_prices[0]
                        del sngsp_time[0]
                        del sngsp_close[0]
                        del sngsp_high[0]
                        del sngsp_low[0]
                        del sngsp_bvp[0]
                        del sngsp_svp[0]
        
        df = pd.DataFrame(sngsp_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{SNGSP.ticker} {SNGSP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sngsp_db:
                    sngsp_db.append(f'#{SNGSP.ticker} {SNGSP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SNGSP.ticker} {SNGSP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{SNGSP.ticker} {SNGSP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sngsp_db:
                    sngsp_db.append(f'#{SNGSP.ticker} {SNGSP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SNGSP.ticker} {SNGSP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_sngs(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_nlmk():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=NLMK.figi,
            from_=now() - timedelta(days=90),
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
                    nlmk_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    nlmk_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    nlmk_prices.append(float(quotation_to_decimal(candle.close)))
                    nlmk_time.append(candle.time)
                    nlmk_close.append(float(quotation_to_decimal(candle.close)))
                    nlmk_high.append(float(quotation_to_decimal(candle.high)))
                    nlmk_low.append(float(quotation_to_decimal(candle.low)))
                    nlmk_bvp.append(BVP)
                    nlmk_svp.append(SVP)

                    if len(nlmk_volumes) > NLMK.length_of_df and len(nlmk_lots) > NLMK.length_of_df and len(nlmk_prices) > NLMK.length_of_df and len(nlmk_time) > NLMK.length_of_df and len(nlmk_close) > NLMK.length_of_df and len(nlmk_high) > NLMK.length_of_df and len(nlmk_low) > NLMK.length_of_df and len(nlmk_bvp) > NLMK.length_of_df and len(nlmk_svp) > NLMK.length_of_df:
                        del nlmk_volumes[0]
                        del nlmk_lots[0]
                        del nlmk_prices[0]
                        del nlmk_time[0]
                        del nlmk_close[0]
                        del nlmk_high[0]
                        del nlmk_low[0]
                        del nlmk_bvp[0]
                        del nlmk_svp[0]

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
                    nlmk_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    nlmk_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    nlmk_prices.append(int(quotation_to_decimal(candle.close)))
                    nlmk_time.append(candle.time)
                    nlmk_close.append(float(quotation_to_decimal(candle.close)))
                    nlmk_high.append(float(quotation_to_decimal(candle.high)))
                    nlmk_low.append(float(quotation_to_decimal(candle.low)))
                    nlmk_bvp.append(BVP)
                    nlmk_svp.append(SVP)

                    if len(nlmk_volumes) > NLMK.length_of_df and len(nlmk_lots) > NLMK.length_of_df and len(nlmk_prices) > NLMK.length_of_df and len(nlmk_time) > NLMK.length_of_df and len(nlmk_close) > NLMK.length_of_df and len(nlmk_high) > NLMK.length_of_df and len(nlmk_low) > NLMK.length_of_df and len(nlmk_bvp) > NLMK.length_of_df and len(nlmk_svp) > NLMK.length_of_df:
                        del nlmk_volumes[0]
                        del nlmk_lots[0]
                        del nlmk_prices[0]
                        del nlmk_time[0]
                        del nlmk_close[0]
                        del nlmk_high[0]
                        del nlmk_low[0]
                        del nlmk_bvp[0]
                        del nlmk_svp[0]
        
        df = pd.DataFrame(nlmk_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{NLMK.ticker} {NLMK.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in nlmk_db:
                    nlmk_db.append(f'#{NLMK.ticker} {NLMK.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{NLMK.ticker} {NLMK.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{NLMK.ticker} {NLMK.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in nlmk_db:
                    nlmk_db.append(f'#{NLMK.ticker} {NLMK.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{NLMK.ticker} {NLMK.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_plzl():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=PLZL.figi,
            from_=now() - timedelta(days=90),
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
                    plzl_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    plzl_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    plzl_prices.append(float(quotation_to_decimal(candle.close)))
                    plzl_time.append(candle.time)
                    plzl_close.append(float(quotation_to_decimal(candle.close)))
                    plzl_high.append(float(quotation_to_decimal(candle.high)))
                    plzl_low.append(float(quotation_to_decimal(candle.low)))
                    plzl_bvp.append(BVP)
                    plzl_svp.append(SVP)

                    if len(plzl_volumes) > PLZL.length_of_df and len(plzl_lots) > PLZL.length_of_df and len(plzl_prices) > PLZL.length_of_df and len(plzl_time) > PLZL.length_of_df and len(plzl_close) > PLZL.length_of_df and len(plzl_high) > PLZL.length_of_df and len(plzl_low) > PLZL.length_of_df and len(plzl_bvp) > PLZL.length_of_df and len(plzl_svp) > PLZL.length_of_df:
                        del plzl_volumes[0]
                        del plzl_lots[0]
                        del plzl_prices[0]
                        del plzl_time[0]
                        del plzl_close[0]
                        del plzl_high[0]
                        del plzl_low[0]
                        del plzl_bvp[0]
                        del plzl_svp[0]

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
                    plzl_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    plzl_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    plzl_prices.append(int(quotation_to_decimal(candle.close)))
                    plzl_time.append(candle.time)
                    plzl_close.append(float(quotation_to_decimal(candle.close)))
                    plzl_high.append(float(quotation_to_decimal(candle.high)))
                    plzl_low.append(float(quotation_to_decimal(candle.low)))
                    plzl_bvp.append(BVP)
                    plzl_svp.append(SVP)

                    if len(plzl_volumes) > PLZL.length_of_df and len(plzl_lots) > PLZL.length_of_df and len(plzl_prices) > PLZL.length_of_df and len(plzl_time) > PLZL.length_of_df and len(plzl_close) > PLZL.length_of_df and len(plzl_high) > PLZL.length_of_df and len(plzl_low) > PLZL.length_of_df and len(plzl_bvp) > PLZL.length_of_df and len(plzl_svp) > PLZL.length_of_df:
                        del plzl_volumes[0]
                        del plzl_lots[0]
                        del plzl_prices[0]
                        del plzl_time[0]
                        del plzl_close[0]
                        del plzl_high[0]
                        del plzl_low[0]
                        del plzl_bvp[0]
                        del plzl_svp[0]
        
        df = pd.DataFrame(plzl_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{PLZL.ticker} {PLZL.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in plzl_db:
                    plzl_db.append(f'#{PLZL.ticker} {PLZL.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{PLZL.ticker} {PLZL.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{PLZL.ticker} {PLZL.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in plzl_db:
                    plzl_db.append(f'#{PLZL.ticker} {PLZL.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{PLZL.ticker} {PLZL.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_tatn():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=TATN.figi,
            from_=now() - timedelta(days=90),
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
                    tatn_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    tatn_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    tatn_prices.append(float(quotation_to_decimal(candle.close)))
                    tatn_time.append(candle.time)
                    tatn_close.append(float(quotation_to_decimal(candle.close)))
                    tatn_high.append(float(quotation_to_decimal(candle.high)))
                    tatn_low.append(float(quotation_to_decimal(candle.low)))
                    tatn_bvp.append(BVP)
                    tatn_svp.append(SVP)

                    if len(tatn_volumes) > TATN.length_of_df and len(tatn_lots) > TATN.length_of_df and len(tatn_prices) > TATN.length_of_df and len(tatn_time) > TATN.length_of_df and len(tatn_close) > TATN.length_of_df and len(tatn_high) > TATN.length_of_df and len(tatn_low) > TATN.length_of_df and len(tatn_bvp) > TATN.length_of_df and len(tatn_svp) > TATN.length_of_df:
                        del tatn_volumes[0]
                        del tatn_lots[0]
                        del tatn_prices[0]
                        del tatn_time[0]
                        del tatn_close[0]
                        del tatn_high[0]
                        del tatn_low[0]
                        del tatn_bvp[0]
                        del tatn_svp[0]

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
                    tatn_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    tatn_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    tatn_prices.append(int(quotation_to_decimal(candle.close)))
                    tatn_time.append(candle.time)
                    tatn_close.append(float(quotation_to_decimal(candle.close)))
                    tatn_high.append(float(quotation_to_decimal(candle.high)))
                    tatn_low.append(float(quotation_to_decimal(candle.low)))
                    tatn_bvp.append(BVP)
                    tatn_svp.append(SVP)

                    if len(tatn_volumes) > TATN.length_of_df and len(tatn_lots) > TATN.length_of_df and len(tatn_prices) > TATN.length_of_df and len(tatn_time) > TATN.length_of_df and len(tatn_close) > TATN.length_of_df and len(tatn_high) > TATN.length_of_df and len(tatn_low) > TATN.length_of_df and len(tatn_bvp) > TATN.length_of_df and len(tatn_svp) > TATN.length_of_df:
                        del tatn_volumes[0]
                        del tatn_lots[0]
                        del tatn_prices[0]
                        del tatn_time[0]
                        del tatn_close[0]
                        del tatn_high[0]
                        del tatn_low[0]
                        del tatn_bvp[0]
                        del tatn_svp[0]
        
        df = pd.DataFrame(tatn_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{TATN.ticker} {TATN.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in tatn_db:
                    tatn_db.append(f'#{TATN.ticker} {TATN.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{TATN.ticker} {TATN.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{TATN.ticker} {TATN.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in tatn_db:
                    tatn_db.append(f'#{TATN.ticker} {TATN.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{TATN.ticker} {TATN.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_mtlr():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=MTLR.figi,
            from_=now() - timedelta(days=90),
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
                    mtlr_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    mtlr_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mtlr_prices.append(float(quotation_to_decimal(candle.close)))
                    mtlr_time.append(candle.time)
                    mtlr_close.append(float(quotation_to_decimal(candle.close)))
                    mtlr_high.append(float(quotation_to_decimal(candle.high)))
                    mtlr_low.append(float(quotation_to_decimal(candle.low)))
                    mtlr_bvp.append(BVP)
                    mtlr_svp.append(SVP)

                    if len(mtlr_volumes) > MTLR.length_of_df and len(mtlr_lots) > MTLR.length_of_df and len(mtlr_prices) > MTLR.length_of_df and len(mtlr_time) > MTLR.length_of_df and len(mtlr_close) > MTLR.length_of_df and len(mtlr_high) > MTLR.length_of_df and len(mtlr_low) > MTLR.length_of_df and len(mtlr_bvp) > MTLR.length_of_df and len(mtlr_svp) > MTLR.length_of_df:
                        del mtlr_volumes[0]
                        del mtlr_lots[0]
                        del mtlr_prices[0]
                        del mtlr_time[0]
                        del mtlr_close[0]
                        del mtlr_high[0]
                        del mtlr_low[0]
                        del mtlr_bvp[0]
                        del mtlr_svp[0]

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
                    mtlr_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    mtlr_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mtlr_prices.append(int(quotation_to_decimal(candle.close)))
                    mtlr_time.append(candle.time)
                    mtlr_close.append(float(quotation_to_decimal(candle.close)))
                    mtlr_high.append(float(quotation_to_decimal(candle.high)))
                    mtlr_low.append(float(quotation_to_decimal(candle.low)))
                    mtlr_bvp.append(BVP)
                    mtlr_svp.append(SVP)

                    if len(mtlr_volumes) > MTLR.length_of_df and len(mtlr_lots) > MTLR.length_of_df and len(mtlr_prices) > MTLR.length_of_df and len(mtlr_time) > MTLR.length_of_df and len(mtlr_close) > MTLR.length_of_df and len(mtlr_high) > MTLR.length_of_df and len(mtlr_low) > MTLR.length_of_df and len(mtlr_bvp) > MTLR.length_of_df and len(mtlr_svp) > MTLR.length_of_df:
                        del mtlr_volumes[0]
                        del mtlr_lots[0]
                        del mtlr_prices[0]
                        del mtlr_time[0]
                        del mtlr_close[0]
                        del mtlr_high[0]
                        del mtlr_low[0]
                        del mtlr_bvp[0]
                        del mtlr_svp[0]
        
        df = pd.DataFrame(mtlr_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{MTLR.ticker} {MTLR.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in mtlr_db:
                    mtlr_db.append(f'#{MTLR.ticker} {MTLR.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MTLR.ticker} {MTLR.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{MTLR.ticker} {MTLR.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in mtlr_db:
                    mtlr_db.append(f'#{MTLR.ticker} {MTLR.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MTLR.ticker} {MTLR.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_mtss():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=MTSS.figi,
            from_=now() - timedelta(days=90),
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
                    mtss_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    mtss_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mtss_prices.append(float(quotation_to_decimal(candle.close)))
                    mtss_time.append(candle.time)
                    mtss_close.append(float(quotation_to_decimal(candle.close)))
                    mtss_high.append(float(quotation_to_decimal(candle.high)))
                    mtss_low.append(float(quotation_to_decimal(candle.low)))
                    mtss_bvp.append(BVP)
                    mtss_svp.append(SVP)

                    if len(mtss_volumes) > MTSS.length_of_df and len(mtss_lots) > MTSS.length_of_df and len(mtss_prices) > MTSS.length_of_df and len(mtss_time) > MTSS.length_of_df and len(mtss_close) > MTSS.length_of_df and len(mtss_high) > MTSS.length_of_df and len(mtss_low) > MTSS.length_of_df and len(mtss_bvp) > MTSS.length_of_df and len(mtss_svp) > MTSS.length_of_df:
                        del mtss_volumes[0]
                        del mtss_lots[0]
                        del mtss_prices[0]
                        del mtss_time[0]
                        del mtss_close[0]
                        del mtss_high[0]
                        del mtss_low[0]
                        del mtss_bvp[0]
                        del mtss_svp[0]

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
                    mtss_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    mtss_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mtss_prices.append(int(quotation_to_decimal(candle.close)))
                    mtss_time.append(candle.time)
                    mtss_close.append(float(quotation_to_decimal(candle.close)))
                    mtss_high.append(float(quotation_to_decimal(candle.high)))
                    mtss_low.append(float(quotation_to_decimal(candle.low)))
                    mtss_bvp.append(BVP)
                    mtss_svp.append(SVP)

                    if len(mtss_volumes) > MTSS.length_of_df and len(mtss_lots) > MTSS.length_of_df and len(mtss_prices) > MTSS.length_of_df and len(mtss_time) > MTSS.length_of_df and len(mtss_close) > MTSS.length_of_df and len(mtss_high) > MTSS.length_of_df and len(mtss_low) > MTSS.length_of_df and len(mtss_bvp) > MTSS.length_of_df and len(mtss_svp) > MTSS.length_of_df:
                        del mtss_volumes[0]
                        del mtss_lots[0]
                        del mtss_prices[0]
                        del mtss_time[0]
                        del mtss_close[0]
                        del mtss_high[0]
                        del mtss_low[0]
                        del mtss_bvp[0]
                        del mtss_svp[0]
        
        df = pd.DataFrame(mtss_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{MTSS.ticker} {MTSS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in mtss_db:
                    mtss_db.append(f'#{MTSS.ticker} {MTSS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MTSS.ticker} {MTSS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{MTSS.ticker} {MTSS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in mtss_db:
                    mtss_db.append(f'#{MTSS.ticker} {MTSS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MTSS.ticker} {MTSS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_moex():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=MOEX.figi,
            from_=now() - timedelta(days=90),
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
                    moex_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    moex_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    moex_prices.append(float(quotation_to_decimal(candle.close)))
                    moex_time.append(candle.time)
                    moex_close.append(float(quotation_to_decimal(candle.close)))
                    moex_high.append(float(quotation_to_decimal(candle.high)))
                    moex_low.append(float(quotation_to_decimal(candle.low)))
                    moex_bvp.append(BVP)
                    moex_svp.append(SVP)

                    if len(moex_volumes) > MOEX.length_of_df and len(moex_lots) > MOEX.length_of_df and len(moex_prices) > MOEX.length_of_df and len(moex_time) > MOEX.length_of_df and len(moex_close) > MOEX.length_of_df and len(moex_high) > MOEX.length_of_df and len(moex_low) > MOEX.length_of_df and len(moex_bvp) > MOEX.length_of_df and len(moex_svp) > MOEX.length_of_df:
                        del moex_volumes[0]
                        del moex_lots[0]
                        del moex_prices[0]
                        del moex_time[0]
                        del moex_close[0]
                        del moex_high[0]
                        del moex_low[0]
                        del moex_bvp[0]
                        del moex_svp[0]

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
                    moex_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    moex_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    moex_prices.append(int(quotation_to_decimal(candle.close)))
                    moex_time.append(candle.time)
                    moex_close.append(float(quotation_to_decimal(candle.close)))
                    moex_high.append(float(quotation_to_decimal(candle.high)))
                    moex_low.append(float(quotation_to_decimal(candle.low)))
                    moex_bvp.append(BVP)
                    moex_svp.append(SVP)

                    if len(moex_volumes) > MOEX.length_of_df and len(moex_lots) > MOEX.length_of_df and len(moex_prices) > MOEX.length_of_df and len(moex_time) > MOEX.length_of_df and len(moex_close) > MOEX.length_of_df and len(moex_high) > MOEX.length_of_df and len(moex_low) > MOEX.length_of_df and len(moex_bvp) > MOEX.length_of_df and len(moex_svp) > MOEX.length_of_df:
                        del moex_volumes[0]
                        del moex_lots[0]
                        del moex_prices[0]
                        del moex_time[0]
                        del moex_close[0]
                        del moex_high[0]
                        del moex_low[0]
                        del moex_bvp[0]
                        del moex_svp[0]
        
        df = pd.DataFrame(moex_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{MOEX.ticker} {MOEX.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in moex_db:
                    moex_db.append(f'#{MOEX.ticker} {MOEX.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MOEX.ticker} {MOEX.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{MOEX.ticker} {MOEX.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in moex_db:
                    moex_db.append(f'#{MOEX.ticker} {MOEX.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{MOEX.ticker} {MOEX.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_rual():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=RUAL.figi,
            from_=now() - timedelta(days=90),
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
                    rual_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    rual_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    rual_prices.append(float(quotation_to_decimal(candle.close)))
                    rual_time.append(candle.time)
                    rual_close.append(float(quotation_to_decimal(candle.close)))
                    rual_high.append(float(quotation_to_decimal(candle.high)))
                    rual_low.append(float(quotation_to_decimal(candle.low)))
                    rual_bvp.append(BVP)
                    rual_svp.append(SVP)

                    if len(rual_volumes) > RUAL.length_of_df and len(rual_lots) > RUAL.length_of_df and len(rual_prices) > RUAL.length_of_df and len(rual_time) > RUAL.length_of_df and len(rual_close) > RUAL.length_of_df and len(rual_high) > RUAL.length_of_df and len(rual_low) > RUAL.length_of_df and len(rual_bvp) > RUAL.length_of_df and len(rual_svp) > RUAL.length_of_df:
                        del rual_volumes[0]
                        del rual_lots[0]
                        del rual_prices[0]
                        del rual_time[0]
                        del rual_close[0]
                        del rual_high[0]
                        del rual_low[0]
                        del rual_bvp[0]
                        del rual_svp[0]

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
                    rual_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    rual_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    rual_prices.append(int(quotation_to_decimal(candle.close)))
                    rual_time.append(candle.time)
                    rual_close.append(float(quotation_to_decimal(candle.close)))
                    rual_high.append(float(quotation_to_decimal(candle.high)))
                    rual_low.append(float(quotation_to_decimal(candle.low)))
                    rual_bvp.append(BVP)
                    rual_svp.append(SVP)

                    if len(rual_volumes) > RUAL.length_of_df and len(rual_lots) > RUAL.length_of_df and len(rual_prices) > RUAL.length_of_df and len(rual_time) > RUAL.length_of_df and len(rual_close) > RUAL.length_of_df and len(rual_high) > RUAL.length_of_df and len(rual_low) > RUAL.length_of_df and len(rual_bvp) > RUAL.length_of_df and len(rual_svp) > RUAL.length_of_df:
                        del rual_volumes[0]
                        del rual_lots[0]
                        del rual_prices[0]
                        del rual_time[0]
                        del rual_close[0]
                        del rual_high[0]
                        del rual_low[0]
                        del rual_bvp[0]
                        del rual_svp[0]
        
        df = pd.DataFrame(rual_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{RUAL.ticker} {RUAL.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in rual_db:
                    rual_db.append(f'#{RUAL.ticker} {RUAL.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{RUAL.ticker} {RUAL.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{RUAL.ticker} {RUAL.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in rual_db:
                    rual_db.append(f'#{RUAL.ticker} {RUAL.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{RUAL.ticker} {RUAL.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_aflt():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=AFLT.figi,
            from_=now() - timedelta(days=90),
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
                    aflt_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    aflt_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    aflt_prices.append(float(quotation_to_decimal(candle.close)))
                    aflt_time.append(candle.time)
                    aflt_close.append(float(quotation_to_decimal(candle.close)))
                    aflt_high.append(float(quotation_to_decimal(candle.high)))
                    aflt_low.append(float(quotation_to_decimal(candle.low)))
                    aflt_bvp.append(BVP)
                    aflt_svp.append(SVP)

                    if len(aflt_volumes) > AFLT.length_of_df and len(aflt_lots) > AFLT.length_of_df and len(aflt_prices) > AFLT.length_of_df and len(aflt_time) > AFLT.length_of_df and len(aflt_close) > AFLT.length_of_df and len(aflt_high) > AFLT.length_of_df and len(aflt_low) > AFLT.length_of_df and len(aflt_bvp) > AFLT.length_of_df and len(aflt_svp) > AFLT.length_of_df:
                        del aflt_volumes[0]
                        del aflt_lots[0]
                        del aflt_prices[0]
                        del aflt_time[0]
                        del aflt_close[0]
                        del aflt_high[0]
                        del aflt_low[0]
                        del aflt_bvp[0]
                        del aflt_svp[0]

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
                    aflt_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    aflt_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    aflt_prices.append(int(quotation_to_decimal(candle.close)))
                    aflt_time.append(candle.time)
                    aflt_close.append(float(quotation_to_decimal(candle.close)))
                    aflt_high.append(float(quotation_to_decimal(candle.high)))
                    aflt_low.append(float(quotation_to_decimal(candle.low)))
                    aflt_bvp.append(BVP)
                    aflt_svp.append(SVP)

                    if len(aflt_volumes) > AFLT.length_of_df and len(aflt_lots) > AFLT.length_of_df and len(aflt_prices) > AFLT.length_of_df and len(aflt_time) > AFLT.length_of_df and len(aflt_close) > AFLT.length_of_df and len(aflt_high) > AFLT.length_of_df and len(aflt_low) > AFLT.length_of_df and len(aflt_bvp) > AFLT.length_of_df and len(aflt_svp) > AFLT.length_of_df:
                        del aflt_volumes[0]
                        del aflt_lots[0]
                        del aflt_prices[0]
                        del aflt_time[0]
                        del aflt_close[0]
                        del aflt_high[0]
                        del aflt_low[0]
                        del aflt_bvp[0]
                        del aflt_svp[0]
        
        df = pd.DataFrame(aflt_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{AFLT.ticker} {AFLT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in aflt_db:
                    aflt_db.append(f'#{AFLT.ticker} {AFLT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{AFLT.ticker} {AFLT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{AFLT.ticker} {AFLT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in aflt_db:
                    aflt_db.append(f'#{AFLT.ticker} {AFLT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{AFLT.ticker} {AFLT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_cbom():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=CBOM.figi,
            from_=now() - timedelta(days=90),
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
                    cbom_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    cbom_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    cbom_prices.append(float(quotation_to_decimal(candle.close)))
                    cbom_time.append(candle.time)
                    cbom_close.append(float(quotation_to_decimal(candle.close)))
                    cbom_high.append(float(quotation_to_decimal(candle.high)))
                    cbom_low.append(float(quotation_to_decimal(candle.low)))
                    cbom_bvp.append(BVP)
                    cbom_svp.append(SVP)

                    if len(cbom_volumes) > CBOM.length_of_df and len(cbom_lots) > CBOM.length_of_df and len(cbom_prices) > CBOM.length_of_df and len(cbom_time) > CBOM.length_of_df and len(cbom_close) > CBOM.length_of_df and len(cbom_high) > CBOM.length_of_df and len(cbom_low) > CBOM.length_of_df and len(cbom_bvp) > CBOM.length_of_df and len(cbom_svp) > CBOM.length_of_df:
                        del cbom_volumes[0]
                        del cbom_lots[0]
                        del cbom_prices[0]
                        del cbom_time[0]
                        del cbom_close[0]
                        del cbom_high[0]
                        del cbom_low[0]
                        del cbom_bvp[0]
                        del cbom_svp[0]

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
                    cbom_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    cbom_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    cbom_prices.append(int(quotation_to_decimal(candle.close)))
                    cbom_time.append(candle.time)
                    cbom_close.append(float(quotation_to_decimal(candle.close)))
                    cbom_high.append(float(quotation_to_decimal(candle.high)))
                    cbom_low.append(float(quotation_to_decimal(candle.low)))
                    cbom_bvp.append(BVP)
                    cbom_svp.append(SVP)

                    if len(cbom_volumes) > CBOM.length_of_df and len(cbom_lots) > CBOM.length_of_df and len(cbom_prices) > CBOM.length_of_df and len(cbom_time) > CBOM.length_of_df and len(cbom_close) > CBOM.length_of_df and len(cbom_high) > CBOM.length_of_df and len(cbom_low) > CBOM.length_of_df and len(cbom_bvp) > CBOM.length_of_df and len(cbom_svp) > CBOM.length_of_df:
                        del cbom_volumes[0]
                        del cbom_lots[0]
                        del cbom_prices[0]
                        del cbom_time[0]
                        del cbom_close[0]
                        del cbom_high[0]
                        del cbom_low[0]
                        del cbom_bvp[0]
                        del cbom_svp[0]
        
        df = pd.DataFrame(cbom_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{CBOM.ticker} {CBOM.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_cbom(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in cbom_db:
                    cbom_db.append(f'#{CBOM.ticker} {CBOM.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_cbom(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{CBOM.ticker} {CBOM.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_cbom(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{CBOM.ticker} {CBOM.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_cbom(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in cbom_db:
                    cbom_db.append(f'#{CBOM.ticker} {CBOM.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_cbom(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{CBOM.ticker} {CBOM.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_cbom(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_ozon():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=OZON.figi,
            from_=now() - timedelta(days=90),
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
                    ozon_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    ozon_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    ozon_prices.append(float(quotation_to_decimal(candle.close)))
                    ozon_time.append(candle.time)
                    ozon_close.append(float(quotation_to_decimal(candle.close)))
                    ozon_high.append(float(quotation_to_decimal(candle.high)))
                    ozon_low.append(float(quotation_to_decimal(candle.low)))
                    ozon_bvp.append(BVP)
                    ozon_svp.append(SVP)

                    if len(ozon_volumes) > OZON.length_of_df and len(ozon_lots) > OZON.length_of_df and len(ozon_prices) > OZON.length_of_df and len(ozon_time) > OZON.length_of_df and len(ozon_close) > OZON.length_of_df and len(ozon_high) > OZON.length_of_df and len(ozon_low) > OZON.length_of_df and len(ozon_bvp) > OZON.length_of_df and len(ozon_svp) > OZON.length_of_df:
                        del ozon_volumes[0]
                        del ozon_lots[0]
                        del ozon_prices[0]
                        del ozon_time[0]
                        del ozon_close[0]
                        del ozon_high[0]
                        del ozon_low[0]
                        del ozon_bvp[0]
                        del ozon_svp[0]

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
                    ozon_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    ozon_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    ozon_prices.append(int(quotation_to_decimal(candle.close)))
                    ozon_time.append(candle.time)
                    ozon_close.append(float(quotation_to_decimal(candle.close)))
                    ozon_high.append(float(quotation_to_decimal(candle.high)))
                    ozon_low.append(float(quotation_to_decimal(candle.low)))
                    ozon_bvp.append(BVP)
                    ozon_svp.append(SVP)

                    if len(ozon_volumes) > OZON.length_of_df and len(ozon_lots) > OZON.length_of_df and len(ozon_prices) > OZON.length_of_df and len(ozon_time) > OZON.length_of_df and len(ozon_close) > OZON.length_of_df and len(ozon_high) > OZON.length_of_df and len(ozon_low) > OZON.length_of_df and len(ozon_bvp) > OZON.length_of_df and len(ozon_svp) > OZON.length_of_df:
                        del ozon_volumes[0]
                        del ozon_lots[0]
                        del ozon_prices[0]
                        del ozon_time[0]
                        del ozon_close[0]
                        del ozon_high[0]
                        del ozon_low[0]
                        del ozon_bvp[0]
                        del ozon_svp[0]
        
        df = pd.DataFrame(ozon_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{OZON.ticker} {OZON.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in ozon_db:
                    ozon_db.append(f'#{OZON.ticker} {OZON.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{OZON.ticker} {OZON.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{OZON.ticker} {OZON.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in ozon_db:
                    ozon_db.append(f'#{OZON.ticker} {OZON.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{OZON.ticker} {OZON.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_afks():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=OZON.figi,
            from_=now() - timedelta(days=90),
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
                    afks_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    afks_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    afks_prices.append(float(quotation_to_decimal(candle.close)))
                    afks_time.append(candle.time)
                    afks_close.append(float(quotation_to_decimal(candle.close)))
                    afks_high.append(float(quotation_to_decimal(candle.high)))
                    afks_low.append(float(quotation_to_decimal(candle.low)))
                    afks_bvp.append(BVP)
                    afks_svp.append(SVP)

                    if len(afks_volumes) > AFKS.length_of_df and len(afks_lots) > AFKS.length_of_df and len(afks_prices) > AFKS.length_of_df and len(afks_time) > AFKS.length_of_df and len(afks_close) > AFKS.length_of_df and len(afks_high) > AFKS.length_of_df and len(afks_low) > AFKS.length_of_df and len(afks_bvp) > AFKS.length_of_df and len(afks_svp) > AFKS.length_of_df:
                        del afks_volumes[0]
                        del afks_lots[0]
                        del afks_prices[0]
                        del afks_time[0]
                        del afks_close[0]
                        del afks_high[0]
                        del afks_low[0]
                        del afks_bvp[0]
                        del afks_svp[0]

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
                    afks_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    afks_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    afks_prices.append(int(quotation_to_decimal(candle.close)))
                    afks_time.append(candle.time)
                    afks_close.append(float(quotation_to_decimal(candle.close)))
                    afks_high.append(float(quotation_to_decimal(candle.high)))
                    afks_low.append(float(quotation_to_decimal(candle.low)))
                    afks_bvp.append(BVP)
                    afks_svp.append(SVP)

                    if len(afks_volumes) > AFKS.length_of_df and len(afks_lots) > AFKS.length_of_df and len(afks_prices) > AFKS.length_of_df and len(afks_time) > AFKS.length_of_df and len(afks_close) > AFKS.length_of_df and len(afks_high) > AFKS.length_of_df and len(afks_low) > AFKS.length_of_df and len(afks_bvp) > AFKS.length_of_df and len(afks_svp) > AFKS.length_of_df:
                        del afks_volumes[0]
                        del afks_lots[0]
                        del afks_prices[0]
                        del afks_time[0]
                        del afks_close[0]
                        del afks_high[0]
                        del afks_low[0]
                        del afks_bvp[0]
                        del afks_svp[0]
        
        df = pd.DataFrame(afks_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{AFKS.ticker} {AFKS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_afks(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in afks_db:
                    afks_db.append(f'#{AFKS.ticker} {AFKS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_afks(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{AFKS.ticker} {AFKS.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_afks(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{AFKS.ticker} {AFKS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_afks(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in afks_db:
                    afks_db.append(f'#{AFKS.ticker} {AFKS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_afks(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{AFKS.ticker} {AFKS.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_afks(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_smlt():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=SMLT.figi,
            from_=now() - timedelta(days=90),
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
                    smlt_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    smlt_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    smlt_prices.append(float(quotation_to_decimal(candle.close)))
                    smlt_time.append(candle.time)
                    smlt_close.append(float(quotation_to_decimal(candle.close)))
                    smlt_high.append(float(quotation_to_decimal(candle.high)))
                    smlt_low.append(float(quotation_to_decimal(candle.low)))
                    smlt_bvp.append(BVP)
                    smlt_svp.append(SVP)

                    if len(smlt_volumes) > SMLT.length_of_df and len(smlt_lots) > SMLT.length_of_df and len(smlt_prices) > SMLT.length_of_df and len(smlt_time) > SMLT.length_of_df and len(smlt_close) > SMLT.length_of_df and len(smlt_high) > SMLT.length_of_df and len(smlt_low) > SMLT.length_of_df and len(smlt_bvp) > SMLT.length_of_df and len(smlt_svp) > SMLT.length_of_df:
                        del smlt_volumes[0]
                        del smlt_lots[0]
                        del smlt_prices[0]
                        del smlt_time[0]
                        del smlt_close[0]
                        del smlt_high[0]
                        del smlt_low[0]
                        del smlt_bvp[0]
                        del smlt_svp[0]

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
                    smlt_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    smlt_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    smlt_prices.append(int(quotation_to_decimal(candle.close)))
                    smlt_time.append(candle.time)
                    smlt_close.append(float(quotation_to_decimal(candle.close)))
                    smlt_high.append(float(quotation_to_decimal(candle.high)))
                    smlt_low.append(float(quotation_to_decimal(candle.low)))
                    smlt_bvp.append(BVP)
                    smlt_svp.append(SVP)

                    if len(smlt_volumes) > SMLT.length_of_df and len(smlt_lots) > SMLT.length_of_df and len(smlt_prices) > SMLT.length_of_df and len(smlt_time) > SMLT.length_of_df and len(smlt_close) > SMLT.length_of_df and len(smlt_high) > SMLT.length_of_df and len(smlt_low) > SMLT.length_of_df and len(smlt_bvp) > SMLT.length_of_df and len(smlt_svp) > SMLT.length_of_df:
                        del smlt_volumes[0]
                        del smlt_lots[0]
                        del smlt_prices[0]
                        del smlt_time[0]
                        del smlt_close[0]
                        del smlt_high[0]
                        del smlt_low[0]
                        del smlt_bvp[0]
                        del smlt_svp[0]
        
        df = pd.DataFrame(smlt_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{SMLT.ticker} {SMLT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in smlt_db:
                    smlt_db.append(f'#{SMLT.ticker} {SMLT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SMLT.ticker} {SMLT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{SMLT.ticker} {SMLT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in smlt_db:
                    smlt_db.append(f'#{SMLT.ticker} {SMLT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SMLT.ticker} {SMLT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_spbe():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=SPBE.figi,
            from_=now() - timedelta(days=90),
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
                    spbe_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    spbe_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    spbe_prices.append(float(quotation_to_decimal(candle.close)))
                    spbe_time.append(candle.time)
                    spbe_close.append(float(quotation_to_decimal(candle.close)))
                    spbe_high.append(float(quotation_to_decimal(candle.high)))
                    spbe_low.append(float(quotation_to_decimal(candle.low)))
                    spbe_bvp.append(BVP)
                    spbe_svp.append(SVP)

                    if len(spbe_volumes) > SPBE.length_of_df and len(spbe_lots) > SPBE.length_of_df and len(spbe_prices) > SPBE.length_of_df and len(spbe_time) > SPBE.length_of_df and len(spbe_close) > SPBE.length_of_df and len(spbe_high) > SPBE.length_of_df and len(spbe_low) > SPBE.length_of_df and len(spbe_bvp) > SPBE.length_of_df and len(spbe_svp) > SPBE.length_of_df:
                        del spbe_volumes[0]
                        del spbe_lots[0]
                        del spbe_prices[0]
                        del spbe_time[0]
                        del spbe_close[0]
                        del spbe_high[0]
                        del spbe_low[0]
                        del spbe_bvp[0]
                        del spbe_svp[0]

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
                    spbe_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    spbe_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    spbe_prices.append(int(quotation_to_decimal(candle.close)))
                    spbe_time.append(candle.time)
                    spbe_close.append(float(quotation_to_decimal(candle.close)))
                    spbe_high.append(float(quotation_to_decimal(candle.high)))
                    spbe_low.append(float(quotation_to_decimal(candle.low)))
                    spbe_bvp.append(BVP)
                    spbe_svp.append(SVP)

                    if len(spbe_volumes) > SPBE.length_of_df and len(spbe_lots) > SPBE.length_of_df and len(spbe_prices) > SPBE.length_of_df and len(spbe_time) > SPBE.length_of_df and len(spbe_close) > SPBE.length_of_df and len(spbe_high) > SPBE.length_of_df and len(spbe_low) > SPBE.length_of_df and len(spbe_bvp) > SPBE.length_of_df and len(spbe_svp) > SPBE.length_of_df:
                        del spbe_volumes[0]
                        del spbe_lots[0]
                        del spbe_prices[0]
                        del spbe_time[0]
                        del spbe_close[0]
                        del spbe_high[0]
                        del spbe_low[0]
                        del spbe_bvp[0]
                        del spbe_svp[0]
        
        df = pd.DataFrame(spbe_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{SPBE.ticker} {SPBE.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in spbe_db:
                    spbe_db.append(f'#{SPBE.ticker} {SPBE.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SPBE.ticker} {SPBE.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{SPBE.ticker} {SPBE.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in spbe_db:
                    spbe_db.append(f'#{SPBE.ticker} {SPBE.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SPBE.ticker} {SPBE.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_pikk():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=PIKK.figi,
            from_=now() - timedelta(days=90),
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
                    pikk_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    pikk_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    pikk_prices.append(float(quotation_to_decimal(candle.close)))
                    pikk_time.append(candle.time)
                    pikk_close.append(float(quotation_to_decimal(candle.close)))
                    pikk_high.append(float(quotation_to_decimal(candle.high)))
                    pikk_low.append(float(quotation_to_decimal(candle.low)))
                    pikk_bvp.append(BVP)
                    pikk_svp.append(SVP)

                    if len(pikk_volumes) > PIKK.length_of_df and len(pikk_lots) > PIKK.length_of_df and len(pikk_prices) > PIKK.length_of_df and len(pikk_time) > PIKK.length_of_df and len(pikk_close) > PIKK.length_of_df and len(pikk_high) > PIKK.length_of_df and len(pikk_low) > PIKK.length_of_df and len(pikk_bvp) > PIKK.length_of_df and len(pikk_svp) > PIKK.length_of_df:
                        del pikk_volumes[0]
                        del pikk_lots[0]
                        del pikk_prices[0]
                        del pikk_time[0]
                        del pikk_close[0]
                        del pikk_high[0]
                        del pikk_low[0]
                        del pikk_bvp[0]
                        del pikk_svp[0]

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
                    pikk_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    pikk_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    pikk_prices.append(int(quotation_to_decimal(candle.close)))
                    pikk_time.append(candle.time)
                    pikk_close.append(float(quotation_to_decimal(candle.close)))
                    pikk_high.append(float(quotation_to_decimal(candle.high)))
                    pikk_low.append(float(quotation_to_decimal(candle.low)))
                    pikk_bvp.append(BVP)
                    pikk_svp.append(SVP)

                    if len(pikk_volumes) > PIKK.length_of_df and len(pikk_lots) > PIKK.length_of_df and len(pikk_prices) > PIKK.length_of_df and len(pikk_time) > PIKK.length_of_df and len(pikk_close) > PIKK.length_of_df and len(pikk_high) > PIKK.length_of_df and len(pikk_low) > PIKK.length_of_df and len(pikk_bvp) > PIKK.length_of_df and len(pikk_svp) > PIKK.length_of_df:
                        del pikk_volumes[0]
                        del pikk_lots[0]
                        del pikk_prices[0]
                        del pikk_time[0]
                        del pikk_close[0]
                        del pikk_high[0]
                        del pikk_low[0]
                        del pikk_bvp[0]
                        del pikk_svp[0]
        
        df = pd.DataFrame(pikk_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{PIKK.ticker} {PIKK.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in pikk_db:
                    pikk_db.append(f'#{PIKK.ticker} {PIKK.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{PIKK.ticker} {PIKK.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{PIKK.ticker} {PIKK.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in pikk_db:
                    pikk_db.append(f'#{PIKK.ticker} {PIKK.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{PIKK.ticker} {PIKK.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_irao():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=IRAO.figi,
            from_=now() - timedelta(days=90),
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
                    irao_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    irao_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    irao_prices.append(float(quotation_to_decimal(candle.close)))
                    irao_time.append(candle.time)
                    irao_close.append(float(quotation_to_decimal(candle.close)))
                    irao_high.append(float(quotation_to_decimal(candle.high)))
                    irao_low.append(float(quotation_to_decimal(candle.low)))
                    irao_bvp.append(BVP)
                    irao_svp.append(SVP)

                    if len(irao_volumes) > IRAO.length_of_df and len(irao_lots) > IRAO.length_of_df and len(irao_prices) > IRAO.length_of_df and len(irao_time) > IRAO.length_of_df and len(irao_close) > IRAO.length_of_df and len(irao_high) > IRAO.length_of_df and len(irao_low) > IRAO.length_of_df and len(irao_bvp) > IRAO.length_of_df and len(irao_svp) > IRAO.length_of_df:
                        del irao_volumes[0]
                        del irao_lots[0]
                        del irao_prices[0]
                        del irao_time[0]
                        del irao_close[0]
                        del irao_high[0]
                        del irao_low[0]
                        del irao_bvp[0]
                        del irao_svp[0]

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
                    irao_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    irao_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    irao_prices.append(int(quotation_to_decimal(candle.close)))
                    irao_time.append(candle.time)
                    irao_close.append(float(quotation_to_decimal(candle.close)))
                    irao_high.append(float(quotation_to_decimal(candle.high)))
                    irao_low.append(float(quotation_to_decimal(candle.low)))
                    irao_bvp.append(BVP)
                    irao_svp.append(SVP)

                    if len(irao_volumes) > IRAO.length_of_df and len(irao_lots) > IRAO.length_of_df and len(irao_prices) > IRAO.length_of_df and len(irao_time) > IRAO.length_of_df and len(irao_close) > IRAO.length_of_df and len(irao_high) > IRAO.length_of_df and len(irao_low) > IRAO.length_of_df and len(irao_bvp) > IRAO.length_of_df and len(irao_svp) > IRAO.length_of_df:
                        del irao_volumes[0]
                        del irao_lots[0]
                        del irao_prices[0]
                        del irao_time[0]
                        del irao_close[0]
                        del irao_high[0]
                        del irao_low[0]
                        del irao_bvp[0]
                        del irao_svp[0]
        
        df = pd.DataFrame(irao_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{IRAO.ticker} {IRAO.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_irao(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in irao_db:
                    irao_db.append(f'#{IRAO.ticker} {IRAO.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_irao(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{IRAO.ticker} {IRAO.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_irao(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{IRAO.ticker} {IRAO.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_irao(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in irao_db:
                    irao_db.append(f'#{IRAO.ticker} {IRAO.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_irao(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{IRAO.ticker} {IRAO.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_irao(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_sibn():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=SIBN.figi,
            from_=now() - timedelta(days=90),
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
                    sibn_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    sibn_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sibn_prices.append(float(quotation_to_decimal(candle.close)))
                    sibn_time.append(candle.time)
                    sibn_close.append(float(quotation_to_decimal(candle.close)))
                    sibn_high.append(float(quotation_to_decimal(candle.high)))
                    sibn_low.append(float(quotation_to_decimal(candle.low)))
                    sibn_bvp.append(BVP)
                    sibn_svp.append(SVP)

                    if len(sibn_volumes) > SIBN.length_of_df and len(sibn_lots) > SIBN.length_of_df and len(sibn_prices) > SIBN.length_of_df and len(sibn_time) > SIBN.length_of_df and len(sibn_close) > SIBN.length_of_df and len(sibn_high) > SIBN.length_of_df and len(sibn_low) > SIBN.length_of_df and len(sibn_bvp) > SIBN.length_of_df and len(sibn_svp) > SIBN.length_of_df:
                        del sibn_volumes[0]
                        del sibn_lots[0]
                        del sibn_prices[0]
                        del sibn_time[0]
                        del sibn_close[0]
                        del sibn_high[0]
                        del sibn_low[0]
                        del sibn_bvp[0]
                        del sibn_svp[0]

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
                    sibn_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    sibn_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sibn_prices.append(int(quotation_to_decimal(candle.close)))
                    sibn_time.append(candle.time)
                    sibn_close.append(float(quotation_to_decimal(candle.close)))
                    sibn_high.append(float(quotation_to_decimal(candle.high)))
                    sibn_low.append(float(quotation_to_decimal(candle.low)))
                    sibn_bvp.append(BVP)
                    sibn_svp.append(SVP)

                    if len(sibn_volumes) > SIBN.length_of_df and len(sibn_lots) > SIBN.length_of_df and len(sibn_prices) > SIBN.length_of_df and len(sibn_time) > SIBN.length_of_df and len(sibn_close) > SIBN.length_of_df and len(sibn_high) > SIBN.length_of_df and len(sibn_low) > SIBN.length_of_df and len(sibn_bvp) > SIBN.length_of_df and len(sibn_svp) > SIBN.length_of_df:
                        del sibn_volumes[0]
                        del sibn_lots[0]
                        del sibn_prices[0]
                        del sibn_time[0]
                        del sibn_close[0]
                        del sibn_high[0]
                        del sibn_low[0]
                        del sibn_bvp[0]
                        del sibn_svp[0]
        
        df = pd.DataFrame(sibn_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{SIBN.ticker} {SIBN.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sibn_db:
                    sibn_db.append(f'#{SIBN.ticker} {SIBN.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SIBN.ticker} {SIBN.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{SIBN.ticker} {SIBN.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sibn_db:
                    sibn_db.append(f'#{SIBN.ticker} {SIBN.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SIBN.ticker} {SIBN.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_rasp():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=RASP.figi,
            from_=now() - timedelta(days=90),
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
                    rasp_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    rasp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    rasp_prices.append(float(quotation_to_decimal(candle.close)))
                    rasp_time.append(candle.time)
                    rasp_close.append(float(quotation_to_decimal(candle.close)))
                    rasp_high.append(float(quotation_to_decimal(candle.high)))
                    rasp_low.append(float(quotation_to_decimal(candle.low)))
                    rasp_bvp.append(BVP)
                    rasp_svp.append(SVP)

                    if len(rasp_volumes) > RASP.length_of_df and len(rasp_lots) > RASP.length_of_df and len(rasp_prices) > RASP.length_of_df and len(rasp_time) > RASP.length_of_df and len(rasp_close) > RASP.length_of_df and len(rasp_high) > RASP.length_of_df and len(rasp_low) > RASP.length_of_df and len(rasp_bvp) > RASP.length_of_df and len(rasp_svp) > RASP.length_of_df:
                        del rasp_volumes[0]
                        del rasp_lots[0]
                        del rasp_prices[0]
                        del rasp_time[0]
                        del rasp_close[0]
                        del rasp_high[0]
                        del rasp_low[0]
                        del rasp_bvp[0]
                        del rasp_svp[0]

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
                    rasp_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    rasp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    rasp_prices.append(int(quotation_to_decimal(candle.close)))
                    rasp_time.append(candle.time)
                    rasp_close.append(float(quotation_to_decimal(candle.close)))
                    rasp_high.append(float(quotation_to_decimal(candle.high)))
                    rasp_low.append(float(quotation_to_decimal(candle.low)))
                    rasp_bvp.append(BVP)
                    rasp_svp.append(SVP)

                    if len(rasp_volumes) > RASP.length_of_df and len(rasp_lots) > RASP.length_of_df and len(rasp_prices) > RASP.length_of_df and len(rasp_time) > RASP.length_of_df and len(rasp_close) > RASP.length_of_df and len(rasp_high) > RASP.length_of_df and len(rasp_low) > RASP.length_of_df and len(rasp_bvp) > RASP.length_of_df and len(rasp_svp) > RASP.length_of_df:
                        del rasp_volumes[0]
                        del rasp_lots[0]
                        del rasp_prices[0]
                        del rasp_time[0]
                        del rasp_close[0]
                        del rasp_high[0]
                        del rasp_low[0]
                        del rasp_bvp[0]
                        del rasp_svp[0]
        
        df = pd.DataFrame(rasp_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{RASP.ticker} {RASP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in rasp_db:
                    rasp_db.append(f'#{RASP.ticker} {RASP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{RASP.ticker} {RASP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{RASP.ticker} {RASP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in rasp_db:
                    rasp_db.append(f'#{RASP.ticker} {RASP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{RASP.ticker} {RASP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_sgzh():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=SGZH.figi,
            from_=now() - timedelta(days=90),
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
                    sgzh_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    sgzh_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sgzh_prices.append(float(quotation_to_decimal(candle.close)))
                    sgzh_time.append(candle.time)
                    sgzh_close.append(float(quotation_to_decimal(candle.close)))
                    sgzh_high.append(float(quotation_to_decimal(candle.high)))
                    sgzh_low.append(float(quotation_to_decimal(candle.low)))
                    sgzh_bvp.append(BVP)
                    sgzh_svp.append(SVP)

                    if len(sgzh_volumes) > SGZH.length_of_df and len(sgzh_lots) > SGZH.length_of_df and len(sgzh_prices) > SGZH.length_of_df and len(sgzh_time) > SGZH.length_of_df and len(sgzh_close) > SGZH.length_of_df and len(sgzh_high) > SGZH.length_of_df and len(sgzh_low) > SGZH.length_of_df and len(sgzh_bvp) > SGZH.length_of_df and len(sgzh_svp) > SGZH.length_of_df:
                        del sgzh_volumes[0]
                        del sgzh_lots[0]
                        del sgzh_prices[0]
                        del sgzh_time[0]
                        del sgzh_close[0]
                        del sgzh_high[0]
                        del sgzh_low[0]
                        del sgzh_bvp[0]
                        del sgzh_svp[0]

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
                    sgzh_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    sgzh_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    sgzh_prices.append(int(quotation_to_decimal(candle.close)))
                    sgzh_time.append(candle.time)
                    sgzh_close.append(float(quotation_to_decimal(candle.close)))
                    sgzh_high.append(float(quotation_to_decimal(candle.high)))
                    sgzh_low.append(float(quotation_to_decimal(candle.low)))
                    sgzh_bvp.append(BVP)
                    sgzh_svp.append(SVP)

                    if len(sgzh_volumes) > SGZH.length_of_df and len(sgzh_lots) > SGZH.length_of_df and len(sgzh_prices) > SGZH.length_of_df and len(sgzh_time) > SGZH.length_of_df and len(sgzh_close) > SGZH.length_of_df and len(sgzh_high) > SGZH.length_of_df and len(sgzh_low) > SGZH.length_of_df and len(sgzh_bvp) > SGZH.length_of_df and len(sgzh_svp) > SGZH.length_of_df:
                        del sgzh_volumes[0]
                        del sgzh_lots[0]
                        del sgzh_prices[0]
                        del sgzh_time[0]
                        del sgzh_close[0]
                        del sgzh_high[0]
                        del sgzh_low[0]
                        del sgzh_bvp[0]
                        del sgzh_svp[0]
        
        df = pd.DataFrame(sgzh_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{SGZH.ticker} {SGZH.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1])))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sgzh_db:
                    sgzh_db.append(f'#{SGZH.ticker} {SGZH.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1])))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SGZH.ticker} {SGZH.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1])))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{SGZH.ticker} {SGZH.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1])))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in sgzh_db:
                    sgzh_db.append(f'#{SGZH.ticker} {SGZH.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1])))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{SGZH.ticker} {SGZH.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1])))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_dsky():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=DSKY.figi,
            from_=now() - timedelta(days=90),
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
                    dsky_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    dsky_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    dsky_prices.append(float(quotation_to_decimal(candle.close)))
                    dsky_time.append(candle.time)
                    dsky_close.append(float(quotation_to_decimal(candle.close)))
                    dsky_high.append(float(quotation_to_decimal(candle.high)))
                    dsky_low.append(float(quotation_to_decimal(candle.low)))
                    dsky_bvp.append(BVP)
                    dsky_svp.append(SVP)

                    if len(dsky_volumes) > DSKY.length_of_df and len(dsky_lots) > DSKY.length_of_df and len(dsky_prices) > DSKY.length_of_df and len(dsky_time) > DSKY.length_of_df and len(dsky_close) > DSKY.length_of_df and len(dsky_high) > DSKY.length_of_df and len(dsky_low) > DSKY.length_of_df and len(dsky_bvp) > DSKY.length_of_df and len(dsky_svp) > DSKY.length_of_df:
                        del dsky_volumes[0]
                        del dsky_lots[0]
                        del dsky_prices[0]
                        del dsky_time[0]
                        del dsky_close[0]
                        del dsky_high[0]
                        del dsky_low[0]
                        del dsky_bvp[0]
                        del dsky_svp[0]

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
                    dsky_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    dsky_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    dsky_prices.append(int(quotation_to_decimal(candle.close)))
                    dsky_time.append(candle.time)
                    dsky_close.append(float(quotation_to_decimal(candle.close)))
                    dsky_high.append(float(quotation_to_decimal(candle.high)))
                    dsky_low.append(float(quotation_to_decimal(candle.low)))
                    dsky_bvp.append(BVP)
                    dsky_svp.append(SVP)

                    if len(dsky_volumes) > DSKY.length_of_df and len(dsky_lots) > DSKY.length_of_df and len(dsky_prices) > DSKY.length_of_df and len(dsky_time) > DSKY.length_of_df and len(dsky_close) > DSKY.length_of_df and len(dsky_high) > DSKY.length_of_df and len(dsky_low) > DSKY.length_of_df and len(dsky_bvp) > DSKY.length_of_df and len(dsky_svp) > DSKY.length_of_df:
                        del dsky_volumes[0]
                        del dsky_lots[0]
                        del dsky_prices[0]
                        del dsky_time[0]
                        del dsky_close[0]
                        del dsky_high[0]
                        del dsky_low[0]
                        del dsky_bvp[0]
                        del dsky_svp[0]
        
        df = pd.DataFrame(dsky_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{DSKY.ticker} {DSKY.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in dsky_db:
                    dsky_db.append(f'#{DSKY.ticker} {DSKY.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{DSKY.ticker} {DSKY.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{DSKY.ticker} {DSKY.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in dsky_db:
                    dsky_db.append(f'#{DSKY.ticker} {DSKY.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{DSKY.ticker} {DSKY.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_trnfp():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=TRNFP.figi,
            from_=now() - timedelta(days=90),
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
                    trnfp_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    trnfp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    trnfp_prices.append(float(quotation_to_decimal(candle.close)))
                    trnfp_time.append(candle.time)
                    trnfp_close.append(float(quotation_to_decimal(candle.close)))
                    trnfp_high.append(float(quotation_to_decimal(candle.high)))
                    trnfp_low.append(float(quotation_to_decimal(candle.low)))
                    trnfp_bvp.append(BVP)
                    trnfp_svp.append(SVP)

                    if len(trnfp_volumes) > TRNFP.length_of_df and len(trnfp_lots) > TRNFP.length_of_df and len(trnfp_prices) > TRNFP.length_of_df and len(trnfp_time) > TRNFP.length_of_df and len(trnfp_close) > TRNFP.length_of_df and len(trnfp_high) > TRNFP.length_of_df and len(trnfp_low) > TRNFP.length_of_df and len(trnfp_bvp) > TRNFP.length_of_df and len(trnfp_svp) > TRNFP.length_of_df:
                        del trnfp_volumes[0]
                        del trnfp_lots[0]
                        del trnfp_prices[0]
                        del trnfp_time[0]
                        del trnfp_close[0]
                        del trnfp_high[0]
                        del trnfp_low[0]
                        del trnfp_bvp[0]
                        del trnfp_svp[0]

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
                    trnfp_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    trnfp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    trnfp_prices.append(int(quotation_to_decimal(candle.close)))
                    trnfp_time.append(candle.time)
                    trnfp_close.append(float(quotation_to_decimal(candle.close)))
                    trnfp_high.append(float(quotation_to_decimal(candle.high)))
                    trnfp_low.append(float(quotation_to_decimal(candle.low)))
                    trnfp_bvp.append(BVP)
                    trnfp_svp.append(SVP)

                    if len(trnfp_volumes) > TRNFP.length_of_df and len(trnfp_lots) > TRNFP.length_of_df and len(trnfp_prices) > TRNFP.length_of_df and len(trnfp_time) > TRNFP.length_of_df and len(trnfp_close) > TRNFP.length_of_df and len(trnfp_high) > TRNFP.length_of_df and len(trnfp_low) > TRNFP.length_of_df and len(trnfp_bvp) > TRNFP.length_of_df and len(trnfp_svp) > TRNFP.length_of_df:
                        del trnfp_volumes[0]
                        del trnfp_lots[0]
                        del trnfp_prices[0]
                        del trnfp_time[0]
                        del trnfp_close[0]
                        del trnfp_high[0]
                        del trnfp_low[0]
                        del trnfp_bvp[0]
                        del trnfp_svp[0]
        
        df = pd.DataFrame(trnfp_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{TRNFP.ticker} {TRNFP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in trnfp_db:
                    trnfp_db.append(f'#{TRNFP.ticker} {TRNFP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{TRNFP.ticker} {TRNFP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{TRNFP.ticker} {TRNFP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in trnfp_db:
                    trnfp_db.append(f'#{TRNFP.ticker} {TRNFP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{TRNFP.ticker} {TRNFP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_rnft():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=RNFT.figi,
            from_=now() - timedelta(days=90),
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
                    rnft_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    rnft_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    rnft_prices.append(float(quotation_to_decimal(candle.close)))
                    rnft_time.append(candle.time)
                    rnft_close.append(float(quotation_to_decimal(candle.close)))
                    rnft_high.append(float(quotation_to_decimal(candle.high)))
                    rnft_low.append(float(quotation_to_decimal(candle.low)))
                    rnft_bvp.append(BVP)
                    rnft_svp.append(SVP)

                    if len(rnft_volumes) > RNFT.length_of_df and len(rnft_lots) > RNFT.length_of_df and len(rnft_prices) > RNFT.length_of_df and len(rnft_time) > RNFT.length_of_df and len(rnft_close) > RNFT.length_of_df and len(rnft_high) > RNFT.length_of_df and len(rnft_low) > RNFT.length_of_df and len(rnft_bvp) > RNFT.length_of_df and len(rnft_svp) > RNFT.length_of_df:
                        del rnft_volumes[0]
                        del rnft_lots[0]
                        del rnft_prices[0]
                        del rnft_time[0]
                        del rnft_close[0]
                        del rnft_high[0]
                        del rnft_low[0]
                        del rnft_bvp[0]
                        del rnft_svp[0]

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
                    rnft_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    rnft_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    rnft_prices.append(int(quotation_to_decimal(candle.close)))
                    rnft_time.append(candle.time)
                    rnft_close.append(float(quotation_to_decimal(candle.close)))
                    rnft_high.append(float(quotation_to_decimal(candle.high)))
                    rnft_low.append(float(quotation_to_decimal(candle.low)))
                    rnft_bvp.append(BVP)
                    rnft_svp.append(SVP)

                    if len(rnft_volumes) > RNFT.length_of_df and len(rnft_lots) > RNFT.length_of_df and len(rnft_prices) > RNFT.length_of_df and len(rnft_time) > RNFT.length_of_df and len(rnft_close) > RNFT.length_of_df and len(rnft_high) > RNFT.length_of_df and len(rnft_low) > RNFT.length_of_df and len(rnft_bvp) > RNFT.length_of_df and len(rnft_svp) > RNFT.length_of_df:
                        del rnft_volumes[0]
                        del rnft_lots[0]
                        del rnft_prices[0]
                        del rnft_time[0]
                        del rnft_close[0]
                        del rnft_high[0]
                        del rnft_low[0]
                        del rnft_bvp[0]
                        del rnft_svp[0]
        
        df = pd.DataFrame(rnft_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                if f'#{RNFT.ticker} {RNFT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in rnft_db:
                    rnft_db.append(f'#{RNFT.ticker} {RNFT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{RNFT.ticker} {RNFT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
            else:
                if f'#{RNFT.ticker} {RNFT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.' not in rnft_db:
                    rnft_db.append(f'#{RNFT.ticker} {RNFT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    send_message(f'#{RNFT.ticker} {RNFT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                    time.sleep(3)
   
    return 0


def check_abnormal_volume_five():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=FIVE.figi,
            from_=now() - timedelta(days=90),
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
                    five_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    five_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    five_prices.append(float(quotation_to_decimal(candle.close)))
                    five_time.append(candle.time)
                    five_close.append(float(quotation_to_decimal(candle.close)))
                    five_high.append(float(quotation_to_decimal(candle.high)))
                    five_low.append(float(quotation_to_decimal(candle.low)))
                    five_bvp.append(BVP)
                    five_svp.append(SVP)

                    if len(five_volumes) > FIVE.length_of_df and len(five_lots) > FIVE.length_of_df and len(five_prices) > FIVE.length_of_df and len(five_time) > FIVE.length_of_df and len(five_close) > FIVE.length_of_df and len(five_high) > FIVE.length_of_df and len(five_low) > FIVE.length_of_df and len(five_bvp) > FIVE.length_of_df and len(five_svp) > FIVE.length_of_df:
                        del five_volumes[0]
                        del five_lots[0]
                        del five_prices[0]
                        del five_time[0]
                        del five_close[0]
                        del five_high[0]
                        del five_low[0]
                        del five_bvp[0]
                        del five_svp[0]

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
                    five_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    five_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    five_prices.append(int(quotation_to_decimal(candle.close)))
                    five_time.append(candle.time)
                    five_close.append(float(quotation_to_decimal(candle.close)))
                    five_high.append(float(quotation_to_decimal(candle.high)))
                    five_low.append(float(quotation_to_decimal(candle.low)))
                    five_bvp.append(BVP)
                    five_svp.append(SVP)

                    if len(five_volumes) > FIVE.length_of_df and len(five_lots) > FIVE.length_of_df and len(five_prices) > FIVE.length_of_df and len(five_time) > FIVE.length_of_df and len(five_close) > FIVE.length_of_df and len(five_high) > FIVE.length_of_df and len(five_low) > FIVE.length_of_df and len(five_bvp) > FIVE.length_of_df and len(five_svp) > FIVE.length_of_df:
                        del five_volumes[0]
                        del five_lots[0]
                        del five_prices[0]
                        del five_time[0]
                        del five_close[0]
                        del five_high[0]
                        del five_low[0]
                        del five_bvp[0]
                        del five_svp[0]
        
        df = pd.DataFrame(five_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                send_message(f'#{FIVE.ticker} {FIVE.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
            else:
                send_message(f'#{FIVE.ticker} {FIVE.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
   
    return 0


def check_abnormal_volume_bspb():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=BSPB.figi,
            from_=now() - timedelta(days=90),
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
                    bspb_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    bspb_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    bspb_prices.append(float(quotation_to_decimal(candle.close)))
                    bspb_time.append(candle.time)
                    bspb_close.append(float(quotation_to_decimal(candle.close)))
                    bspb_high.append(float(quotation_to_decimal(candle.high)))
                    bspb_low.append(float(quotation_to_decimal(candle.low)))
                    bspb_bvp.append(BVP)
                    bspb_svp.append(SVP)

                    if len(bspb_volumes) > BSPB.length_of_df and len(bspb_lots) > BSPB.length_of_df and len(bspb_prices) > BSPB.length_of_df and len(bspb_time) > BSPB.length_of_df and len(bspb_close) > BSPB.length_of_df and len(bspb_high) > BSPB.length_of_df and len(bspb_low) > BSPB.length_of_df and len(bspb_bvp) > BSPB.length_of_df and len(bspb_svp) > BSPB.length_of_df:
                        del bspb_volumes[0]
                        del bspb_lots[0]
                        del bspb_prices[0]
                        del bspb_time[0]
                        del bspb_close[0]
                        del bspb_high[0]
                        del bspb_low[0]
                        del bspb_bvp[0]
                        del bspb_svp[0]

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
                    bspb_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    bspb_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    bspb_prices.append(int(quotation_to_decimal(candle.close)))
                    bspb_time.append(candle.time)
                    bspb_close.append(float(quotation_to_decimal(candle.close)))
                    bspb_high.append(float(quotation_to_decimal(candle.high)))
                    bspb_low.append(float(quotation_to_decimal(candle.low)))
                    bspb_bvp.append(BVP)
                    bspb_svp.append(SVP)

                    if len(bspb_volumes) > BSPB.length_of_df and len(bspb_lots) > BSPB.length_of_df and len(bspb_prices) > BSPB.length_of_df and len(bspb_time) > BSPB.length_of_df and len(bspb_close) > BSPB.length_of_df and len(bspb_high) > BSPB.length_of_df and len(bspb_low) > BSPB.length_of_df and len(bspb_bvp) > BSPB.length_of_df and len(bspb_svp) > BSPB.length_of_df:
                        del bspb_volumes[0]
                        del bspb_lots[0]
                        del bspb_prices[0]
                        del bspb_time[0]
                        del bspb_close[0]
                        del bspb_high[0]
                        del bspb_low[0]
                        del bspb_bvp[0]
                        del bspb_svp[0]
        
        df = pd.DataFrame(bspb_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                send_message(f'#{BSPB.ticker} {BSPB.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
            else:
                send_message(f'#{BSPB.ticker} {BSPB.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
   
    return 0


def check_abnormal_volume_flot():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=FLOT.figi,
            from_=now() - timedelta(days=90),
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
                    flot_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    flot_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    flot_prices.append(float(quotation_to_decimal(candle.close)))
                    flot_time.append(candle.time)
                    flot_close.append(float(quotation_to_decimal(candle.close)))
                    flot_high.append(float(quotation_to_decimal(candle.high)))
                    flot_low.append(float(quotation_to_decimal(candle.low)))
                    flot_bvp.append(BVP)
                    flot_svp.append(SVP)

                    if len(flot_volumes) > FLOT.length_of_df and len(flot_lots) > FLOT.length_of_df and len(flot_prices) > FLOT.length_of_df and len(flot_time) > FLOT.length_of_df and len(flot_close) > FLOT.length_of_df and len(flot_high) > FLOT.length_of_df and len(flot_low) > FLOT.length_of_df and len(flot_bvp) > FLOT.length_of_df and len(flot_svp) > FLOT.length_of_df:
                        del flot_volumes[0]
                        del flot_lots[0]
                        del flot_prices[0]
                        del flot_time[0]
                        del flot_close[0]
                        del flot_high[0]
                        del flot_low[0]
                        del flot_bvp[0]
                        del flot_svp[0]

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
                    flot_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    flot_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    flot_prices.append(int(quotation_to_decimal(candle.close)))
                    flot_time.append(candle.time)
                    flot_close.append(float(quotation_to_decimal(candle.close)))
                    flot_high.append(float(quotation_to_decimal(candle.high)))
                    flot_low.append(float(quotation_to_decimal(candle.low)))
                    flot_bvp.append(BVP)
                    flot_svp.append(SVP)

                    if len(flot_volumes) > FLOT.length_of_df and len(flot_lots) > FLOT.length_of_df and len(flot_prices) > FLOT.length_of_df and len(flot_time) > FLOT.length_of_df and len(flot_close) > FLOT.length_of_df and len(flot_high) > FLOT.length_of_df and len(flot_low) > FLOT.length_of_df and len(flot_bvp) > FLOT.length_of_df and len(flot_svp) > FLOT.length_of_df:
                        del flot_volumes[0]
                        del flot_lots[0]
                        del flot_prices[0]
                        del flot_time[0]
                        del flot_close[0]
                        del flot_high[0]
                        del flot_low[0]
                        del flot_bvp[0]
                        del flot_svp[0]
        
        df = pd.DataFrame(flot_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                send_message(f'#{FLOT.ticker} {FLOT.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
            else:
                send_message(f'#{FLOT.ticker} {FLOT.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
   
    return 0


def check_abnormal_volume_uwgn():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=UWGN.figi,
            from_=now() - timedelta(days=90),
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
                    uwgn_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    uwgn_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    uwgn_prices.append(float(quotation_to_decimal(candle.close)))
                    uwgn_time.append(candle.time)
                    uwgn_close.append(float(quotation_to_decimal(candle.close)))
                    uwgn_high.append(float(quotation_to_decimal(candle.high)))
                    uwgn_low.append(float(quotation_to_decimal(candle.low)))
                    uwgn_bvp.append(BVP)
                    uwgn_svp.append(SVP)

                    if len(uwgn_volumes) > UWGN.length_of_df and len(uwgn_lots) > UWGN.length_of_df and len(uwgn_prices) > UWGN.length_of_df and len(uwgn_time) > UWGN.length_of_df and len(uwgn_close) > UWGN.length_of_df and len(uwgn_high) > UWGN.length_of_df and len(uwgn_low) > UWGN.length_of_df and len(uwgn_bvp) > UWGN.length_of_df and len(uwgn_svp) > UWGN.length_of_df:
                        del uwgn_volumes[0]
                        del uwgn_lots[0]
                        del uwgn_prices[0]
                        del uwgn_time[0]
                        del uwgn_close[0]
                        del uwgn_high[0]
                        del uwgn_low[0]
                        del uwgn_bvp[0]
                        del uwgn_svp[0]

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
                    uwgn_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    uwgn_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    uwgn_prices.append(int(quotation_to_decimal(candle.close)))
                    uwgn_time.append(candle.time)
                    uwgn_close.append(float(quotation_to_decimal(candle.close)))
                    uwgn_high.append(float(quotation_to_decimal(candle.high)))
                    uwgn_low.append(float(quotation_to_decimal(candle.low)))
                    uwgn_bvp.append(BVP)
                    uwgn_svp.append(SVP)

                    if len(uwgn_volumes) > UWGN.length_of_df and len(uwgn_lots) > UWGN.length_of_df and len(uwgn_prices) > UWGN.length_of_df and len(uwgn_time) > UWGN.length_of_df and len(uwgn_close) > UWGN.length_of_df and len(uwgn_high) > UWGN.length_of_df and len(uwgn_low) > UWGN.length_of_df and len(uwgn_bvp) > UWGN.length_of_df and len(uwgn_svp) > UWGN.length_of_df:
                        del uwgn_volumes[0]
                        del uwgn_lots[0]
                        del uwgn_prices[0]
                        del uwgn_time[0]
                        del uwgn_close[0]
                        del uwgn_high[0]
                        del uwgn_low[0]
                        del uwgn_bvp[0]
                        del uwgn_svp[0]
        
        df = pd.DataFrame(uwgn_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                send_message(f'#{UWGN.ticker} {UWGN.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
            else:
                send_message(f'#{UWGN.ticker} {UWGN.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(df["Объем"].iloc[-1])} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
   
    return 0


def check_abnormal_volume_mtlrp():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=MTLRP.figi,
            from_=now() - timedelta(days=90),
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
                    mtlrp_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    mtlrp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mtlrp_prices.append(float(quotation_to_decimal(candle.close)))
                    mtlrp_time.append(candle.time)
                    mtlrp_close.append(float(quotation_to_decimal(candle.close)))
                    mtlrp_high.append(float(quotation_to_decimal(candle.high)))
                    mtlrp_low.append(float(quotation_to_decimal(candle.low)))
                    mtlrp_bvp.append(BVP)
                    mtlrp_svp.append(SVP)

                    if len(mtlrp_volumes) > MTLRP.length_of_df and len(mtlrp_lots) > MTLRP.length_of_df and len(mtlrp_prices) > MTLRP.length_of_df and len(mtlrp_time) > MTLRP.length_of_df and len(mtlrp_close) > MTLRP.length_of_df and len(mtlrp_high) > MTLRP.length_of_df and len(mtlrp_low) > MTLRP.length_of_df and len(mtlrp_bvp) > MTLRP.length_of_df and len(mtlrp_svp) > MTLRP.length_of_df:
                        del mtlrp_volumes[0]
                        del mtlrp_lots[0]
                        del mtlrp_prices[0]
                        del mtlrp_time[0]
                        del mtlrp_close[0]
                        del mtlrp_high[0]
                        del mtlrp_low[0]
                        del mtlrp_bvp[0]
                        del mtlrp_svp[0]

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
                    mtlrp_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    mtlrp_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    mtlrp_prices.append(int(quotation_to_decimal(candle.close)))
                    mtlrp_time.append(candle.time)
                    mtlrp_close.append(float(quotation_to_decimal(candle.close)))
                    mtlrp_high.append(float(quotation_to_decimal(candle.high)))
                    mtlrp_low.append(float(quotation_to_decimal(candle.low)))
                    mtlrp_bvp.append(BVP)
                    mtlrp_svp.append(SVP)

                    if len(mtlrp_volumes) > MTLRP.length_of_df and len(mtlrp_lots) > MTLRP.length_of_df and len(mtlrp_prices) > MTLRP.length_of_df and len(mtlrp_time) > MTLRP.length_of_df and len(mtlrp_close) > MTLRP.length_of_df and len(mtlrp_high) > MTLRP.length_of_df and len(mtlrp_low) > MTLRP.length_of_df and len(mtlrp_bvp) > MTLRP.length_of_df and len(mtlrp_svp) > MTLRP.length_of_df:
                        del mtlrp_volumes[0]
                        del mtlrp_lots[0]
                        del mtlrp_prices[0]
                        del mtlrp_time[0]
                        del mtlrp_close[0]
                        del mtlrp_high[0]
                        del mtlrp_low[0]
                        del mtlrp_bvp[0]
                        del mtlrp_svp[0]
        
        df = pd.DataFrame(mtlrp_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                send_message(f'#{MTLRP.ticker} {MTLRP.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
            else:
                send_message(f'#{MTLRP.ticker} {MTLRP.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
   
    return 0


def check_abnormal_volume_iskj():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=ISKJ.figi,
            from_=now() - timedelta(days=90),
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
                    iskj_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    iskj_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    iskj_prices.append(float(quotation_to_decimal(candle.close)))
                    iskj_time.append(candle.time)
                    iskj_close.append(float(quotation_to_decimal(candle.close)))
                    iskj_high.append(float(quotation_to_decimal(candle.high)))
                    iskj_low.append(float(quotation_to_decimal(candle.low)))
                    iskj_bvp.append(BVP)
                    iskj_svp.append(SVP)

                    if len(iskj_volumes) > ISKJ.length_of_df and len(iskj_lots) > ISKJ.length_of_df and len(iskj_prices) > ISKJ.length_of_df and len(iskj_time) > ISKJ.length_of_df and len(iskj_close) > ISKJ.length_of_df and len(iskj_high) > ISKJ.length_of_df and len(iskj_low) > ISKJ.length_of_df and len(iskj_bvp) > ISKJ.length_of_df and len(iskj_svp) > ISKJ.length_of_df:
                        del iskj_volumes[0]
                        del iskj_lots[0]
                        del iskj_prices[0]
                        del iskj_time[0]
                        del iskj_close[0]
                        del iskj_high[0]
                        del iskj_low[0]
                        del iskj_bvp[0]
                        del iskj_svp[0]

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
                    iskj_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    iskj_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    iskj_prices.append(int(quotation_to_decimal(candle.close)))
                    iskj_time.append(candle.time)
                    iskj_close.append(float(quotation_to_decimal(candle.close)))
                    iskj_high.append(float(quotation_to_decimal(candle.high)))
                    iskj_low.append(float(quotation_to_decimal(candle.low)))
                    iskj_bvp.append(BVP)
                    iskj_svp.append(SVP)

                    if len(iskj_volumes) > ISKJ.length_of_df and len(iskj_lots) > ISKJ.length_of_df and len(iskj_prices) > ISKJ.length_of_df and len(iskj_time) > ISKJ.length_of_df and len(iskj_close) > ISKJ.length_of_df and len(iskj_high) > ISKJ.length_of_df and len(iskj_low) > ISKJ.length_of_df and len(iskj_bvp) > ISKJ.length_of_df and len(iskj_svp) > ISKJ.length_of_df:
                        del iskj_volumes[0]
                        del iskj_lots[0]
                        del iskj_prices[0]
                        del iskj_time[0]
                        del iskj_close[0]
                        del iskj_high[0]
                        del iskj_low[0]
                        del iskj_bvp[0]
                        del iskj_svp[0]
        
        df = pd.DataFrame(iskj_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                send_message(f'#{ISKJ.ticker} {ISKJ.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
            else:
                send_message(f'#{ISKJ.ticker} {ISKJ.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
   
    return 0


def check_abnormal_volume_upro():
    with Client(TOKEN) as client:        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi=UPRO.figi,
            from_=now() - timedelta(days=90),
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
                    upro_volumes.append(make_million_volumes_on_float_stock_prices(final_stock_volume_rub))
                    upro_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    upro_prices.append(float(quotation_to_decimal(candle.close)))
                    upro_time.append(candle.time)
                    upro_close.append(float(quotation_to_decimal(candle.close)))
                    upro_high.append(float(quotation_to_decimal(candle.high)))
                    upro_low.append(float(quotation_to_decimal(candle.low)))
                    upro_bvp.append(BVP)
                    upro_svp.append(SVP)

                    if len(upro_volumes) > UPRO.length_of_df and len(upro_lots) > UPRO.length_of_df and len(upro_prices) > UPRO.length_of_df and len(upro_time) > UPRO.length_of_df and len(upro_close) > UPRO.length_of_df and len(upro_high) > UPRO.length_of_df and len(upro_low) > UPRO.length_of_df and len(upro_bvp) > UPRO.length_of_df and len(upro_svp) > UPRO.length_of_df:
                        del upro_volumes[0]
                        del upro_lots[0]
                        del upro_prices[0]
                        del upro_time[0]
                        del upro_close[0]
                        del upro_high[0]
                        del upro_low[0]
                        del upro_bvp[0]
                        del upro_svp[0]

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
                    upro_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    upro_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    upro_prices.append(int(quotation_to_decimal(candle.close)))
                    upro_time.append(candle.time)
                    upro_close.append(float(quotation_to_decimal(candle.close)))
                    upro_high.append(float(quotation_to_decimal(candle.high)))
                    upro_low.append(float(quotation_to_decimal(candle.low)))
                    upro_bvp.append(BVP)
                    upro_svp.append(SVP)

                    if len(upro_volumes) > UPRO.length_of_df and len(upro_lots) > UPRO.length_of_df and len(upro_prices) > UPRO.length_of_df and len(upro_time) > UPRO.length_of_df and len(upro_close) > UPRO.length_of_df and len(upro_high) > UPRO.length_of_df and len(upro_low) > UPRO.length_of_df and len(upro_bvp) > UPRO.length_of_df and len(upro_svp) > UPRO.length_of_df:
                        del upro_volumes[0]
                        del upro_lots[0]
                        del upro_prices[0]
                        del upro_time[0]
                        del upro_close[0]
                        del upro_high[0]
                        del upro_low[0]
                        del upro_bvp[0]
                        del upro_svp[0]
        
        df = pd.DataFrame(upro_data)

        # Calculate the rolling average and standard deviation of the trading volume
        volume_mean = df['Объем'].mean()
        volume_std = df['Объем'].std()
        
        # Calculate the rolling average and standard deviation of the trading prices
        prices_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prices_mean) / prices_std
            
        if abnormal_volume > THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                send_message(f'#{UPRO.ticker} {UPRO.name}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_upro(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
            else:
                send_message(f'#{UPRO.ticker} {UPRO.name}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_upro(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                time.sleep(3)
   
    return 0


