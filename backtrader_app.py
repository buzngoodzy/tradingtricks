import backtrader as bt
import datetime
import matplotlib # For plotting

# --- I. Data Handling Section ---
class GenericCSV_IMFData(bt.feeds.GenericCSVData):
    """
    Custom CSV data feed for IMF data.
    Assumes CSV columns are: Date,Open,High,Low,Close,Volume,OpenInterest
    """
    params = (
        ('dtformat', ('%Y-%m-%d')),  # Expects date in YYYY-MM-DD format
        ('datetime', 0),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('openinterest', 6), # Use -1 if not available
        # [Source: Backtrader Documentation on GenericCSVData]
    )

# Conceptual Comments for Data Handling:
# - Yahoo Finance Data: Use `bt.feeds.YahooFinanceCSVData(dataname='yahoo_data.csv')`. [Source: General Backtrader Docs/YahooFinanceCSVData]
# - Multiple Feeds: Add multiple via `cerebro.adddata()`. Access with `self.datas[i]`. [Source: General Backtrader Docs/Multiple Feeds]
# - Data Filters/Resampling: Use `data.addfilter(bt.filters.SessionFiller)` or `cerebro.resampledata(data_feed, timeframe=bt.TimeFrame.Weeks)`. [Source: General Backtrader Docs on Data Filtering/Resampling]

# --- II. Strategy Definition Section ---
class SMACrossoverStrategy(bt.Strategy):
    """
    A Simple Moving Average (SMA) Crossover strategy with a stop-loss.
    - Buys on fast SMA crossing above slow SMA.
    - Sells on fast SMA crossing below slow SMA or if stop-loss is hit.
    """
    params = (
        ('fast_sma_period', 10),
        ('slow_sma_period', 30), # Default, will be overridden in run_backtest for guaranteed_trades_data
        ('stop_loss_perc', 0.05), # 5% stop-loss
        ('printlog', True), # Parameter to control logging
    )

    def __init__(self):
        self.data_close = self.datas[0].close # Convenience alias for close price
        self.data_datetime = self.datas[0].datetime # Convenience alias for datetime
        self.fast_sma = bt.indicators.SimpleMovingAverage(self.data_close, period=self.p.fast_sma_period) # [Source: 25, 28-42]
        self.slow_sma = bt.indicators.SimpleMovingAverage(self.data_close, period=self.p.slow_sma_period) # [Source: 25, 28-42]
        self.sma_crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma) # [Source: 27, 39, 43-45]
        self.order = None
        self.buyprice = None
        self.buycomm = None # To store commission for the buy trade
        self.stop_loss_order = None

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function for this strategy, controlled by printlog parameter '''
        # [Source: 53, 74-76 for printout concept]
        if self.p.printlog or doprint:
            dt = dt or self.data_datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order): # [Source: 94 (implied for order notification), 57-60 for stop-loss]
        # Log order details if printlog is True
        if self.p.printlog:
            order_details = f'ORDER {order.ordtype_str()} {order.getstatusname()}: Ref: {order.ref}, Size: {order.size:.2f}'
            if hasattr(order.executed, 'price') and order.executed.price is not None: # Check if executed price exists
                order_details += f', Exec Price: {order.executed.price:.2f}'
            elif hasattr(order, 'price') and order.price is not None: # Use order.price if not executed (e.g. for Stop orders)
                 order_details += f', Price: {order.price:.2f}'
            self.log(order_details)

        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted - Nothing more to do
            return

        if order.status == order.Completed:
            if order.isbuy():
                self.log(f'BUY EXECUTED: Ref: {order.ref}, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, Size: {order.executed.size:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm # Store commission for this buy
                stop_price = self.buyprice * (1.0 - self.p.stop_loss_perc)
                # Use parent=order to link stop-loss to the buy order
                self.stop_loss_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=order.executed.size, parent=order)
                self.log(f'STOP-LOSS SELL ORDER (Ref: {self.stop_loss_order.ref}) PLACED: Price: {stop_price:.2f}, Linked to Buy Ref: {order.ref}')
            elif order.issell():
                # Check if this sell order is the stop-loss order
                if self.stop_loss_order and self.stop_loss_order.ref == order.ref:
                    self.log(f'STOP-LOSS ORDER EXECUTED: Ref: {order.ref}, Price: {order.executed.price:.2f}, Size: {order.executed.size:.2f}')
                    self.stop_loss_order = None # Clear the stop-loss order reference
                else: # Regular sell (profit taking / trend reversal)
                    self.log(f'PROFIT-TAKING SELL EXECUTED: Ref: {order.ref}, Price: {order.executed.price:.2f}, Size: {order.executed.size:.2f}')
                    # If there was an active stop-loss order, cancel it
                    if self.stop_loss_order:
                        self.log(f'CANCELLING ACTIVE STOP-LOSS ORDER (Ref: {self.stop_loss_order.ref}) due to profit-taking sell.')
                        self.cancel(self.stop_loss_order)
                        self.stop_loss_order = None
                # P/L for the trade is handled by notify_trade
        elif order.status in [order.Canceled, order.Margin, order.Rejected, order.Expired]:
            self.log(f'ORDER {order.getstatusname()}: Ref: {order.ref}')
            # If a stop-loss order was canceled/rejected (e.g. by us or by margin), clear the reference
            if self.stop_loss_order and self.stop_loss_order.ref == order.ref:
                self.log(f'Active STOP-LOSS ORDER (Ref: {order.ref}) was CANCELED/MARGIN/REJECTED/EXPIRED.')
                self.stop_loss_order = None

        # Reset self.order only if the order is not Accepted or Submitted (final state)
        if order.status not in [order.Accepted, order.Submitted]:
            self.order = None


    def notify_trade(self, trade): # [Source: 94 (implied for trade notification)]
        if trade.isclosed:
            self.log(f'TRADE CLOSED: Ref: {trade.ref}, PNL Gross: {trade.pnl:.2f}, PNL Net (incl comm): {trade.pnlcomm:.2f}, Commission: {trade.commission:.2f}', doprint=True)
            # Reset buy price and commission after a trade is closed
            self.buyprice = None
            self.buycomm = None
        elif trade.isopen:
            self.log(f'TRADE OPENED: Ref: {trade.ref}, Price: {trade.price:.2f}, Size: {trade.size:.2f}')


    def next(self):
        # Log Crossover and SMA values if printlog is True
        self.log(f'Crossover Value: {self.sma_crossover[0]:.2f}, FastSMA: {self.fast_sma[0]:.2f}, SlowSMA: {self.slow_sma[0]:.2f}')
        # self.log(f'Next -> Close: {self.data_close[0]:.2f}, FastSMA: {self.fast_sma[0]:.2f}, SlowSMA: {self.slow_sma[0]:.2f}, Crossover: {self.sma_crossover[0]:.2f}')


        if self.order: return # Check for pending orders

        if not self.position: # Not in the market
            if self.sma_crossover[0] > 0: # Fast > Slow SMA
                self.log(f'BUY CREATE, Close: {self.data_close[0]:.2f}, FastSMA: {self.fast_sma[0]:.2f}, SlowSMA: {self.slow_sma[0]:.2f}')
                self.order = self.buy()
        else: # Already in the market
            if self.sma_crossover[0] < 0: # Fast < Slow SMA
                self.log(f'SELL CREATE (Profit Taking/Trend Reversal), Close: {self.data_close[0]:.2f}, FastSMA: {self.fast_sma[0]:.2f}, SlowSMA: {self.slow_sma[0]:.2f}')
                self.order = self.sell()
            # Stop-loss is handled by its own order type in notify_order.

# Conceptual Comments for Strategy Section:
# - Other Indicators: MACD (`bt.indicators.MACD`), PSAR (`bt.indicators.ParabolicSAR`), RSI (`bt.indicators.RSI`). [Source: MACD/PSAR 46-50, RSI 35, 36, 51-53]
# - Parameter Passing: Override in `cerebro.addstrategy(SMACrossoverStrategy, fast_sma_period=15)`. [Source: Backtrader docs on cerebro.addstrategy]
# - Order Execution: `self.close()`, other types like `bt.Order.Limit`, `bt.Order.StopTrail`. [Source: e.g., exectype param in 97, Backtrader docs on Order Types]

# --- III. Cerebro Setup & Backtest Execution Section ---
def run_backtest():
    cerebro = bt.Cerebro(stdstats=False) # stdstats=False to disable default observers/analyzers if adding custom ones
    # [Source: 64, 69, 82 for Cerebro init]

    # --- Dynamic CSV File Loading ---
    preferred_dataname = 'guaranteed_trades_data.csv' # Updated preferred CSV
    dataname_to_load = None
    csv_files_found = glob.glob('*.csv')

    if os.path.exists(preferred_dataname):
        dataname_to_load = preferred_dataname
        print(f"Using preferred data file: {dataname_to_load}")
    elif csv_files_found:
        csv_files_found.sort() # Ensure consistent order
        dataname_to_load = csv_files_found[0]
        if len(csv_files_found) > 1:
            print(f"Multiple CSV files found. Using first sorted: {dataname_to_load}. Other files: {', '.join(csv_files_found[1:])}")
        else:
            print(f"Preferred data file not found. Using only available CSV: {dataname_to_load}")
    else:
        print("CRITICAL ERROR: No CSV data files found in the directory (neither 'guaranteed_trades_data.csv' nor any other *.csv).")
        print("Please add a CSV data file to the script's directory.")
        return # Exit if no data

    # --- Data Feed Setup with Default Dates (Adjustable) ---
    # IMPORTANT: These example dates (Jan 2022) are suitable for 'guaranteed_trades_data.csv'.
    # If using your own data, YOU MUST ADJUST 'fromdate' and 'todate' to match your data's actual range
    # and ensure there are SUFFICIENT BARS for the chosen indicator periods (e.g., > slow_sma_period).
    fromdate = datetime.datetime(2022, 1, 1) # Updated default fromdate
    todate = datetime.datetime(2022, 1, 31)   # Updated default todate

    data_feed = GenericCSV_IMFData(
        dataname=dataname_to_load,
        fromdate=fromdate,
        todate=todate,
        # [Source: 64, 69, 82 for adding data]
    )
    cerebro.adddata(data_feed)

    # --- Strategy Configuration ---
    # Example parameters, ensure they are suitable for the data and chosen indicator periods
    cerebro.addstrategy(SMACrossoverStrategy,
                        fast_sma_period=10, # Updated fast SMA
                        slow_sma_period=20, # Updated slow SMA
                        printlog=True) # Set to False to reduce console output from strategy logs
    # [Source: 64, 69, 82 for adding strategy]

    # --- Broker and Sizer Setup ---
    cerebro.broker.setcash(100000.0) # [Source: cash in 64, 69, 82]
    cerebro.broker.setcommission(commission=0.001) # [Source: commperc 65, 82, or comm 134]
    cerebro.addsizer(bt.sizers.FixedSize, stake=100) # Updated stake to 100
    # [Source: stake in 63, 65, 87, 100, 104 for sizer]

    # --- Analyzers ---
    # [Source: General Analyzer section 112-120, Sharpe 113, 116, SQN 113, 119, TradeAnalyzer 113, 118, DrawDown/AnnualReturn from BT Docs]
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio', timeframe=bt.TimeFrame.Days, riskfreerate=0.0) # riskfreerate for Sharpe
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
    cerebro.addobserver(bt.observers.Broker) # For cash and value plotting
    cerebro.addobserver(bt.observers.Trades) # For trade markers on chart
    cerebro.addobserver(bt.observers.BuySell) # For buy/sell signals on chart (might be redundant with Trades)

    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # --- Run Backtest with Error Handling ---
    try:
        results = cerebro.run() # [Source: 64, 70, 83 for run command]
    except IndexError:
        print("CRITICAL ERROR: IndexError during cerebro.run().")
        print("This often means the data period is too short for the indicator periods (e.g., slow_sma_period).")
        print(f"Data: {dataname_to_load}, From: {fromdate.strftime('%Y-%m-%d')}, To: {todate.strftime('%Y-%m-%d')}")
        print(f"Slow SMA Period: {SMACrossoverStrategy.params.slow_sma_period} (or as overridden in addstrategy)") # Needs access to actual param
        return # Exit if critical error
    except Exception as e:
        print(f"CRITICAL ERROR during cerebro.run(): {e}")
        return # Exit if critical error


    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # --- Print Analyzer Results ---
    if results and len(results) > 0:
        strat_results = results[0] # Assuming one strategy run
        print("\n--- Analyzer Results ---")

        sharpe_analysis = strat_results.analyzers.sharpe_ratio.get_analysis()
        print(f"Sharpe Ratio: {sharpe_analysis.get('sharperatio', 'N/A')}")

        sqn_analysis = strat_results.analyzers.sqn.get_analysis()
        print(f"SQN: {sqn_analysis.get('sqn', 'N/A')}")

        drawdown_analysis = strat_results.analyzers.drawdown.get_analysis()
        print(f"Max Drawdown: {drawdown_analysis.max.drawdown:.2f}%")
        print(f"Max Drawdown Money: {drawdown_analysis.max.moneydown:.2f}")
        
        annual_return_analysis = strat_results.analyzers.annual_return.get_analysis()
        print("Annual Returns:")
        for year, ret in annual_return_analysis.items():
            print(f"  {year}: {ret*100:.2f}%")

        trade_analysis = strat_results.analyzers.trade_analyzer.get_analysis()
        if trade_analysis.total.total > 0: # Check if any trades happened
            print("\n--- Trade Analysis ---")
            print(f"Total Trades: {trade_analysis.total.total}")
            print(f"Winning Trades: {trade_analysis.won.total}")
            print(f"Losing Trades: {trade_analysis.lost.total}")
            print(f"Net PnL: {trade_analysis.pnl.net.total:.2f}")
            print(f"Average Winning Trade: {trade_analysis.won.pnl.average:.2f}" if trade_analysis.won.total > 0 else "Average Winning Trade: N/A")
            print(f"Average Losing Trade: {trade_analysis.lost.pnl.average:.2f}" if trade_analysis.lost.total > 0 else "Average Losing Trade: N/A")
        else:
            print("\nNo trades were executed during this backtest.")
    else:
        print("\nNo strategy results to analyze (possibly due to errors or no trades).")

    # --- Plotting ---
    # [Source: 65-67 for plot command, style/volume options 28, 33-37, 66-73 for plot customization]
    enable_plotting = True # Set to False to disable plotting entirely
    if enable_plotting and results and results[0] and results[0].analyzers.trade_analyzer.get_analysis().total.total > 0:
        try:
            plot_filename = 'backtest_plot.png'
            print(f"\nAttempting to save plot to {plot_filename}...")
            # cerebro.plot(style='candlestick', volume=True, savefig=True, figfilename=plot_filename, figscale=1.2)
            # Using a simpler plot call for broader compatibility, add more observers for details
            cerebro.plot(savefig=True, figfilename=plot_filename, figscale=1.2)

            print(f"Plot saved to {plot_filename}. If it doesn't appear, ensure matplotlib backend is suitable (e.g., TkAgg, Qt5Agg).")
        except Exception as e:
            print(f"\nError during plotting: {e}")
            print("Plotting may require a GUI environment or a specific matplotlib backend like 'Agg' for non-GUI environments.")
            print("If you are in a headless environment, ensure 'matplotlib.use('Agg')' is set at the top of the script, or disable plotting.")
    elif enable_plotting:
        print("\nPlotting skipped as no trades were executed or results are unavailable.")
    else:
        print("\nPlotting is disabled by the 'enable_plotting' variable in the script.")


# --- IV. Conceptual Comments for Cerebro Extensions ---
# - Parameter Optimization: `cerebro.optstrategy(StrategyName, param1=range(10,20))`. [Source: Backtrader Docs on Optimization]
# - Other Analyzers/Observers: `bt.analyzers.DrawDown`, `bt.observers.Broker`. [Source: Backtrader Docs on Analyzers/Observers, PyFolio 120, 123]
# - Writers: `cerebro.addwriter(bt.WriterFile, csv=True, out='results.csv')`. [Source: Backtrader Docs on Writers]
# - PyFolio Integration: Use `bt.analyzers.PyFolio` and `pyfoliozer.get_pf_items()`. [Source: PyFolio 120, 123]

# --- V. Live Trading Extension (Conceptual Comments) ---
# - Data Feed: Replace CSV with live broker feed (e.g., `bt.stores.IBStore`). [Source: e.g., 22, 77, 46-58 for IBStore]
# - Broker Integration: Configure `ibstore = bt.stores.IBStore(host, port)`. [Source: IBStore params from BT Docs]
# - Data from Store: `data = ibstore.getdata(dataname='SYMBOL')`. [Source: General store/data pattern]
# - Broker Instance: `broker = ibstore.getbroker()`, `cerebro.setbroker(broker)`. [Source: General store/broker pattern]
# - Additional Considerations: Real-time data nuances, latency, error handling, risk management. [Source: General live trading knowledge]

if __name__ == '__main__':
    run_backtest()

# --- VI. Comparative Framework Explanations (Conceptual) ---
# IMPORTANT NOTE: Source document numbers `[like this]` are placeholders.
#
# 1. QuantConnect LEAN Engine Approach:
#   - Data Handling: `AddEquity()`, `AddUniverse()`, custom data. [Source: QC Docs - Data Handling, Universes, Asset Classes]
#   - Strategy: `QCAlgorithm`, `Initialize()`, `OnData(Slice data)`. [Source: QC Docs - Algorithm Framework, Event Handling]
#   - Indicators/Orders: `self.SMA()`, `MarketOrder()`, `SetHoldings()`. [Source: QC Docs - Indicators, Orders, Portfolio]
#   - Backtesting/Live: Unified C#/Python, wide brokerage support. [Source: QC Docs - Deployment, Brokerages, 78-83]
#   - Optimization/Analysis: Cloud optimization, web UI. [Source: QC Docs - Optimization, Analysis, 5-12]
#   - Strategy Library: Community forum, Algorithm Market. [Source: QC Docs - Strategy Library, QC Community Forum]
#
# 2. Freqtrade Approach:
#   - Strategy: `IStrategy`, `populate_indicators()`, `populate_buy_trend()`, `populate_sell_trend()`. [Source: Freqtrade Docs - Strategy Dev, Advanced Strategy]
#   - Data: Crypto OHLCV via `freqtrade download-data`, pandas DataFrames. [Source: Freqtrade Docs - Data Mgmt, Pairs & Timeframes]
#   - Indicators: `technical` library, `pandas-ta`. [Source: Freqtrade Docs - Indicators, technical/pandas-ta docs]
#   - Backtesting/Live: `freqtrade backtesting`, Dry-Run, `freqtrade trade` for crypto. [Source: Freqtrade Docs - Modes, Supported Exchanges]
#   - Hyperopt: `freqtrade hyperopt` for Bayesian optimization (buy, sell, stoploss, roi spaces). [Source: Freqtrade Docs - Hyperopt, Optimization Spaces]
#   - Community/Extensibility: Active community, customizable (notifications, plotting). [Source: Freqtrade Community, Customization Docs]
