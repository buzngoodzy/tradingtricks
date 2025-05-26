import backtrader as bt
import datetime
import matplotlib # For plotting

# Placeholder for Data Handling section
class GenericCSV_IMFData(bt.feeds.GenericCSVData):
    """
    Custom CSV data feed for IMF data.
    Assumes CSV columns are: Date,Open,High,Low,Close,Volume,OpenInterest
    """
    params = (
        ('dtformat', ('%Y-%m-%d')),  # Expects date in YYYY-MM-DD format
        ('datetime', 0),  # Index of the datetime column
        ('open', 1),  # Index of the open price column
        ('high', 2),  # Index of the high price column
        ('low', 3),  # Index of the low price column
        ('close', 4),  # Index of the close price column
        ('volume', 5),  # Index of the volume column
        ('openinterest', 6),  # Index of the open interest column, use -1 if not available
        # Maps CSV columns to Backtrader OHLCV fields [Source: Backtrader Documentation on GenericCSVData]
    )

# Conceptual Comments for Data Handling:
#
# Adapting for Yahoo Finance Data:
# For Yahoo Finance CSV files, Backtrader provides a specific loader:
# `bt.feeds.YahooFinanceCSVData`. This can be used similarly to GenericCSV_IMFData
# but is pre-configured for Yahoo's specific CSV format.
# Example: `data = bt.feeds.YahooFinanceCSVData(dataname='yahoo_data.csv')`
# [Source: General Backtrader Docs/YahooFinanceCSVData]
#
# Handling Multiple Data Feeds:
# Cerebro can manage multiple data feeds. Each data feed is added using `cerebro.adddata()`.
# Backtrader assigns the first data feed (data0) to the strategy by default.
# Subsequent feeds (data1, data2, etc.) can be accessed in the strategy via `self.datas[i]`.
# Example:
#   `cerebro.adddata(data_feed_1)`
#   `cerebro.adddata(data_feed_2)`
# [Source: General Backtrader Docs/Multiple Feeds]
#
# Data Filters and Resampling/Replaying:
# Backtrader allows for data manipulation through filters and resampling/replaying:
# - `addfilter()`: Can be used to apply transformations to data feeds, e.g., `bt.filters.SessionFilter`.
#   Example: `data.addfilter(bt.filters.SessionFiller)`
# - `resampledata()` / `replaydata()`: To change the timeframe of data (e.g., daily to weekly)
#   or to replay data at a different speed/frequency.
#   Example: `cerebro.resampledata(data_feed, timeframe=bt.TimeFrame.Weeks)`
# [Source: General Backtrader Docs on Data Filtering and Resampling, e.g., sections on bt.DataBase.addfilter, cerebro.resampledata]

# Placeholder for Strategy Definition section
class SMACrossoverStrategy(bt.Strategy):
    """
    A Simple Moving Average (SMA) Crossover strategy with a stop-loss.
    - Buys when the fast SMA crosses above the slow SMA.
    - Sells when the fast SMA crosses below the slow SMA.
    - Implements a percentage-based stop-loss.
    """
    params = (
        ('fast_sma_period', 10),  # Period for the fast SMA
        ('slow_sma_period', 30),  # Period for the slow SMA
        ('stop_loss_perc', 0.05), # Percentage for stop-loss (e.g., 0.05 for 5%)
    )

    def __init__(self):
        """Strategy constructor"""
        self.data0 = self.datas[0]  # Primary data feed

        # Instantiate SMAs
        # [Source: 25, 28-42]
        self.fast_sma = bt.indicators.SimpleMovingAverage(
            self.data0.close, period=self.p.fast_sma_period
        )
        self.slow_sma = bt.indicators.SimpleMovingAverage(
            self.data0.close, period=self.p.slow_sma_period
        )

        # Instantiate Crossover indicator
        # [Source: 27, 39, 43-45]
        self.sma_crossover = bt.indicators.CrossOver(
            self.fast_sma, self.slow_sma
        )

        self.order = None  # To track pending orders
        self.buyprice = None # To store the price of the last buy order
        self.stop_loss_order = None # To track the stop-loss order

    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        # [Source: 53, 74-76 for printout concept]
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """Handles order notifications."""
        # [Source: 94 (implied for order notification), 57-60 for stop-loss concept]
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted - Nothing to do
            self.log(f'ORDER {order.ordtype_str()} {order.getstatusname()}: Ref: {order.ref}, Size: {order.size}, Price: {order.price:.2f}')
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, Size: {order.executed.size}'
                )
                self.buyprice = order.executed.price
                
                # Create and submit stop-loss order
                stop_price = self.buyprice * (1.0 - self.p.stop_loss_perc)
                self.stop_loss_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=order.executed.size) # Ensure stop loss size matches buy size
                self.log(f'STOP-LOSS SELL ORDER PLACED: Price: {stop_price:.2f}, Ref: {self.stop_loss_order.ref}')

            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, Size: {order.executed.size}')
                if self.buyprice: # Ensure buyprice is set (i.e., this sell is related to a previous buy)
                    self.log(f'PROFIT/LOSS for this trade: {(order.executed.price - self.buyprice) * order.executed.size - order.executed.comm:.2f}') # Basic P/L for this specific sell
                self.buyprice = None # Reset buy price
                # If this sell order was our stop-loss order, clear it
                if self.stop_loss_order and self.stop_loss_order.ref == order.ref:
                    self.stop_loss_order = None
                    self.log('STOP-LOSS ORDER EXECUTED')


        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ORDER {order.getstatusname()}: Ref: {order.ref}')
            if self.stop_loss_order and self.stop_loss_order.ref == order.ref: # If the canceled order was the stop-loss
                self.stop_loss_order = None # Clear stop-loss order reference
                self.log('STOP-LOSS ORDER CANCELED/MARGIN/REJECTED')


        self.order = None # Reset pending order tracker, unless it's a stop-loss which has its own tracker

    def notify_trade(self, trade):
        """Handles trade notifications."""
        # [Source: 94 (implied for trade notification)]
        if trade.isclosed:
            self.log(
                f'TRADE PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}, '
                f'Commission: {trade.commission:.2f}'
            )

    def next(self):
        """Core logic for the strategy, called on each new bar."""
        # Check if an order is pending. If so, do nothing.
        if self.order:
            return

        # Check if we are in the market
        if not self.position:  # Not in the market
            if self.sma_crossover[0] > 0:  # Fast SMA crossed above Slow SMA
                self.log(f'BUY CREATE, Close: {self.data0.close[0]:.2f}, FastSMA: {self.fast_sma[0]:.2f}, SlowSMA: {self.slow_sma[0]:.2f}')
                self.order = self.buy()
        else:  # Already in the market
            # Sell signal: Fast SMA crosses below Slow SMA OR if stop-loss is hit (handled by notify_order for stop order type)
            if self.sma_crossover[0] < 0:
                self.log(f'SELL CREATE (Profit Taking/Trend Reversal), Close: {self.data0.close[0]:.2f}, FastSMA: {self.fast_sma[0]:.2f}, SlowSMA: {self.slow_sma[0]:.2f}')
                self.order = self.sell() # Regular sell for profit or trend reversal
            # Stop-loss is handled by the stop_loss_order placed in notify_order.
            # However, one might also implement a trailing stop or other conditions here.

# Conceptual Comments for Strategy Section:
#
# Other Indicators:
# - MACD (Moving Average Convergence Divergence): Can be used to identify changes in strength, direction, momentum, and duration of a trend.
#   `macd = bt.indicators.MACD(self.data0.close)`
#   `signal = macd.signal`
#   Crossover signals can be generated from `bt.indicators.CrossOver(macd.macd, macd.signal)`.
# - PSAR (Parabolic Stop and Reverse): Used to find potential reversals in the market direction. Often used as a trailing stop-loss.
#   `psar = bt.indicators.ParabolicSAR(self.datas[0])`
# - RSI (Relative Strength Index): A momentum oscillator that measures the speed and change of price movements.
#   `rsi = bt.indicators.RSI(self.data0.close, period=14)`
#   Signals can be derived from overbought (e.g., >70) or oversold (e.g., <30) conditions.
# [Source: MACD/PSAR 46-50, RSI 35, 36, 51-53]
#
# Parameter Passing to Strategies:
# Strategy parameters (defined in `params`) can be overridden when adding the strategy to Cerebro:
# `cerebro.addstrategy(SMACrossoverStrategy, fast_sma_period=15, slow_sma_period=40)`
# This allows for optimization and testing different parameter sets without modifying the strategy code directly.
# [Source: Backtrader documentation on cerebro.addstrategy]
#
# Alternative Order Execution Methods:
# - `self.close()`: Closes the current open position for the given data feed.
# - Other Order Types: Backtrader supports various order types via the `exectype` parameter in `buy()`/`sell()`:
#   - `bt.Order.Limit`: Buy or sell at a specific price or better.
#   - `bt.Order.StopLimit`: A Stop order that, once triggered, becomes a Limit order.
#   - `bt.Order.Market`: Execute at the current market price (default).
#   - `bt.Order.StopTrail`: A trailing stop-loss order.
# [Source: e.g., exectype parameter in 97, Backtrader documentation on Order Types]

# Placeholder for Cerebro Setup section

def run_backtest():
    # --- Cerebro Setup Section ---
    cerebro = bt.Cerebro() # [Source: 64, 69, 82]

    # --- Data Feed ---
    data_feed = GenericCSV_IMFData(
        dataname='sample_imf_data.csv',
        fromdate=datetime.datetime(2020, 1, 1),
        todate=datetime.datetime(2020, 1, 24) # Use the actual end date of sample data
    )
    cerebro.adddata(data_feed) # [Source: 64, 69, 82]

    # --- Add Strategy ---
    cerebro.addstrategy(SMACrossoverStrategy, fast_sma_period=5, slow_sma_period=15) # [Source: 64, 69, 82]

    # --- Set Initial Cash ---
    cerebro.broker.setcash(100000.0) # [Source: cash in 64, 69, 82]

    # --- Set Commission ---
    cerebro.broker.setcommission(commission=0.001) # [Source: commperc 65, 82, or comm 134]

    # --- Add Sizer ---
    cerebro.addsizer(bt.sizers.FixedSize, stake=10) # [Source: stake in 63, 65, 87, 100, 104]

    # --- Add Analyzers ---
    # [Source: General Analyzer section 112-120, Sharpe Ratio 113, 116, SQN 113, 119, TradeAnalyzer 113, 118]
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio', timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # --- Run Backtest ---
    results = cerebro.run() # [Source: 64, 70, 83]

    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # --- Print Analyzer Results ---
    if results and len(results) > 0: # Check if results exist
        strat = results[0] # Assuming one strategy
        print('\n--- SCALAR ANALYZERS ---')
        sharpe_analysis = strat.analyzers.sharpe_ratio.get_analysis()
        sqn_analysis = strat.analyzers.sqn.get_analysis()
        
        print(f"Sharpe Ratio: {sharpe_analysis.get('sharperatio', 'N/A')}") # Use .get for safety
        print(f"SQN: {sqn_analysis.get('sqn', 'N/A')}")

        print('\n--- TRADE ANALYZER ---')
        trade_analysis = strat.analyzers.trade_analyzer.get_analysis()
        if trade_analysis:
            print(f"Total Trades: {trade_analysis.total.get('total', 0)}")
            print(f"Winning Trades: {trade_analysis.won.get('total', 0)}")
            print(f"Losing Trades: {trade_analysis.lost.get('total', 0)}")
            pnl_net = trade_analysis.pnl.net if hasattr(trade_analysis.pnl, 'net') else None
            if pnl_net:
                 print(f"Net PnL: {pnl_net.get('total', 0.0):.2f}")
            else:
                print("Net PnL: N/A")

            # Additional trade statistics
            print(f"Average Winning Trade: {trade_analysis.won.pnl.average:.2f}" if trade_analysis.won.total > 0 else "Average Winning Trade: N/A")
            print(f"Average Losing Trade: {trade_analysis.lost.pnl.average:.2f}" if trade_analysis.lost.total > 0 else "Average Losing Trade: N/A")
            print(f"Longest Winning Streak: {trade_analysis.streak.won.longest}" if hasattr(trade_analysis.streak.won, 'longest') else "Longest Winning Streak: N/A")
            print(f"Longest Losing Streak: {trade_analysis.streak.lost.longest}" if hasattr(trade_analysis.streak.lost, 'longest') else "Longest Losing Streak: N/A")

        else:
            print("No trades to analyze.")
    else:
        print("No strategy results to analyze.")
        
    # --- Plot Results ---
    # [Source: 65, 66, 67, style/volume options 28, 33-37, 66-73]
    # Note: Plotting in some environments might require `matplotlib.use('Agg')` if a display is not available.
    # The plot will be saved to a file (e.g., plot.png) or displayed interactively.
    try:
        # cerebro.plot(style='candlestick', volume=True)
        # For environments where interactive plotting is an issue, or to save the plot:
        # cerebro.plot(style='candlestick', volume=True, savefig=True, figfilename='backtest_plot.png')
        # For now, let's try with a simple plot command. If it fails in the test environment, this will be adjusted.
        # Disabling plot for now to ensure script runs in headless environments.
        # cerebro.plot(style='candlestick', volume=True)
        print("\nPlotting is disabled in this version to ensure compatibility with headless environments.")
        print("To enable plotting, uncomment 'cerebro.plot(...)' and ensure a GUI or 'Agg' backend is available.")

    except Exception as e:
        print(f"\nError during plotting: {e}. Plotting might require a GUI environment or specific matplotlib backend.")


# Conceptual Comments for Cerebro Section:
#
# Parameter Optimization:
# - `cerebro.optstrategy(StrategyName, param1=range(10, 20), param2=[True, False])`
#   Allows testing a strategy with different combinations of parameters to find optimal ones.
#   Each parameter combination runs as a separate backtest.
#   [Source: Backtrader documentation on Optimization]
#
# Other Analyzers and Observers:
# - Analyzers:
#   - `bt.analyzers.DrawDown`: Calculates maximum drawdown.
#   - `bt.analyzers.AnnualReturn`: Provides annualized returns.
#   - `bt.analyzers.LogReturns`: Computes log returns.
#   - `bt.analyzers.PyFolio`: Integrates with PyFolio for advanced performance analysis. (Requires PyFolio installation)
# - Observers:
#   - `bt.observers.Broker`: Shows cash and value.
#   - `bt.observers.Trades`: Marks trades on the chart.
#   - `bt.observers.BuySell`: Shows buy/sell signals.
#   - `bt.observers.Value`: Plots portfolio value over time.
#   Example: `cerebro.addobserver(bt.observers.Broker)`
#   [Source: Backtrader documentation on Analyzers and Observers, PyFolio 120, 123]
#
# Cerebro Writers:
# - `cerebro.addwriter(bt.WriterFile, csv=True, out='backtest_results.csv')`
#   Saves the results of the backtest (e.g., trades, cash value over time) to a CSV file.
#   Useful for external analysis or record-keeping.
#   [Source: Backtrader documentation on Writers]
#
# Alternative Run Modes:
# - `runonce=False`: If set in `cerebro.run(runonce=False)`, it allows multiple strategies to run concurrently,
#   sharing the same data feed. Useful for comparing strategies.
# - Step-by-step execution (for debugging or custom logic):
#   ```python
#   for i, data in enumerate(cerebro.rundatas):
#       # Custom logic for each data feed or bar
#       pass
#   ```
#   This is a more advanced usage and less common for standard backtests.
#   [Source: General Backtrader documentation, e.g., 24, 47, 50, 61-64 for general execution concepts]
#
# PyFolio Integration:
# - Requires `bt.analyzers.PyFolio` to be added.
# - After running, the `get_pf_items()` method of the PyFolio analyzer can be used
#   to generate inputs for PyFolio's `create_full_tear_sheet`.
#   Example:
#   ```python
#   # cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
#   # ... after cerebro.run() ...
#   # pyfoliozer = results[0].analyzers.getbyname('pyfolio')
#   # returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()
#   # import pyfolio as pf
#   # pf.create_full_tear_sheet(returns, positions=positions, transactions=transactions, gross_lev=gross_lev)
#   ```
#   [Source: PyFolio 120, 123, Backtrader documentation on PyFolio analyzer]

# --- V. Live Trading Extension (Conceptual Comments) ---
#
# For live trading, the overall structure of the Backtrader application remains,
# but key components related to data feeds and broker interaction are replaced.
#
# Data Feed Replacement:
# For live trading, the historical data feed (`GenericCSV_IMFData`) would be replaced
# with a live data feed from a broker.
#
# Broker Integration:
# This typically involves using a store interface provided by Backtrader, such as
# `bt.stores.IBStore` for Interactive Brokers [Source: e.g., 22, 77, 46-58 for IBStore concept],
# and configuring it with your broker's connection details.
#
# Cerebro Configuration:
# Cerebro would be configured to use this live store. For instance, to connect to
# Interactive Brokers:
#   `ibstore = bt.stores.IBStore(host='127.0.0.1', port=7497)` (example parameters).
#   [Source: IBStore parameters from Backtrader documentation]
#
# Adding Data from Store:
# Live data for a specific symbol would be fetched from the store and added to Cerebro:
#   `data = ibstore.getdata(dataname='YOUR_SYMBOL')` # Replace 'YOUR_SYMBOL' with the actual ticker
#   `cerebro.adddata(data)`
#   [Source: General store/data retrieval pattern in Backtrader documentation]
#
# Broker Instance:
# A live broker instance would also be set up using the store:
#   `broker = ibstore.getbroker()`
# And then added to Cerebro:
#   `cerebro.setbroker(broker)`
#   [Source: General store/broker retrieval pattern in Backtrader documentation]
#
# Strategy Logic:
# The core strategy logic within `SMACrossoverStrategy.next()` (i.e., the conditions
# for generating buy/sell signals based on indicator crossovers) would largely remain the same.
#
# Order Execution:
# However, order execution methods like `self.buy()` and `self.sell()` within the
# strategy would now interact directly with the live broker, sending actual orders
# to the market instead of simulating them. The `notify_order` and `notify_trade`
# methods would receive updates about these live orders and trades.
#
# Additional Considerations:
# - Real-time Data: Live data feeds often have different characteristics than historical data
#   (e.g., tick-by-tick updates vs. OHLC bars). Strategies might need adjustments.
# - Latency: Network and broker latency can affect order execution and fill prices.
# - Disconnections & Error Handling: Robust error handling for API disconnections,
#   order rejections, or other broker-related issues is crucial.
# - Risk Management: Sizers, stop-loss mechanisms, and overall risk management
#   parameters might need to be more conservative or dynamically adjusted for live trading.
# - API Keys & Security: Secure management of API keys and credentials is paramount.
# - Broker Specifics: Different brokers might have different data formats, order types,
#   or API limitations that need to be accommodated.
#   [Source: General considerations for live trading systems, common knowledge in algorithmic trading]


if __name__ == '__main__':
    run_backtest()

# --- VI. Comparative Framework Explanations ---
#
# IMPORTANT NOTE: The following explanations are based on general knowledge of
# QuantConnect LEAN and Freqtrade. Specific features and their implementation
# details can vary. Source document numbers `[like this]` are placeholders
# and should be verified against your specific source materials.
#

# 1. QuantConnect LEAN Engine Approach:
#
#   - **Data Handling:**
#     - LEAN supports various asset classes through methods like `AddEquity()`, `AddForex()`, `AddCrypto()`, `AddFuture()`, `AddOption()`.
#       It handles data resolution (tick, second, minute, hour, daily) and allows users to specify desired timeframes.
#     - Universe selection (`AddUniverse()`) enables dynamic selection of assets based on criteria (e.g., top N by dollar volume).
#       `UniverseSettings` control aspects like data normalization and leverage for assets in the universe.
#     - Supports custom data sources for alternative datasets (e.g., sentiment, fundamentals).
#     - [Source: QC Docs - Data Handling, QC Docs - Universes, QC Docs - Asset Classes]
#
#   - **Strategy Definition:**
#     - Strategies are typically classes inheriting from `QCAlgorithm`.
#     - The `Initialize()` method is crucial for one-time setup: setting cash, broker, adding securities/universes,
#       scheduling events (e.g., rebalancing), and initializing indicators.
#     - `OnData(Slice data)` is the primary event handler, called when new data (market, custom, etc.) arrives.
#       Trade logic, signal generation, and order placement usually occur here.
#     - Other event handlers like `OnOrderEvent(OrderEvent orderEvent)` and `OnSecuritiesChanged(SecurityChanges changes)`
#       allow reactions to order status updates and universe changes.
#     - [Source: QC Docs - Algorithm Framework, QC Docs - Event Handling, QC Docs - Scheduling Events]
#
#   - **Indicators & Orders:**
#     - LEAN provides a rich library of built-in indicators (e.g., `self.SMA()`, `self.EMA()`, `self.RSI()`, `self.MACD()`).
#       Custom indicators can also be created.
#     - Various order types are supported: `MarketOrder()`, `LimitOrder()`, `StopMarketOrder()`, `StopLimitOrder()`,
#       `MarketOnOpenOrder()`, `MarketOnCloseOrder()`.
#     - Portfolio construction helpers like `SetHoldings(symbol, percentage)` simplify allocation.
#       Bracket orders (take profit and stop loss) can be created with `LimitOrder()` and `StopMarketOrder()` in conjunction.
#     - [Source: QC Docs - Indicators, QC Docs - Order Types, QC Docs - Portfolio Construction]
#
#   - **Backtesting/Live:**
#     - LEAN offers a unified approach for both backtesting and live trading, primarily using C# with Python support.
#       The same algorithm code can be deployed for both, minimizing discrepancies.
#     - Supports a wide range of brokerages for live deployment, including Interactive Brokers, OANDA, FXCM,
#       and several major cryptocurrency exchanges (e.g., Binance, Coinbase Pro, Kraken).
#     - [Source: QC Docs - Deployment, QC Docs - Brokerages, 78-83]
#
#   - **Optimization & Analysis:**
#     - QuantConnect Cloud provides powerful, distributed parameter optimization capabilities.
#     - The platform offers built-in charting and performance analysis tools within the web interface.
#     - Results can be analyzed through detailed statistics, logs, and visualizations.
#     - "Strategy Explorer" or similar tools might be available for deeper analysis of backtest results.
#     - [Source: QC Docs - Optimization, QC Docs - Analysis, 5-12]
#
#   - **Strategy Library:**
#     - QuantConnect hosts a community forum where users share strategies and ideas.
#     - They also offer a "Strategy Library" or "Algorithm Market" with pre-built strategies or templates,
#       some free and some for a fee, which can be used as starting points or for inspiration.
#     - [Source: QC Docs - Strategy Library, QC Community Forum]
#
# 2. Freqtrade Approach:
#
#   - **Strategy Definition:**
#     - Strategies are Python classes inheriting from `IStrategy`.
#     - `populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame`:
#       This method is used to define and calculate all necessary technical indicators.
#       It receives a pandas DataFrame of historical OHLCV data and should return a DataFrame with indicator columns added.
#     - `populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame`:
#       Defines the conditions for entering a buy trade. It should set a 'buy' column (e.g., with 1 or True) on rows where buy signals occur.
#     - `populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame`:
#       Defines the conditions for exiting a trade (sell signal). It should set a 'sell' column.
#     - Optional methods like `minimal_roi_table` (for ROI-based selling), `stoploss_calculator` (for custom stop-loss logic),
#       and `custom_stake_amount` (for dynamic stake sizing) allow further customization.
#     - [Source: Freqtrade Docs - Strategy Development, Freqtrade Docs - Advanced Strategy]
#
#   - **Data Handling:**
#     - Freqtrade primarily focuses on cryptocurrency trading and ingests OHLCV (kline) data.
#     - Data is typically downloaded using the `freqtrade download-data` command, which fetches historical data
#       from supported cryptocurrency exchanges (e.g., Binance, Kraken, Bittrex).
#     - Data is stored locally (often as JSON files) and loaded into pandas DataFrames for strategy processing.
#     - Custom data pairs and different timeframes (e.g., 1m, 5m, 1h, 1d) are supported.
#     - [Source: Freqtrade Docs - Data Management, Freqtrade Docs - Pairs & Timeframes]
#
#   - **Indicators:**
#     - Freqtrade heavily relies on the `technical` library (which is bundled with it) for a wide range of indicators.
#     - It also supports the popular `pandas-ta` library, allowing users to access an even broader set of indicators.
#     - Indicators are calculated within the `populate_indicators` method of the strategy, typically operating on pandas DataFrames.
#     - [Source: Freqtrade Docs - Indicators, technical library documentation, pandas-ta documentation]
#
#   - **Backtesting & Live:**
#     - Freqtrade is designed primarily for cryptocurrency trading.
#     - **Backtesting Mode (`freqtrade backtesting`):** Allows testing strategies on historical data to evaluate performance.
#       Generates detailed reports with key metrics.
#     - **Dry-Run Mode:** Simulates live trading using real-time data from an exchange but without executing actual orders.
#       Useful for testing strategy behavior in current market conditions.
#     - **Live Trading Mode (`freqtrade trade`):** Deploys the strategy to trade with real funds on a connected exchange.
#     - [Source: Freqtrade Docs - Modes of Operation, Freqtrade Docs - Supported Exchanges]
#
#   - **Hyperopt:**
#     - Freqtrade includes a powerful built-in feature for parameter optimization called Hyperopt (`freqtrade hyperopt`).
#     - It uses Bayesian optimization techniques to find optimal strategy parameters.
#     - Optimization is typically performed over predefined "spaces":
#       - `buy`: Optimizes parameters used in buy signal generation.
#       - `sell`: Optimizes parameters used in sell signal generation.
#       - `stoploss`: Optimizes the stop-loss value.
#       - `roi`: Optimizes the "Return On Investment" table (for time-based profit taking).
#       - `trailing`: Optimizes parameters for trailing stop-loss.
#     - Users define parameter ranges and Hyperopt searches for the best combination based on a chosen loss function.
#     - [Source: Freqtrade Docs - Hyperopt, Freqtrade Docs - Optimization Spaces]
#
#   - **Community & Extensibility:**
#     - Freqtrade has an active open-source community.
#     - It is highly extensible, allowing users to customize various aspects, including data providers (beyond exchanges),
#       notifications (e.g., Telegram, Discord), and plotting.
#     - Custom strategy development is a core feature.
#     - [Source: Freqtrade Community Resources, Freqtrade Docs - Customization]
#
