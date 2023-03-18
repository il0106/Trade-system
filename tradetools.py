import time
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import talib as ta
import matplotlib.pyplot as plt
import csv
from datetime import datetime
import os
import smtplib
import mimetypes
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart
from typing import List
import yfinance as yf
from QuikPy import QuikPy


def write_to_file(record, name: str = 'report_robot1.csv'):
    with open(name, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';', dialect='excel')
        writer.writerow([datetime.now()] + [record])


def workday():
    if datetime.isoweekday(datetime.now()) == 7 or datetime.isoweekday(datetime.now()) == 6:
        return False
    else:
        return True


def send_email(addr_to: str, msg_subj: str, msg_text: str, files: List[str]):
    # ====== login and password ======
    addr_from = '###@yandex.ru' # privacy purposes
    password = '###' # privacy purposes
    # ================================

    msg = MIMEMultipart()
    msg['From'] = '###@yandex.ru' # privacy purposes
    msg['To'] = addr_to
    msg['Subject'] = msg_subj

    body = msg_text
    msg.attach(MIMEText(body, 'plain'))

    def attach_file(msg, filepath):
        filename = os.path.basename(filepath)
        ctype, encoding = mimetypes.guess_type(filepath)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        if maintype == 'text':  #
            with open(filepath) as fp:
                file = MIMEText(fp.read(), _subtype=subtype)
                fp.close()
        elif maintype == 'image':
            with open(filepath, 'rb') as fp:
                file = MIMEImage(fp.read(), _subtype=subtype)
                fp.close()
        elif maintype == 'audio':
            with open(filepath, 'rb') as fp:
                file = MIMEAudio(fp.read(), _subtype=subtype)
                fp.close()
        else:
            with open(filepath, 'rb') as fp:
                file = MIMEBase(maintype, subtype)
                file.set_payload(fp.read())
                fp.close()
                encoders.encode_base64(file)
        file.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(file)

    def process_attachement(msg, files):
        for f in files:
            if os.path.isfile(f):
                attach_file(msg, f)
            elif os.path.exists(f):
                dir = os.listdir(f)
                for file in dir:
                    attach_file(msg, f + "/" + file)

    process_attachement(msg, files)

    # ==================================== Configuring the provider =================================================
    server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)
    # server.starttls()
    # server.set_debuglevel(True)
    # ===============================================================================================================
    server.login(addr_from, password)
    server.send_message(msg)
    server.quit()


def check_send_clean_file(addr_to: str,
                          msg_subj: str,
                          msg_text: str,
                          path: List[str],
                          limit_megabytes: float = 5.0):
    if os.path.isfile(path[0]):
        limit_size = limit_megabytes * (2 ** 20)
        current_size = os.path.getsize(path[0])
        if current_size >= limit_size:
            send_email(addr_to, msg_subj, msg_text, path)
            f = open(path[0], 'w')
            f.close()
        else:
            write_to_file(
                f'Current file size = {current_size}, limit file size = {limit_size}.')
    else:
        write_to_file('The file was not detected at the last check.')


def linkage_for_two_instruments(symbol1: str,
                                symbol2: str,
                                horizon_mt5: int = None,
                                mt5tf: str = None,
                                yahootf: str = None,
                                start_y: str = None,
                                end_y: str = None,
                                source: str = 'mt5'):
    """
    Parameters
    ----------
    symbol1, symbol2: str
        if you use yahoo: tickers from https://finance.yahoo.com/
    start_y, end_y: str
        Time for yahoo
        YYYY-MM-DD
    yahootf: str
        Timeframe for Yahoo Finance
        Valid: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
        Intraday data cannot extend last 60 days
    mt5tf: str
        Timeframe for MetaTrader 5
        Valid: M1,M2,M3,M4,M5,M6,M10,M12,M15,M20,M30,H1,H2,H3,H4,H6,H8,H12,D1,W1,MN1
    """

    if source == 'yahoo':
        rates1 = yf.Ticker(symbol1).history(start=start_y, end=end_y, interval=yahootf)['Close']
        rates2 = yf.Ticker(symbol2).history(start=start_y, end=end_y, interval=yahootf)['Close']
    elif source == 'mt5':
        if initialize(verbose=False):
            mt5tf = mttimeframe(mt5tf)
            rates1 = pd.DataFrame(mt5.copy_rates_from_pos(symbol1, mt5tf, 1, horizon_mt5))['close']
            rates2 = pd.DataFrame(mt5.copy_rates_from_pos(symbol2, mt5tf, 1, horizon_mt5))['close']
        else:
            print('MT5 is not connected.')
            rates1 = 0
            rates2 = 0
    else:
        rates1 = 0
        rates2 = 0
    corr = np.corrcoef(rates1, rates2)[0, 1]
    cov = np.cov(rates1, rates2)
    spread_minus = rates1 - rates2
    std_spread_minus = np.std(spread_minus)
    mean_spread_minus = np.mean(spread_minus)
    spread_delenie = rates1 / rates2
    std_spread_delenie = np.std(spread_delenie)
    mean_spread_delenie = np.mean(spread_delenie)
    return print(f'''Korrelation = {corr},\
        \rСovariation = {cov[0, 0], cov[1, 1]},\
        \rstd_spread_minus = {std_spread_minus},\
        \rmean_spread_minus = {mean_spread_minus},\
        \rstd_spread_delenie = {std_spread_delenie},\
        \rmean_spread_delenie = {mean_spread_delenie}.''')


def initialize(source: int = 0,
               path_for_mt5: int = 0,
               verbose: bool = False):
    """
    Establishing a connection to the terminal

    Parameters
    ---------
        source: int = 0:
            0 - MT5;
            1 - QUIK
        path: int = 0:
            0 - home demo-MT5;
            1 - home trade-MT5;
            2 - server demo-MT5;
            3 - server trade-MT5;
            4 - home demo-QUIK;
        verbose: bool = False
            Display detailed information
    """

    if source == 0:
        init_path = "C:\\PROGRAMS\\MetaQuotes\\Терминалы\\MT5 серверный (тестовый)\\terminal64.exe"

        if path_for_mt5 == 0:
            init_path = "C:\\PROGRAMS\\MetaQuotes\\Терминалы\\MT5 серверный (тестовый)\\terminal64.exe"
        elif path_for_mt5 == 1:
            init_path = "C:\\PROGRAMS\\Брокер Just2Trade\\MT5\\terminal64.exe"
        elif path_for_mt5 == 2:
            init_path = "C:\\Users\\Administrator\\Desktop\\MT5\\terminal64.exe"
        elif path_for_mt5 == 3:
            pass

        if path_for_mt5 == 0 or path_for_mt5 == 2:
            if not mt5.initialize(init_path,
                                  login='###', #privacy purposes
                                  password='###', #privacy purposes
                                  server='MetaQuotes-Demo',
                                  timeout=60,
                                  portable=False):
                if verbose:
                    write_to_file(f'''Failed to connect to the MT5 terminal. Error: {mt5.last_error()},\
                        \rTerminal number: {path_for_mt5},\
                        \rPath of the terminal: {init_path}.''')
                mt5.shutdown()
                connection = False
            else:
                connection = True

        elif path_for_mt5 == 1 or path_for_mt5 == 3:
            if not mt5.initialize(init_path,
                                  login='###', #privacy purposes
                                  password='###', #privacy purposes
                                  server='Just2Trade-MT5',
                                  timeout=60,
                                  portable=False):
                if verbose:
                    write_to_file(f'''Failed to connect to the MT5 terminal. Error: {mt5.last_error()},\
                        \rTerminal number: {path_for_mt5},\
                        \rPath of the terminal: {init_path}.''')
                mt5.shutdown()
                connection = False
            else:
                connection = True
        else:
            connection = False

        return connection

    elif source == 1:
        quik_provider = QuikPy()
        if quik_provider.IsConnected()["data"] == 1:
            connection = True
        else:
            if verbose:
                write_to_file(f'Failed to connect to the QUIK terminal.')
            quik_provider.CloseConnectionAndThread()
            connection = False
        return connection, quik_provider

    else:
        return False


def raworder(order_type,
             symbol,
             volume,
             price,
             deviation,
             comment=None,
             ticket=None):
    order = {"action": mt5.TRADE_ACTION_DEAL,
             "symbol": symbol,
             "volume": volume,
             "type": order_type,
             "price": price,
             "deviation": deviation,
             "type_filling": mt5.ORDER_FILLING_RETURN,
             "type_time": mt5.ORDER_TIME_DAY, }
    if comment is not None:
        order["comment"] = comment
    if ticket is not None:
        order["position"] = ticket
    return mt5.order_send(order)


def close(symbol,
          deviation,
          comment: str = None,
          ticket=None,
          attempts: int = 5,
          display: bool = False):
    if ticket is not None:
        positions = mt5.positions_get(ticket=ticket)
    else:
        positions = mt5.positions_get(symbol=symbol)

    tried = 0
    done = 0

    for pos in positions:
        if pos.type == mt5.ORDER_TYPE_BUY or pos.type == mt5.ORDER_TYPE_SELL:
            tried += 1
            for tries in range(attempts):
                info = mt5.symbol_info_tick(symbol)
                if info is None:
                    return None
                if pos.type == mt5.ORDER_TYPE_BUY:
                    r = raworder(mt5.ORDER_TYPE_SELL, symbol, pos.volume, info.bid, deviation, comment, pos.ticket)
                else:
                    r = raworder(mt5.ORDER_TYPE_BUY, symbol, pos.volume, info.ask, deviation, comment, pos.ticket)
                if r is None:
                    return None
                if r.retcode != mt5.TRADE_RETCODE_REQUOTE and r.retcode != mt5.TRADE_RETCODE_PRICE_OFF:
                    if r.retcode == mt5.TRADE_RETCODE_DONE:
                        done += 1
                    break
    if done > 0:
        if done == tried:
            return True
        elif display:
            write_to_file('The position is partially closed.')
    return False


def buy(request_buy, display: bool = False):
    order_check = mt5.order_check(request_buy)

    if display:
        write_to_file('A buy signal was received. Turning on the order_check.')

    order_check_dict = order_check._asdict()
    if display:
        for field in order_check_dict.keys():
            write_to_file(f"order_check: {field} = {order_check_dict[field]}")

    order = mt5.order_send(request_buy)

    if order.retcode != mt5.TRADE_RETCODE_DONE:
        if display:
            write_to_file(f'BUY ORDER HAS NOT BEEN EXECUTED. retcode = {order.retcode}.')
            write_to_file('UNEXECUTED BUY ORDER:')

            order_dict = order._asdict()
            for field in order_dict.keys():
                write_to_file(f'{field} = {order_dict[field]}')
        return False
    else:
        if display:
            write_to_file(f'''BUY ORDER HAS BEEN EXECUTED.\
            \rBought {request_buy['symbol']} {request_buy['volume']} lots at the price {request_buy['price']},\
            \rThe acceptable spread was {request_buy['deviation']} points.''')
        return True


def sell(request_sell, display: bool = False):
    order_check = mt5.order_check(request_sell)

    if display:
        write_to_file('A sell signal was received. Turning on the order_check.')

    order_check_dict = order_check._asdict()
    if display:
        for field in order_check_dict.keys():
            write_to_file(f"order_check: {field} = {order_check_dict[field]}")

    order = mt5.order_send(request_sell)

    if order.retcode != mt5.TRADE_RETCODE_DONE:
        if display:
            write_to_file(f'SELL ORDER HAS NOT BEEN EXECUTED. retcode = {order.retcode}.')
            write_to_file('UNEXECUTED SELL ORDER:')

            order_dict = order._asdict()
            for field in order_dict.keys():
                write_to_file(f'{field} = {order_dict[field]}')
        return False
    else:
        if display:
            write_to_file(f'''SELL ORDER HAS BEEN EXECUTED.\
            \rSold {request_sell['symbol']} {request_sell['volume']} lots at the price {request_sell['price']},\
            \rThe acceptable spread was {request_sell['deviation']} points.''')
        return True


def correlation_for_symbol(symbol: str,
                           horizon: int,
                           tf: str,
                           windows_list: list = None,
                           windows: bool = False,
                           particular_information: bool = True,
                           plot: bool = False):
    connection = initialize(verbose=False)
    if connection:
        mt5tf = mttimeframe(tf)
        symb_rates = pd.DataFrame(mt5.copy_rates_from_pos(symbol, mt5tf, 1, horizon))['close']

        symbols = mt5.symbols_get(
            group='*EUR*,*USD*,*RUB*,*AUD*,*CAD*,*JPY*,*CHF*,*NZD*,*GBP*,'
                  '!*CNH*,!*SEK*,!*HKD*,!*SGD*,!*NOK*,!*DKK*,'
                  '!*TRY*,!*ZAR*,!*CZK*,!*HUF*,!*PLN*,!*RUR*,'
                  '!*LTC*,!*BTC*,!*MXN*,!*ETC*,!*MBT*,!*ZEC*,'
                  '!*XRP*,!*GEL*,!*DSH*,!*GEL*,!*ETH*,!*XMR*,'
                  '!*XTI*,!*XBR*,!*XNG*,!*EOS*,!*EMC*,!*COP*,'
                  '!*ARS*,!*CLP*,!*XAU*,!*XPD*,!*XPT*,!*XAG*')
        list_symbols = []
        for i in range(len(symbols)):
            list_symbols.append(symbols[i].name)

        kotirovki = {}
        for i in list_symbols:
            kotirovki[i] = pd.DataFrame(mt5.copy_rates_from_pos(i, mt5tf, 1, horizon))['close']

        def correl(a1, a2):
            return np.corrcoef(a1, a2)[0, 1]

        list_for_max = []
        for k, v in kotirovki.items():
            if particular_information:
                print(f'Correlation {symbol} with {k} = {correl(symb_rates, v)}')

            list_for_max.append(correl(symb_rates, v))
        list_for_max.remove(max(list_for_max))
        print(f'Maximum value for {symbol} = {max(list_for_max)}')

        if plot:
            kotirovki_frame = pd.DataFrame(kotirovki)
            kotirovki_frame[symbol] = symb_rates

            columns = len(kotirovki_frame.columns)
            fig, ax = plt.subplots(columns, 1, sharex='col', sharey='row', figsize=(20, 250))

            for i, g in zip(kotirovki_frame.columns, range(columns)):
                if windows:
                    for l in windows_list:
                        ax[g].plot(kotirovki_frame[symbol].rolling(window=l).corr(kotirovki_frame[i]),
                                   label=f'Окно={l}')
                ax[g].axhline(kotirovki_frame[[symbol, i]].corr().iloc[0, 1], c='r')
                ax[g].legend()
                ax[g].set_title(f'{symbol}-{i}')
            plt.show()


def correlation_max_for_all(horizon: int, tf: str, particular_information: bool = False):
    initialize(verbose=False)
    symbols = mt5.symbols_get(
        group='*EUR*,*USD*,*RUB*,*AUD*,*CAD*,*JPY*,*CHF*,*NZD*,*GBP*,'
              '!*CNH*,!*SEK*,!*HKD*,!*SGD*,!*NOK*,!*DKK*,'
              '!*TRY*,!*ZAR*,!*CZK*,!*HUF*,!*PLN*,!*RUR*,'
              '!*LTC*,!*BTC*,!*MXN*,!*ETC*,!*MBT*,!*ZEC*,'
              '!*XRP*,!*GEL*,!*DSH*,!*GEL*,!*ETH*,!*XMR*,'
              '!*XTI*,!*XBR*,!*XNG*,!*EOS*,!*EMC*,!*COP*,'
              '!*ARS*,!*CLP*,!*XAU*,!*XPD*,!*XPT*,!*XAG*')
    list_symbols = []
    for i in range(len(symbols)):
        list_symbols.append(symbols[i].name)

    for i in list_symbols:
        correlation_for_symbol(i, horizon, tf, particular_information=particular_information)


def lot_for_spreadtrade(symbol1, symbol2, lot):
    """
    return:
    [lot for symbol 1, lot for symbol 2]
    """
    try:
        point1 = mt5.symbol_info(symbol1)._asdict()['trade_tick_value']
    except:
        point1 = mt5.symbol_info(symbol1)._asdict()['trade_tick_value']
    try:
        point2 = mt5.symbol_info(symbol2)._asdict()['trade_tick_value']
    except:
        point2 = mt5.symbol_info(symbol2)._asdict()['trade_tick_value']

    if point1 > point2:
        koef = point1 / point2
        lot_for_sym2 = round(lot * koef, 2)
        if lot_for_sym2 == 0:
            lot_for_sym2 = lot
        return [lot, lot_for_sym2]
    elif point1 < point2:
        koef = point2 / point1
        lot_for_sym1 = round(lot * koef, 2)
        if lot_for_sym1 == 0:
            lot_for_sym1 = lot
        return [lot_for_sym1, lot]
    else:
        return [lot, lot]


def mttimeframe(tf: str):
    if tf == 'M1':
        mt5tf = mt5.TIMEFRAME_M1
    elif tf == 'M2':
        mt5tf = mt5.TIMEFRAME_M2
    elif tf == 'M3':
        mt5tf = mt5.TIMEFRAME_M3
    elif tf == 'M4':
        mt5tf = mt5.TIMEFRAME_M4
    elif tf == 'M5':
        mt5tf = mt5.TIMEFRAME_M5
    elif tf == 'M6':
        mt5tf = mt5.TIMEFRAME_M6
    elif tf == 'M10':
        mt5tf = mt5.TIMEFRAME_M10
    elif tf == 'M12':
        mt5tf = mt5.TIMEFRAME_M12
    elif tf == 'M15':
        mt5tf = mt5.TIMEFRAME_M15
    elif tf == 'M20':
        mt5tf = mt5.TIMEFRAME_M20
    elif tf == 'M30':
        mt5tf = mt5.TIMEFRAME_M30
    elif tf == 'H1':
        mt5tf = mt5.TIMEFRAME_H1
    elif tf == 'H2':
        mt5tf = mt5.TIMEFRAME_H2
    elif tf == 'H3':
        mt5tf = mt5.TIMEFRAME_H3
    elif tf == 'H4':
        mt5tf = mt5.TIMEFRAME_H4
    elif tf == 'H6':
        mt5tf = mt5.TIMEFRAME_H6
    elif tf == 'H8':
        mt5tf = mt5.TIMEFRAME_H8
    elif tf == 'H12':
        mt5tf = mt5.TIMEFRAME_H12
    elif tf == 'D1':
        mt5tf = mt5.TIMEFRAME_D1
    elif tf == 'W1':
        mt5tf = mt5.TIMEFRAME_W1
    else:
        mt5tf = mt5.TIMEFRAME_MN1
    return mt5tf


class SpreadRobot:
    def __init__(self,
                 symbol1: str,
                 symbol2: str,
                 horizon: int,
                 timeframe: str,
                 lot: float = 0.01,
                 coef_dev: float = 1.0,
                 coef_risk: float = -0.05,
                 timeperiod_for_ma: int = 60,
                 coef_for_indicator: float = 2.0,
                 magic: int = 666666,
                 min_vol1: float = 0.01,
                 min_vol2: float = 0.01,
                 grow_factor_coef_dev: float = 0.1,
                 validation_break: int = 1,
                 rewriting_attempts: int = 10,
                 comment: str = 'Spread_robot_v2.3',
                 display: bool = False):
        """
        STANDARDS: 3*timeperiod_for_ma < horizon;
        Timeframe for MetaTrader 5:
        Valid: M1,M2,M3,M4,M5,M6,M10,M12,M15,M20,M30,H1,H2,H3,H4,H6,H8,H12,D1,W1,MN1
        """

        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.horizon = horizon
        self.timeframe = timeframe
        self.lot = lot
        self.coef_dev = coef_dev
        self.coef_risk = coef_risk
        self.timeperiod_for_ma = timeperiod_for_ma
        self.coef_for_indicator = coef_for_indicator
        self.magic = magic
        self.min_vol1 = min_vol1
        self.min_vol2 = min_vol2
        self.display = display
        self.grow_factor_coef_dev = grow_factor_coef_dev
        self.validation_break = validation_break
        self.COEF_DEV = coef_dev
        self.comment = comment
        self.rewriting_attempts = rewriting_attempts

    def create_requests_close(self, symbol: str):
        """
        return:
        [request_close_short, request_close_long]
        """
        pos = mt5.positions_get(symbol=symbol)
        if pos is not None and len(pos) > 0:
            vol_of_pos = pos[0].volume
            deviation = int(self.coef_dev * mt5.symbol_info(symbol)._asdict()['spread'])

            request_close_short = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": vol_of_pos,
                "type": mt5.ORDER_TYPE_BUY,
                "price": mt5.symbol_info_tick(symbol).ask,
                "deviation": deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time": mt5.ORDER_TIME_DAY,
                "type_filling": mt5.ORDER_FILLING_RETURN, }

            request_close_long = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": vol_of_pos,
                "type": mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time": mt5.ORDER_TIME_DAY,
                "type_filling": mt5.ORDER_FILLING_RETURN, }

            return [request_close_short, request_close_long]

    def create_requests(self, symbol: str):
        """
        return:
        [request_buy, request_sell]
        """
        if symbol == self.symbol1:
            lot_for_symbol = lot_for_spreadtrade(self.symbol1, self.symbol2, self.lot)[0]
        else:
            lot_for_symbol = lot_for_spreadtrade(self.symbol1, self.symbol2, self.lot)[1]

        deviation = int(self.coef_dev * mt5.symbol_info(symbol)._asdict()['spread'])

        request_buy = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_for_symbol,
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(symbol).ask,
            "deviation": deviation,
            "magic": self.magic,
            "comment": self.comment,
            "type_time": mt5.ORDER_TIME_DAY,
            "type_filling": mt5.ORDER_FILLING_RETURN, }

        request_sell = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_for_symbol,
            "type": mt5.ORDER_TYPE_SELL,
            "price": mt5.symbol_info_tick(symbol).bid,
            "deviation": deviation,
            "magic": self.magic,
            "comment": self.comment,
            "type_time": mt5.ORDER_TIME_DAY,
            "type_filling": mt5.ORDER_FILLING_RETURN, }

        return [request_buy, request_sell]

    def order_with_rewriting(self, function, list_of_params: List):
        tries = 0
        while not function(*list_of_params):
            tries += 1
            self.coef_dev += self.grow_factor_coef_dev
            if tries == self.rewriting_attempts:
                break
            time.sleep(self.validation_break)
        self.coef_dev = self.COEF_DEV

    def close_with_rewriting(self, symbol: str):
        positions = mt5.positions_get(symbol=symbol)
        if positions is not None and len(positions) > 0:
            if positions[0].type == mt5.ORDER_TYPE_BUY:  # close long
                self.order_with_rewriting(sell, [self.create_requests_close(symbol)[1], True])
            else:  # close short
                self.order_with_rewriting(buy, [self.create_requests_close(symbol)[0], True])

    def open_with_rewriting(self, symbol: str, long: bool):
        if long:
            self.order_with_rewriting(buy, [self.create_requests(symbol=symbol)[0], True])
        else:
            self.order_with_rewriting(sell, [self.create_requests(symbol=symbol)[1], True])

    def job(self):
        write_to_file(f'Starting analysis for {self.symbol1} - {self.symbol2}.')

        connection = initialize(verbose=True)
        if connection:

            # Checking primary conditions
            symbol_info1 = mt5.symbol_info(self.symbol1)
            symbol_info2 = mt5.symbol_info(self.symbol2)
            if symbol_info1 is None or symbol_info2 is None:
                write_to_file(f'''{self.symbol1} and {self.symbol2} were not found.\
            \rError: {mt5.last_error()}.''')
                relevant1 = False
            else:
                relevant1 = True

            if symbol_info1.visible is False or symbol_info2.visible is False:
                write_to_file(
                    f'{self.symbol1} and {self.symbol2} are not visible in MarketWatch, trying to switch on.')
                if not mt5.symbol_select(self.symbol1, True) or not mt5.symbol_select(self.symbol2, True):
                    write_to_file(
                        "It was not possible to include symbols in MarketWatch, exit from the terminal.")
                    relevant2 = False
                else:
                    relevant2 = True
            else:
                relevant2 = True

            volume_min1 = mt5.symbol_info(self.symbol1)._asdict()['volume_min']
            volume_min2 = mt5.symbol_info(self.symbol2)._asdict()['volume_min']
            if volume_min1 > self.min_vol1 or volume_min2 > self.min_vol2:
                write_to_file(f'''Minimum volume {self.symbol1} = {volume_min1};\
                        \rMinimum volume {self.symbol2} = {volume_min2}.\
                        \rRequirement for instruments: {self.min_vol1} and {self.min_vol2}.''')
                relevant3 = False
            else:
                relevant3 = True

            pos1 = mt5.positions_get(symbol=self.symbol1)
            pos2 = mt5.positions_get(symbol=self.symbol2)

            if (pos1 is not None and pos2 is not None) and (len(pos1) > 0 or len(pos2) > 0):
                try:
                    vol_of_pos1 = pos1[0].volume
                except:
                    vol_of_pos1 = 0
                try:
                    vol_of_pos2 = pos2[0].volume
                except:
                    vol_of_pos2 = 0

                if vol_of_pos1 > 0 and vol_of_pos2 > 0:
                    relevant4 = False

                    # If loss of two positions is higher than limit
                    current_balance = mt5.account_info()._asdict()['balance']  # Balance
                    current_profit = mt5.account_info()._asdict()['profit']  # Current profit/loss
                    treshold_for_loss = self.coef_risk * current_balance
                    if current_profit <= treshold_for_loss:
                        write_to_file(f'''The account status does not correspond to the robot's rules:\
                                                                \rBalance = {current_balance},\
                                                                \rProfit/loss = {current_profit},\
                                                                \rThreshold for profit/loss = {treshold_for_loss},\
                                                                \rClosing positions.''')
                        self.close_with_rewriting(symbol=self.symbol1)
                        self.close_with_rewriting(symbol=self.symbol2)
                        write_to_file('Positions are closed.')
                        relevant4 = True

                    # Having two one-directional positions, close them both
                    if (pos1[0].type == 0 and pos2[0].type == 0) or (pos1[0].type == 1 and pos2[0].type == 1):
                        write_to_file('Unidirectional positions are detected. Closing unidirectional positions.')
                        self.close_with_rewriting(symbol=self.symbol1)
                        self.close_with_rewriting(symbol=self.symbol2)
                        write_to_file('Checking unidirectional positions complete.')
                        relevant4 = True

                    # If there is an unequal volume
                    elif vol_of_pos1 > 0 and vol_of_pos2 > 0 and vol_of_pos1 != vol_of_pos2:
                        write_to_file('Unequal volumes are detected.')
                        self.close_with_rewriting(symbol=self.symbol1)
                        self.close_with_rewriting(symbol=self.symbol2)
                        write_to_file('Volume check for unequal volumes complete.')
                        relevant4 = True

                # There is the first symbol volume, whereas the second one is ampty
                elif vol_of_pos1 > 0 and vol_of_pos2 == 0:
                    write_to_file('Volume is detected for the first symbol.')
                    self.close_with_rewriting(symbol=self.symbol1)
                    write_to_file('Volume check for the first symbol complete.')
                    relevant4 = True

                # Reverse to the mentioned above
                elif vol_of_pos2 > 0 and vol_of_pos1 == 0:
                    write_to_file('Volume is detected for the second symbol.')
                    self.close_with_rewriting(symbol=self.symbol2)
                    write_to_file('Volume check for the second symbol complete.')
                    relevant4 = True
                else:
                    relevant4 = True
            else:
                relevant4 = True

            if relevant1 is True and relevant2 is True and relevant3 is True:
                mt5tf = mttimeframe(self.timeframe)
                try:
                    symbol1_rates = (pd.DataFrame(mt5.copy_rates_from_pos(self.symbol1, mt5tf, 1, self.horizon)))[
                        'close']
                    symbol2_rates = (pd.DataFrame(mt5.copy_rates_from_pos(self.symbol2, mt5tf, 1, self.horizon)))[
                        'close']

                    # Calculating the spread indicator
                    spread = symbol1_rates - symbol2_rates
                    ma_for_spread = ta.TEMA(spread, timeperiod=self.timeperiod_for_ma)
                    indicator = spread - ma_for_spread
                    current_indicator = indicator[self.horizon - 1]
                    pre_current_indicator = indicator[self.horizon - 2]

                    indicator_for_std = indicator[3 * self.timeperiod_for_ma:]
                    otclonenie = self.coef_for_indicator * np.std(indicator_for_std)
                    indicator_for_std1 = indicator[
                                         3 * self.timeperiod_for_ma - 1:-1]  # here the values are slightly different from the previous indicator_for_std
                    pre_otclonenie = self.coef_for_indicator * pd.DataFrame.std(indicator_for_std1)

                    correl = np.corrcoef(symbol1_rates, symbol2_rates)[0, 1]

                    if self.display:
                        write_to_file(f'''Correlation = {correl},\
                    \rDeviation of currencies from the average spread = {current_indicator},\
                    \rPlanned deviation of currencies from the average spread = +/- {otclonenie},\
                    \rDeviation of currencies from the average spread (previous) = {pre_current_indicator},\
                    \rPlanned deviation of currencies from the average spread (previous) = +/- {pre_otclonenie}.''')

                    # Filters
                    # Buying a spread - the first symbol is bought, the second is sold
                    if current_indicator >= -otclonenie and pre_current_indicator < -pre_otclonenie:
                        write_to_file('Spread buy signal.')

                        if not relevant4:
                            write_to_file(
                                f'Already opened positions: type1 = {pos1[0].type}, type2 = {pos2[0].type}, vol1 = {pos1[0].volume}, vol2 = {pos2[0].volume}.')
                            if pos1[0].type == 1 and pos2[0].type == 0:  # If the first one is in a short, the second one is in a long
                                # Close all positions
                                write_to_file('Close all positions.')
                                self.close_with_rewriting(symbol=self.symbol1)
                                self.close_with_rewriting(symbol=self.symbol2)

                                # Open a new position with a calculated volume according to the standard
                                write_to_file('Open position - reverse.')
                                self.open_with_rewriting(symbol=self.symbol1, long=True)
                                self.open_with_rewriting(symbol=self.symbol2, long=False)

                            elif pos2[0].type == 1 and pos1[0].type == 0:  # If we are already in the right position
                                write_to_file(
                                    'Signal has been received, but we are already in position - volume increase.')
                                self.open_with_rewriting(symbol=self.symbol1, long=True)
                                self.open_with_rewriting(symbol=self.symbol2, long=False)

                        else:  # standard
                            write_to_file('Open new position.')
                            self.open_with_rewriting(symbol=self.symbol1, long=True)
                            self.open_with_rewriting(symbol=self.symbol2, long=False)

                    # Spread sale - the first symbol is sold, the second is bought
                    elif current_indicator <= otclonenie and pre_current_indicator > pre_otclonenie:
                        write_to_file('Spread sell signal.')

                        if not relevant4:
                            write_to_file(
                                f'Already opened positions: type1 = {pos1[0].type}, type2 = {pos2[0].type}, vol1 = {pos1[0].volume}, vol2 = {pos2[0].volume}.')
                            if pos2[0].type == 1 and pos1[0].type == 0:  # If the first one is in a long, the second one is in a short
                                # Close all positions
                                write_to_file('Close all positions.')
                                self.close_with_rewriting(symbol=self.symbol1)
                                self.close_with_rewriting(symbol=self.symbol2)

                                # Open a new position with a calculated volume according to the standard
                                write_to_file('Open position - reverse.')
                                self.open_with_rewriting(symbol=self.symbol1, long=False)
                                self.open_with_rewriting(symbol=self.symbol2, long=True)

                            elif pos1[0].type == 1 and pos2[0].type == 0:
                                write_to_file(
                                    'Signal has been received, but we are already in position - volume increase.')
                                self.open_with_rewriting(symbol=self.symbol1, long=False)
                                self.open_with_rewriting(symbol=self.symbol2, long=True)

                        else:  # standard
                            write_to_file('Open new position.')
                            self.open_with_rewriting(symbol=self.symbol1, long=False)
                            self.open_with_rewriting(symbol=self.symbol2, long=True)

                    else:
                        write_to_file('''There was no signal to enter.''')

                    # Checking erroneous positions after possible operations
                    pos1 = mt5.positions_get(symbol=self.symbol1)
                    pos2 = mt5.positions_get(symbol=self.symbol2)

                    if (pos1 is not None and pos2 is not None) and (len(pos1) > 0 or len(pos1) > 0):
                        try:
                            vol_of_pos1 = pos1[0].volume
                        except:
                            vol_of_pos1 = 0
                        try:
                            vol_of_pos2 = pos2[0].volume
                        except:
                            vol_of_pos2 = 0

                        if vol_of_pos1 > 0 and vol_of_pos2 > 0:
                            # Having two one-directional positions, close them both
                            if (pos1[0].type == 0 and pos2[0].type == 0) or (pos1[0].type == 1 and pos2[0].type == 1):
                                write_to_file(
                                    'Unidirectional positions are detected. Closing unidirectional positions.')
                                self.close_with_rewriting(symbol=self.symbol1)
                                self.close_with_rewriting(symbol=self.symbol2)
                                write_to_file('Checking unidirectional positions complete.')

                            # If there is an unequal volume
                            elif vol_of_pos1 > 0 and vol_of_pos2 > 0 and vol_of_pos1 != vol_of_pos2:
                                write_to_file('Unequal volumes are detected.')
                                self.close_with_rewriting(symbol=self.symbol1)
                                self.close_with_rewriting(symbol=self.symbol2)
                                write_to_file('Volume check for unequal volumes complete.')

                        # There is the first symbol volume, whereas the second one is ampty
                        elif vol_of_pos1 > 0 and vol_of_pos2 == 0:
                            write_to_file('Volume is detected for the first symbol.')
                            self.close_with_rewriting(symbol=self.symbol1)
                            write_to_file('Volume check for the first symbol complete.')

                        # Reverse to the mentioned above
                        elif vol_of_pos2 > 0 and vol_of_pos1 == 0:
                            write_to_file('Volume is detected for the second symbol.')
                            self.close_with_rewriting(symbol=self.symbol2)
                            write_to_file('Volume check for the second symbol complete.')

                    # Logging
                    try:
                        pos1 = mt5.positions_get(symbol=self.symbol1)[0]
                        type1 = pos1.type
                        vol1 = pos1.volume
                    except:
                        type1 = None
                        vol1 = 0
                    try:
                        pos2 = mt5.positions_get(symbol=self.symbol2)[0]
                        type2 = pos2.type
                        vol2 = pos2.volume
                    except:
                        type2 = None
                        vol2 = 0
                    write_to_file(
                        f'{current_indicator};{-otclonenie};{otclonenie};{pre_current_indicator};{-pre_otclonenie};{pre_otclonenie};{type1};{type2};{vol1};{vol2}',
                        name='data_robot1.csv')

                    write_to_file(f'''Analysis {self.symbol1} and {self.symbol2} completed.''')
                    mt5.shutdown()
                except KeyError:
                    write_to_file(f'''KeyError: {KeyError}.''')
                    mt5.shutdown()
            else:
                write_to_file('One of the initial conditions is not met')
                mt5.shutdown()
        else:
            mt5.shutdown()


def correction_sl_tp(symbol: str,
                     horizon: int = 50,
                     timeframe: str = 'H1',
                     period_atr: int = 24,
                     shift_atr_sl: float = 1.0,
                     adapt_atr_sl: float = 0.3,
                     adapt_atr_tp: float = 0.1,
                     display: bool = False):
    write_to_file(f'Correction for {symbol}.')

    connection = initialize(verbose=True)

    if connection:
        mt5tf = mttimeframe(timeframe)

        pos = mt5.positions_get(symbol=symbol)
        if pos is None or len(pos) == 0:
            relevant = False
        else:
            relevant = True

        if relevant:
            current_takeprofit = pos[0].tp
            current_stoploss = pos[0].sl

            symbol_rates = pd.DataFrame(mt5.copy_rates_from_pos(symbol, mt5tf, 1, horizon))
            atr = ta.ATR(symbol_rates['high'], symbol_rates['low'], symbol_rates['close'], period_atr)
            current_close = symbol_rates['close'][horizon - 1]
            current_high = symbol_rates['high'][horizon - 1]
            current_low = symbol_rates['low'][horizon - 1]
            current_atr = atr[horizon - 1]

            if current_takeprofit > current_stoploss:
                tmp_sl = current_high - current_atr * shift_atr_sl - current_stoploss
                if tmp_sl > 0:
                    new_stoploss = current_stoploss + adapt_atr_sl * tmp_sl
                else:
                    new_stoploss = current_stoploss
                new_takeprofit = current_takeprofit - adapt_atr_tp * (current_takeprofit - current_close)
            else:
                tmp_sl = current_low + current_atr * shift_atr_sl - current_stoploss
                if tmp_sl < 0:
                    new_stoploss = current_stoploss + adapt_atr_sl * tmp_sl
                else:
                    new_stoploss = current_stoploss
                new_takeprofit = current_takeprofit + adapt_atr_tp * (current_close - current_takeprofit)

            ticket = pos[0].ticket
            request_for_change = {
                "action": mt5.TRADE_ACTION_SLTP,
                'position': ticket,
                'symbol': symbol,
                "sl": new_stoploss,
                "tp": new_takeprofit}

            result = mt5.order_send(request_for_change)
            if display:
                if result.retcode != 10009:
                    write_to_file(f'''It was not possible to correct the stop-loss and take-profit.\
                        \rretcode = {result.retcode}.''')
                else:
                    write_to_file(f'''Stop-loss changed from {current_stoploss} to {new_stoploss}.\
                        \rTake-profit changed from {current_takeprofit} to {new_takeprofit}.''')

            mt5.shutdown()
        else:
            mt5.shutdown()


if __name__ == '__main__':
    # =================================== Console =================================== #
    report_robot1 = [r'C:\Users\Administrator\.spyder-py3\report_robot1.csv']
    data_robot1 = [r'C:\Users\Administrator\.spyder-py3\data_robot1.csv']
    time_for_sleep = 900
    s1 = 'AUDUSD'
    s2 = 'AUDCAD'
    # =================================== Console =================================== #
    write_to_file('Python script is activated.')
    while True:
        check_send_clean_file("il0106@yandex.ru", "ALGORITHMIC TRADING SYSTEM",
                              f"Report from ATS {datetime.now()}", report_robot1, limit_megabytes=5)
        check_send_clean_file("il0106@yandex.ru", "ALGORITHMIC TRADING SYSTEM",
                              f"Data from ATS {datetime.now()}", data_robot1, limit_megabytes=5)
        if workday():
            spread_robot = SpreadRobot(s1, s2, 72, 'M15', coef_dev=1.5, timeperiod_for_ma=21, coef_for_indicator=3.0,
                                       validation_break=1, display=True)
            spread_robot.job()
            time.sleep(time_for_sleep)
        else:
            write_to_file('WEEKEND')
            time.sleep(time_for_sleep)
