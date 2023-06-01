from tinkoff.invest import Client
import pandas as pd
from datetime import timedelta
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from tinkoff.invest import CandleInterval, Client, HistoricCandle, Quotation, SubscriptionInterval
from tinkoff.invest.utils import now
import pytz
import telegram
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


# Define the Tinkoff api token
TOKEN = 't.b7eKSJEp3fpSiiv4mVt4fWwKIxaMHM1lDMtpGsPTeyl850b9Y4MluXYv-EQrj1vEu7QfkNwqGqGPfTW9N6EvTg'

# Define the Telegram bot token
bot_token = '6202414503:AAGmVIVsV_WluHKzeRXbF89gHuK4rfgVJj8'

# Create a Telegram bot object
application = Application.builder().token(bot_token).build()

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

tickers = ["GAZP", "VTBR", "LKOH", "YNDX", "MGNT", "POLY", "SBERP", "TCSG", "CHMF", "ALRS", "MMK", "PHOR", "SNGS", "SNGSP", "NLMK", "TATN", "MTLR", "MTSS", "MOEX", "RUAL", "AFLT", "CBOM", "OZON", "AFKS", "SMLT", "SPBE", "PIKK", "IRAO", "SIBN", "RASP", "SGZH", "DSKY", "TRNFP", "RNFT", "FIVE", "BSPB", "FLOT", "UWGN", "MTLRP", "ISKJ", "POSI", "UPRO", "BELU"]
names = ["Газпром", "ВТБ", "Лукойл", "ЯНДЕКС", "Магнит", "Polymetal International", "Сбербанк России, акции привилегированные", "TCS Group", "Северсталь", "АЛРОСА", "MAGN", "ФосАгро", "Сургутнефтегаз", "Сургутнефтегаз, акции привилегированные", "НЛМК", "Татнефть", "Мечел", "МТС", "Московская Биржа", "ОК РУСАЛ", "Аэрофлот", "Московский кредитный банк", "Озон Холдингс", "АФК Система", "Группа компаний Самолет", "СПБ Биржа", "ПИК-Специализированный застройщик", "ИНТЕР РАО", "Газпром нефть", "Распадская", "Сегежа Групп", "Детский мир", "Транснефть, акции привилегированные", "РуссНефть", "X5 Retail Group", "Банк Санкт-Петербург", "Совкомфлот", "НПК ОВК", "Мечел, акции привилегированные", "Институт Стволовых Клеток Человека", "Группа Позитив", "Юнипро", "Белуга Групп"]
figi = ["BBG004730RP0", "BBG004730ZJ9", "BBG004731032", "BBG004RVFCY3", "BBG004PYF2N3", "BBG0047315Y7", "BBG00QPYJ5G1", "BBG00475K6C3", "BBG004S68507", "BBG004S689R0", "BBG0047315D0", "BBG004S681M2", "BBG004S681B4", "BBG004RVFFC0", "BBG004S68598", "BBG004S681W1", "BBG004730JJ5", "BBG008F2T3T2", "BBG004S683W7", "BBG009GSYN76", "BBG00Y91R9T3", "BBG004S68614", "BBG00F6NKQX3", "BBG002GHV6L9", "BBG004S68BH6", "BBG004S68473", "BBG004S684M6", "BBG004S68696", "BBG0100R9963", "BBG000BN56Q9", "BBG00475KHX6", "BBG00F9XX7H4", "BBG00JXPFBN0", "BBG000QJW156", "BBG000R04X57", "BBG008HD3V85", "BBG004S68FR6", "BBG000N16BP3", "BBG0145HYFY9", "BBG004S686W0", "BBG000TY1C41"]

stock_info = {"ticker": tickers, "names": names, "figi": figi}

# threshold coefficient for detecting abnormal volumes and abnormal price changes
THRESHOLD = 5.0


LENGTH_OF_GAZP_DF = 61721
LENGTH_OF_VTBR_DF = 58453
LENGTH_OF_ALRS_DF = 39065

gazp_volumes, gazp_lots, gazp_prices, gazp_time, gazp_close, gazp_high, gazp_low, gazp_bvp, gazp_svp = [], [], [], [], [], [], [], [], []
gazp_data = {"Объем": gazp_volumes, "Лоты": gazp_lots, "Цена": gazp_prices, "Время": gazp_time, "Закрытие": gazp_close, "Хай": gazp_high, "Лоу": gazp_low, "Покупка": gazp_bvp, "Продажа": gazp_svp}

alrs_volumes, alrs_lots, alrs_prices, alrs_time, alrs_close, alrs_high, alrs_low, alrs_bvp, alrs_svp = [], [], [], [], [], [], [], [], []
alrs_data = {"Объем": alrs_volumes, "Лоты": alrs_lots, "Цена": alrs_prices, "Время": alrs_time, "Закрытие": alrs_close, "Хай": alrs_high, "Лоу": alrs_low, "Покупка": alrs_bvp, "Продажа": alrs_svp}


def check_abnormal_volume_gazp(update, context):
    with Client(TOKEN) as client:
        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi="BBG004730RP0",
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

                    if len(gazp_volumes) > LENGTH_OF_GAZP_DF and len(gazp_lots) > LENGTH_OF_GAZP_DF and len(gazp_prices) > LENGTH_OF_GAZP_DF and len(gazp_time) > LENGTH_OF_GAZP_DF and len(gazp_close) > LENGTH_OF_GAZP_DF and len(gazp_high) > LENGTH_OF_GAZP_DF and len(gazp_low) > LENGTH_OF_GAZP_DF and len(gazp_bvp) > LENGTH_OF_GAZP_DF and len(gazp_svp) > LENGTH_OF_GAZP_DF:
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
                    alrs_volumes.append(int(candle.volume * quotation_to_decimal(candle.close)))
                    alrs_lots.append(get_final_lots(candle.volume)) # get_final_lots
                    alrs_prices.append(int(quotation_to_decimal(candle.close)))
                    alrs_time.append(candle.time)
                    alrs_close.append(float(quotation_to_decimal(candle.close)))
                    alrs_high.append(float(quotation_to_decimal(candle.high)))
                    alrs_low.append(float(quotation_to_decimal(candle.low)))
                    alrs_bvp.append(BVP)
                    alrs_svp.append(SVP)

                    if len(gazp_volumes) > LENGTH_OF_GAZP_DF and len(gazp_lots) > LENGTH_OF_GAZP_DF and len(gazp_prices) > LENGTH_OF_GAZP_DF and len(gazp_time) > LENGTH_OF_GAZP_DF and len(gazp_close) > LENGTH_OF_GAZP_DF and len(gazp_high) > LENGTH_OF_GAZP_DF and len(gazp_low) > LENGTH_OF_GAZP_DF and len(gazp_bvp) > LENGTH_OF_GAZP_DF and len(gazp_svp) > LENGTH_OF_GAZP_DF:
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
        prcies_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        

        '''print(len(alrs_volumes))
        print(len(alrs_lots))
        print(len(alrs_prices))
        print(len(alrs_time))
        print(len(alrs_close))
        print(len(alrs_high))
        print(len(alrs_low))
        print(len(alrs_bvp))
        print(len(alrs_svp))

        # len of gazp df is 61721
        # len of vtbr df is 58453
        # len of alrs df is 39065'''

        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prcies_mean) / prices_std
            
        if abnormal_volume >= THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                context.bot.send_message(chat_id=update.effective_chat.id, text=f'#{stock_info["ticker"][0]} {stock_info["names"][0]}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                #print(f'#{stock_info["ticker"][0]} {stock_info["names"][0]}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                #print('=========================================')
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text=f'#{stock_info["ticker"][0]} {stock_info["names"][0]}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                #print(f'#{stock_info["ticker"][0]} {stock_info["names"][0]}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                #print('=========================================')
      
    return 0

def check_abnormal_volume_alrs(update, context):
    with Client(TOKEN) as client:
        
        # try to track abnormal volumes on Alrosa
        for candle in client.get_all_candles(
            figi="BBG004S68B31",
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

                    if len(alrs_volumes) > LENGTH_OF_ALRS_DF and len(alrs_lots) > LENGTH_OF_ALRS_DF and len(alrs_prices) > LENGTH_OF_ALRS_DF and len(alrs_time) > LENGTH_OF_ALRS_DF and len(alrs_close) > LENGTH_OF_ALRS_DF and len(alrs_high) > LENGTH_OF_ALRS_DF and len(alrs_low) > LENGTH_OF_ALRS_DF and len(alrs_bvp) > LENGTH_OF_ALRS_DF and len(alrs_svp) > LENGTH_OF_ALRS_DF:
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

                    if len(alrs_volumes) > LENGTH_OF_ALRS_DF and len(alrs_lots) > LENGTH_OF_ALRS_DF and len(alrs_prices) > LENGTH_OF_ALRS_DF and len(alrs_time) > LENGTH_OF_ALRS_DF and len(alrs_close) > LENGTH_OF_ALRS_DF and len(alrs_high) > LENGTH_OF_ALRS_DF and len(alrs_low) > LENGTH_OF_ALRS_DF and len(alrs_bvp) > LENGTH_OF_ALRS_DF and len(alrs_svp) > LENGTH_OF_ALRS_DF:
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
        prcies_mean = df['Цена'].mean()
        prices_std = df['Цена'].std()
        

        '''print(len(alrs_volumes))
        print(len(alrs_lots))
        print(len(alrs_prices))
        print(len(alrs_time))
        print(len(alrs_close))
        print(len(alrs_high))
        print(len(alrs_low))
        print(len(alrs_bvp))
        print(len(alrs_svp))

        # len of gazp df is 61721
        # len of vtbr df is 58453
        # len of alrs df is 39065'''

        
        abnormal_volume = (df['Объем'].iloc[-1] - volume_mean) / volume_std
        abnormal_price_changes = (df['Цена'].iloc[-1] - prcies_mean) / prices_std
            
        if abnormal_volume >= THRESHOLD or abnormal_price_changes > THRESHOLD:
            if df["Покупка"].iloc[-1] > df["Продажа"].iloc[-1]:
                context.bot.send_message(chat_id=update.effective_chat.id, text=f'#{stock_info["ticker"][9]} {stock_info["names"][9]}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                #print(f'#{stock_info["ticker"][9]} {stock_info["names"][9]}\n🟩 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                #print('=========================================')
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text=f'#{stock_info["ticker"][9]} {stock_info["names"][9]}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                #print(f'#{stock_info["ticker"][9]} {stock_info["names"][9]}\n🔻 Аномальный объем\n{calculate_net_change(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 1])}\n{get_stock_volumes(make_million_volumes_on_int_stock_prices(df["Объем"].iloc[-1]))} ({df["Лоты"].iloc[-1]})\nПокупка: {df["Покупка"].iloc[-1]}% Продажа: {df["Продажа"].iloc[-1]}%\nВремя: {convert_time_to_moscow(df["Время"].iloc[-1])}\nЦена: {df["Цена"].iloc[-1]} ₽\n{calculate_net_change_per_day(df["Цена"].iloc[-1], df["Цена"].iloc[-1 - 840])}\nЗаметил Баффет на Уораннах.')
                #print('=========================================')
     
    return 0

# Create a CommandHandler to handle the /check_volume command
application.add_handler(CommandHandler("check_abnormal_volume_gazp", check_abnormal_volume_gazp))
application.add_handler(CommandHandler("check_abnormal_volume_alrs", check_abnormal_volume_alrs))

# Start the bot
application.run_polling()
application.idle()