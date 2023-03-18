# Trade-system
## Purposes
I have always liked the idea of making money from market fluctuations, so I became interested in trading quite some time ago. Of course, eventually I came to the conclusion that I wanted to automate my ideas. As a result, I created several algorithms that allow me to achieve some desired goals, specifically related to stock trading. This repository consists of several algorithms. I would like to pay attention to a robot that trades a spread of two currencies and backtesting algorithms of several of my developments with genetic parametrization.
### tradetools 
One agent, a logging and posting algorithm, and more useful features for financial series analysis.
This project started in the summer of 2021 and was initially a set of packages to be deployed on a server. Subsequently, everything was compiled into a single file for easy deployment
1) The robot for currency spread arbitrage is a python-wrapper algorithm for MT5 and QUIK terminals, which has modules for trading, logging events when the script is running, and functionality for sending reports to a mailbox. 
2) Also tradetools has many functions for various time series analysis, in particular the closing price series of financial series. Among them, I would highlight the function for linkage_for_two_instruments linkage analysis, which calculates covariance/correlation and also various spreads, lot_for_spreadtrade - helps calculate equal shares for trading two instruments based on their linkage. 
3) Algorithm for the mailing list. Part of the algorithm was taken from stackoverflow.com. Another part was written by me. It is responsible for working with excel-files, checking them and sending to the required mail.
### backtest_for_arbitrage
Backtesting for a robot trading a spread of two assets with hyperparameter settings using a genetic algorithm. Making use of such tools as backtrader, deap, tradetools.
### backtest_for_dudoladov

### backtest_for_
###


