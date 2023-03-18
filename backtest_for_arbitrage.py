from __future__ import (absolute_import, division, print_function, unicode_literals)
import backtrader as bt
import tradetools as tt
import pandas as pd
import numpy as np
from datetime import datetime
import MetaTrader5 as mt5
from deap import base
from deap import creator
import random
from deap import tools
from deap import algorithms

# ============================================ Console ============================================

symbol1 = 'AUDUSD'
symbol2 = 'AUDCAD'
timeframe = 'M6'
lot = 0.01
comission = 0.01

# mt5 dates to optimise
# on m15 100200 candles are available by default (more are possible), there are 252 days in a year, that's just over 4 years
mt5_opt_date_from = datetime(2020, 9, 1)
mt5_opt_date_to = datetime(2021, 1, 1)
# даты МТ5 для теста
mt5_test_date_from = datetime(2021, 1, 2)
mt5_test_date_to = datetime(2022, 1, 1)

# BT dates for optimisation (BT times can be assigned their own, or can be referenced)
bt_opt_date_from = mt5_opt_date_from
bt_opt_date_to = mt5_opt_date_to
# BT dates for the test
bt_test_date_from = mt5_test_date_from
bt_test_date_to = mt5_test_date_to

# For the genetic process
RANDOM_SEED = 111
random.seed(RANDOM_SEED)
POPULATION_SIZE = 50
P_CROSSOVER = 0.9
P_MUTATION = 0.2
MAX_GENERATIONS = 50
HALL_OF_FAME_SIZE = 10
CROWDING_FACTOR = 20.0
BOUNDS_HIGH = [200, 50, 10]  # [horizon, timeperiod_for_ma, coef_for_indicator]
BOUNDS_LOW = [1, 1, 0.1]
NUM_OF_PARAMS = len(BOUNDS_HIGH)

list_params = [100, 20, 3]  # [horizon, timeperiod_for_ma, coef_for_indicator]

# ============================================ Work part ============================================

tt.initialize()
mt5tf = tt.mttimeframe(timeframe)
symbol1_rates_opt = pd.DataFrame(mt5.copy_rates_range(symbol1, mt5tf, mt5_opt_date_from, mt5_opt_date_to))
symbol2_rates_opt = pd.DataFrame(mt5.copy_rates_range(symbol2, mt5tf, mt5_opt_date_from, mt5_opt_date_to))
symbol1_rates_test = pd.DataFrame(mt5.copy_rates_range(symbol1, mt5tf, mt5_test_date_from, mt5_test_date_to))
symbol2_rates_test = pd.DataFrame(mt5.copy_rates_range(symbol2, mt5tf, mt5_test_date_from, mt5_test_date_to))

symbol1_rates_opt['time'] = pd.to_datetime(symbol1_rates_opt['time'], unit='s')
symbol2_rates_opt['time'] = pd.to_datetime(symbol2_rates_opt['time'], unit='s')
symbol1_rates_test['time'] = pd.to_datetime(symbol1_rates_test['time'], unit='s')
symbol2_rates_test['time'] = pd.to_datetime(symbol2_rates_test['time'], unit='s')


class MT5parser(bt.feeds.PandasData):
    lines = ('tick_volume',
             'spread',
             'real_volume',)
    params = (('nocase', True),
              ('datetime', 0),  # 'time' in the data from MT5
              ('open', 1),
              ('high', 2),
              ('low', 3),
              ('close', 4),  # symbol
              ('tick_volume', 5),
              ('spread', 6),
              ('real_volume', 7),
              # turn default values to zero
              ('volume', None),
              ('openinterest', None),)


class SpreadStrategy(bt.Strategy):
    params = dict(horizon=None,
                  timeperiod_for_ma=None,
                  coef_for_indicator=None)

    def __init__(self):
        self.close1 = self.datas[0].close
        self.close2 = self.datas[1].close
        self.spread = self.close1 - self.close2
        self.ma_for_spread = bt.talib.TEMA(self.spread,
                                           timeperiod=self.p.timeperiod_for_ma,
                                           subplot=False)
        self.indicator = self.spread - self.ma_for_spread
        self.std = bt.indicators.StandardDeviation(self.indicator,
                                                   period=self.p.horizon - 3 * self.p.timeperiod_for_ma,
                                                   subplot=False)
        self.upper_bound = self.p.coef_for_indicator * self.std
        self.lower_bound = -self.upper_bound

    def next(self):
        # buying the spread - buying the first character, selling the second
        if self.indicator[0] >= self.lower_bound[0] and self.indicator[-1] < self.lower_bound[-1]:
            size_of_pos1 = self.getposition(data=self.datas[0]).size
            size_of_pos2 = self.getposition(data=self.datas[1]).size
            if size_of_pos1 == 0 and size_of_pos2 == 0:  # if not in position
                self.buy(data=self.datas[0])
                self.sell(data=self.datas[1])
            elif size_of_pos1 < 0 < size_of_pos2:  # if the first one is in a short, the second one is in a long
                self.close(data=self.datas[0])
                self.close(data=self.datas[1])
                self.buy(data=self.datas[0])
                self.sell(data=self.datas[1])
            elif size_of_pos1 > 0 > size_of_pos2:  # if the first is in the long, the second is in the short (already the desired position)
                self.buy(data=self.datas[0])
                self.sell(data=self.datas[1])

        # spread sale - the first symbol is sold, the second is bought
        elif self.indicator[0] <= self.upper_bound[0] and self.indicator[-1] > self.upper_bound[-1]:
            size_of_pos1 = self.getposition(data=self.datas[0]).size
            size_of_pos2 = self.getposition(data=self.datas[1]).size
            if size_of_pos1 == 0 and size_of_pos2 == 0:
                self.buy(data=self.datas[1])
                self.sell(data=self.datas[0])
            elif size_of_pos1 > 0 > size_of_pos2:
                self.close(data=self.datas[1])
                self.close(data=self.datas[0])
                self.buy(data=self.datas[1])
                self.sell(data=self.datas[0])
            elif size_of_pos1 < 0 < size_of_pos2:
                self.buy(data=self.datas[1])
                self.sell(data=self.datas[0])


def sqn_for_gen(individual):
    horizon_raw = individual[0]
    timeperiod_for_ma_raw = individual[1]
    coef_for_indicator_raw = individual[2]
    horizon = int(horizon_raw)
    timeperiod_for_ma = int(timeperiod_for_ma_raw)
    coef_for_indicator = coef_for_indicator_raw

    if timeperiod_for_ma < horizon / 3:
        cerebro = bt.Cerebro()
        data1 = MT5parser(dataname=symbol1_rates_opt,
                          fromdate=bt_opt_date_from,
                          todate=bt_opt_date_to)
        data2 = MT5parser(dataname=symbol2_rates_opt,
                          fromdate=bt_opt_date_from,
                          todate=bt_opt_date_to)
        cerebro.adddata(data1)
        cerebro.adddata(data2)
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.0)
        cerebro.addsizer(bt.sizers.SizerFix, stake=100000 * lot)
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        cerebro.addstrategy(SpreadStrategy,
                            horizon=horizon,
                            timeperiod_for_ma=timeperiod_for_ma,
                            coef_for_indicator=coef_for_indicator)
        result = cerebro.run()
        return round(result[0].analyzers.sqn.get_analysis()['sqn'], 2),
    else:
        return 0,


def plot_stratagy(individual, plot_all=False):
    horizon_raw = individual[0]
    timeperiod_for_ma_raw = individual[1]
    coef_for_indicator_raw = individual[2]
    horizon = int(horizon_raw)
    timeperiod_for_ma = int(timeperiod_for_ma_raw)
    coef_for_indicator = coef_for_indicator_raw

    if timeperiod_for_ma < horizon / 3:
        cerebro = bt.Cerebro()
        data1 = MT5parser(dataname=symbol1_rates_opt,
                          fromdate=bt_opt_date_from,
                          todate=bt_opt_date_to)
        data2 = MT5parser(dataname=symbol2_rates_opt,
                          fromdate=bt_opt_date_from,
                          todate=bt_opt_date_to)
        data1.plotinfo.plot = False
        data2.plotinfo.plot = False
        cerebro.adddata(data1)
        cerebro.adddata(data2)
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=comission)
        cerebro.addsizer(bt.sizers.SizerFix, stake=1000 * lot)
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        cerebro.addstrategy(SpreadStrategy,
                            horizon=horizon,
                            timeperiod_for_ma=timeperiod_for_ma,
                            coef_for_indicator=coef_for_indicator)
        if plot_all:
            result = cerebro.run(stdstats=True)
            cerebro.plot(volume=False)
        else:
            cerebro.addobserver(bt.observers.Broker)
            cerebro.addobserver(bt.observers.Trades)
            result = cerebro.run(stdstats=False)
            cerebro.plot(volume=False)
        print(round(result[0].analyzers.sqn.get_analysis()['sqn'], 2))


def eaSimpleWithElitism(population, toolbox, cxpb, mutpb, ngen, stats=None, halloffame=None, verbose=__debug__):
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])

    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    if halloffame is None:
        raise ValueError("halloffame parameter must not be empty!")

    halloffame.update(population)
    hof_size = len(halloffame.items) if halloffame.items else 0

    record = stats.compile(population) if stats else {}
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    if verbose:
        print(logbook.stream)

    for gen in range(1, ngen + 1):
        offspring = toolbox.select(population, len(population) - hof_size)
        offspring = algorithms.varAnd(offspring, toolbox, cxpb, mutpb)

        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        offspring.extend(halloffame.items)
        halloffame.update(offspring)

        record = stats.compile(population) if stats else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        if verbose:
            print(logbook.stream)
    return population, logbook


def start_genesis():
    toolbox = base.Toolbox()
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)

    for i in range(NUM_OF_PARAMS):
        toolbox.register("hyperparameter_" + str(i),
                         random.uniform,
                         BOUNDS_LOW[i],
                         BOUNDS_HIGH[i])
    hyperparameters = ()
    for i in range(NUM_OF_PARAMS):
        hyperparameters = hyperparameters + (toolbox.__getattribute__("hyperparameter_" + str(i)),)

    toolbox.register("individualCreator",
                     tools.initCycle,
                     creator.Individual,
                     hyperparameters,
                     n=1)

    toolbox.register("populationCreator", tools.initRepeat, list, toolbox.individualCreator)

    toolbox.register("evaluate", sqn_for_gen)
    toolbox.register("select", tools.selTournament, tournsize=2)
    toolbox.register("mate",
                     tools.cxSimulatedBinaryBounded,
                     low=BOUNDS_LOW,
                     up=BOUNDS_HIGH,
                     eta=CROWDING_FACTOR)
    toolbox.register("mutate",
                     tools.mutPolynomialBounded,
                     low=BOUNDS_LOW,
                     up=BOUNDS_HIGH,
                     eta=CROWDING_FACTOR,
                     indpb=1.0 / NUM_OF_PARAMS)
    population = toolbox.populationCreator(n=POPULATION_SIZE)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("max", np.max)
    stats.register("avg", np.mean)

    hof = tools.HallOfFame(HALL_OF_FAME_SIZE)

    population, logbook = eaSimpleWithElitism(population,
                                              toolbox,
                                              cxpb=P_CROSSOVER,
                                              mutpb=P_MUTATION,
                                              ngen=MAX_GENERATIONS,
                                              stats=stats,
                                              halloffame=hof,
                                              verbose=True)
    print("Best solutions are:")
    for i in range(HALL_OF_FAME_SIZE):
        print(i, ": ", hof.items[i], ", fitness = ", hof.items[i].fitness.values[0])

# ============================================ Conclusion ============================================
