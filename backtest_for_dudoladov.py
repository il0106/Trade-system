from __future__ import (absolute_import, division, print_function, unicode_literals)
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

pd.set_option('display.max_columns', 50)
pd.set_option('display.max_rows', 50)
pd.set_option('display.max_colwidth', 100)


def find_max(dataframe, col_name, new_col_name, vol):
    dataframe[f'signal_{new_col_name}'] = None
    left_trigger = None
    right_trigger = None
    sup_list = []

    col = dataframe[col_name]

    col_for_r = list(zip(dataframe[col_name].index, dataframe[col_name]))

    idx_signal = None

    for i in range(len(col)):

        x = col[i]

        for l in col[:i][::-1]:
            if x - l < 0:
                left_trigger = False
                break
            elif x - l >= vol:
                left_trigger = True
                break
            else:
                left_trigger = False

        for r in col_for_r[i + 1:]:
            if x - r[1] < 0:
                right_trigger = False
                break
            elif x - r[1] >= vol:
                right_trigger = True

                idx_signal = r[0]

                break

            else:
                right_trigger = False

        if (left_trigger is True) and (right_trigger is True):
            sup_list.append(x)
            dataframe.loc[idx_signal, f'signal_{new_col_name}'] = x

        else:
            sup_list.append(None)

    dataframe[new_col_name] = sup_list

    return dataframe


def find_min(dataframe, col_name, new_col_name, vol):
    dataframe[f'signal_{new_col_name}'] = None
    left_trigger = None
    right_trigger = None
    sup_list = []

    col = dataframe[col_name]
    col_for_r = list(zip(dataframe[col_name].index, dataframe[col_name]))

    idx_signal = None

    for i in range(len(col)):

        x = col[i]

        for l in col[:i][::-1]:
            if l - x < 0:
                left_trigger = False
                break
            elif l - x >= vol:
                left_trigger = True
                break
            else:
                left_trigger = False

        for r in col_for_r[i + 1:]:
            if r[1] - x < 0:
                right_trigger = False
                break
            elif r[1] - x >= vol:
                right_trigger = True

                idx_signal = r[0]

                break

            else:
                right_trigger = False

        if (left_trigger is True) and (right_trigger is True):
            sup_list.append(x)
            dataframe.loc[idx_signal, f'signal_{new_col_name}'] = x

        else:
            sup_list.append(None)

    dataframe[new_col_name] = sup_list

    return dataframe


def trend_detector1(dataframe,
                    name_series,
                    name_max,
                    name_min):
    """
    :param dataframe:
        pd.DataFrame
    :param name_series:
        pd.Series with time series, which will be as a signal for some intersections of extremes
    :param name_max:
        pd.Series with upper extreme of series mentioned above
    :param name_min:
        pd.Series with lower extreme of series mentioned above
    :return:
        updated dataframe
    """

    price = dataframe[name_series]
    max_ext = dataframe[name_max]  # сигнал_макс
    min_ext = dataframe[name_min]

    dataframe['trend_detector1'] = None

    zipped_data = list(zip(dataframe.index, price, max_ext, min_ext))

    last_max = zipped_data[1][2]
    last_min = zipped_data[1][3]
    pre_last_max = zipped_data[0][2]
    pre_last_min = zipped_data[0][3]

    trend_operator = None
    waiting_for_max = None
    waiting_for_min = None

    for index in range(1, len(zipped_data)):

        cur_ziprow = zipped_data[index]
        pre_ziprow = zipped_data[index - 1]

        if cur_ziprow[2] != pre_ziprow[2]:
            last_max = cur_ziprow[2]  # записали текущий максимум
            pre_last_max = pre_ziprow[2]  # записали прошлый максимум
            waiting_for_max = False  # больше не ожидаем экстремума

        if cur_ziprow[3] != pre_ziprow[3]:
            last_min = cur_ziprow[3]
            pre_last_min = pre_ziprow[3]
            waiting_for_min = False

        if trend_operator is None:  # если первое определение тренда (допускаетя любой рассчёт)

            # Определение восходящего тренда (1)
            if (last_max is not None and
                    last_min is not None and
                    pre_last_min is not None and
                    cur_ziprow[1] > last_max > pre_ziprow[1] and  # цена пересекла верхний экстремум снизу вверх
                    pre_last_min < last_min):
                waiting_for_max = True
                trend_operator = 1

            elif (last_max is not None and
                  last_min is not None and
                  pre_last_max is not None and
                  pre_last_min is not None and
                  last_min > pre_last_min and
                  pre_last_max < last_max and
                  waiting_for_min is False):
                trend_operator = 1

            # Определение нисходящего тренда (-1)
            elif (last_max is not None and
                  last_min is not None and
                  pre_last_max is not None and
                  cur_ziprow[1] < last_min < pre_ziprow[1] and  # цена пересекла нижний экстремум сверху вниз
                  last_max < pre_last_max):
                waiting_for_min = True
                trend_operator = -1

            elif (last_max is not None and
                  last_min is not None and
                  pre_last_max is not None and
                  pre_last_min is not None and
                  last_min < pre_last_min and
                  last_max < pre_last_max and
                  waiting_for_max is False):
                trend_operator = -1

            # Определение флэта (0)
            elif (last_max is not None and  # первый вариант - только экстремумы
                  last_min is not None and
                  pre_last_max is not None and
                  pre_last_min is not None and
                  waiting_for_min is False and
                  waiting_for_max is False and
                  ((last_max > pre_last_max and last_min < pre_last_min) or
                   (last_max < pre_last_max and last_min > pre_last_min))):
                trend_operator = 0

            elif (last_max is not None and  # второй вариант - цена пересекла max_ext
                  last_min is not None and
                  pre_last_min is not None and
                  waiting_for_min is False and
                  cur_ziprow[1] > last_max > pre_ziprow[1] and
                  last_min < pre_last_min):
                waiting_for_max = True
                trend_operator = 0

            elif (last_max is not None and  # третий вариант - цена пересекла min_ext
                  last_min is not None and
                  pre_last_max is not None and
                  waiting_for_max is False and
                  cur_ziprow[1] < last_min < pre_ziprow[1] and
                  last_max > pre_last_max):
                waiting_for_min = True
                trend_operator = 0

        elif trend_operator == 1:  # если мы находимся в восходящем тренде

            # Определение нисходящего тренда (-1)
            if (last_max is not None and
                    last_min is not None and
                    pre_last_max is not None and
                    cur_ziprow[1] < last_min < pre_ziprow[1] and  # цена пересекла нижний экстремум сверху вниз
                    last_max < pre_last_max):
                waiting_for_min = True
                trend_operator = -1

            elif (last_max is not None and
                  last_min is not None and
                  pre_last_max is not None and
                  pre_last_min is not None and
                  last_min < pre_last_min and
                  last_max < pre_last_max and
                  waiting_for_max is False):
                trend_operator = -1

            # Определение флэта (0)
            elif (last_max is not None and  # первый вариант - только экстремумы
                  last_min is not None and
                  pre_last_max is not None and
                  pre_last_min is not None and
                  waiting_for_min is False and
                  waiting_for_max is False and
                  ((last_max > pre_last_max and last_min < pre_last_min) or
                   (last_max < pre_last_max and last_min > pre_last_min))):
                trend_operator = 0

            elif (last_max is not None and  # второй вариант - цена пересекла max_ext
                  last_min is not None and
                  pre_last_min is not None and
                  waiting_for_min is False and
                  cur_ziprow[1] > last_max > pre_ziprow[1] and
                  last_min < pre_last_min):
                waiting_for_max = True
                trend_operator = 0

            elif (last_max is not None and  # третий вариант - цена пересекла min_ext
                  last_min is not None and
                  pre_last_max is not None and
                  waiting_for_max is False and
                  cur_ziprow[1] < last_min < pre_ziprow[1] and
                  last_max > pre_last_max):
                waiting_for_min = True
                trend_operator = 0

        elif trend_operator == -1:  # если мы находимся в нисходящем тренде
            # Определение восходящего тренда (1)
            if (last_max is not None and
                    last_min is not None and
                    pre_last_min is not None and
                    cur_ziprow[1] > last_max > pre_ziprow[1] and  # цена пересекла верхний экстремум снизу вверх
                    pre_last_min < last_min):
                waiting_for_max = True
                trend_operator = 1

            elif (last_max is not None and
                  last_min is not None and
                  pre_last_max is not None and
                  pre_last_min is not None and
                  last_min > pre_last_min and
                  pre_last_max < last_max and
                  waiting_for_min is False):
                trend_operator = 1

            # Определение флэта (0)
            elif (last_max is not None and  # первый вариант - только экстремумы
                  last_min is not None and
                  pre_last_max is not None and
                  pre_last_min is not None and
                  waiting_for_min is False and
                  waiting_for_max is False and
                  ((last_max > pre_last_max and last_min < pre_last_min) or
                   (last_max < pre_last_max and last_min > pre_last_min))):
                trend_operator = 0

            elif (last_max is not None and  # второй вариант - цена пересекла max_ext
                  last_min is not None and
                  pre_last_min is not None and
                  waiting_for_min is False and
                  cur_ziprow[1] > last_max > pre_ziprow[1] and
                  last_min < pre_last_min):
                waiting_for_max = True
                trend_operator = 0

            elif (last_max is not None and  # третий вариант - цена пересекла min_ext
                  last_min is not None and
                  pre_last_max is not None and
                  waiting_for_max is False and
                  cur_ziprow[1] < last_min < pre_ziprow[1] and
                  last_max > pre_last_max):
                waiting_for_min = True
                trend_operator = 0

        elif trend_operator == 0:  # Если мы во флэте

            # Определение восходящего тренда (1)
            if (last_max is not None and
                    last_min is not None and
                    pre_last_min is not None and
                    cur_ziprow[1] > last_max > pre_ziprow[1] and  # цена пересекла верхний экстремум снизу вверх
                    pre_last_min < last_min):
                waiting_for_max = True
                trend_operator = 1

            elif (last_max is not None and
                  last_min is not None and
                  pre_last_max is not None and
                  pre_last_min is not None and
                  last_min > pre_last_min and
                  pre_last_max < last_max and
                  waiting_for_min is False):
                trend_operator = 1

            # Определение нисходящего тренда (-1)
            elif (last_max is not None and
                  last_min is not None and
                  pre_last_max is not None and
                  cur_ziprow[1] < last_min < pre_ziprow[1] and  # цена пересекла нижний экстремум сверху вниз
                  last_max < pre_last_max):
                waiting_for_min = True
                trend_operator = -1

            elif (last_max is not None and
                  last_min is not None and
                  pre_last_max is not None and
                  pre_last_min is not None and
                  last_min < pre_last_min and
                  last_max < pre_last_max and
                  waiting_for_max is False):
                trend_operator = -1

        dataframe.loc[cur_ziprow[0], 'trend'] = trend_operator

    return dataframe





