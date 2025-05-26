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
        ('slow_sma_period', 30),
        ('stop_loss_perc', 0.05), # 5% stop-loss
    )

    def __init__(self):
        self.data0 = self.datas[0]
        self.fast_sma = bt.indicators.SimpleMovingAverage(self.data0.close, period=self.p.fast_sma_period) # [Source: 25, 28-42]
        self.slow_sma = bt.indicators.SimpleMovingAverage(self.data0.close, period=self.p.slow_sma_period) # [Source: 25, 28-42]
        self.sma_crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma) # [Source: 27, 39, 43-45]
        self.order = None
        self.buyprice = None
        self.stop_loss_order = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0) # [Source: 53, 74-76 for printout concept]
        print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order): # [Source: 94 (implied for order notification), 57-60 for stop-loss]
        if order.status in [order.Submitted, order.Accepted]:
            self.log(f'ORDER {order.ordtype_str()} {order.getstatusname()}: Ref: {order.ref}, Size: {order.size}, Price: {order.price:.2f}')
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, Size: {order.executed.size}')
                self.buyprice = order.executed.price
                stop_price = self.buyprice * (1.0 - self.p.stop_loss_perc)
                self.stop_loss_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=order.executed.size)
                self.log(f'STOP-LOSS SELL ORDER PLACED: Price: {stop_price:.2f}, Ref: {self.stop_loss_order.ref}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, Size: {order.executed.size}')
                if self.buyprice:
                     self.log(f'PROFIT/LOSS for this trade: {(order.executed.price - self.buyprice) * order.executed.size - order.executed.comm:.2f}')
                self.buyprice = None
                if self.stop_loss_order and self.stop_loss_order.ref == order.ref:
                    self.stop_loss_order = None
                    self.log('STOP-LOSS ORDER EXECUTED')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ORDER {order.getstatusname()}: Ref: {order.ref}')
            if self.stop_loss_order and self.stop_loss_order.ref == order.ref:
                self.stop_loss_order = None
                self.log('STOP-LOSS ORDER CANCELED/MARGIN/REJECTED')
        self.order = None

    def notify_trade(self, trade): # [Source: 94 (implied for trade notification)]
        if trade.isclosed:
            self.log(f'TRADE PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}, Commission: {trade.commission:.2f}')

    def next(self):
        if self.order: return # Check for pending orders

        if not self.position: # Not in the market
            if self.sma_crossover[0] > 0: # Fast > Slow SMA
                self.log(f'BUY CREATE, Close: {self.data0.close[0]:.2f}, FastSMA: {self.fast_sma[0]:.2f}, SlowSMA: {self.slow_sma[0]:.2f}')
                self.order = self.buy()
        else: # Already in the market
            if self.sma_crossover[0] < 0: # Fast < Slow SMA
                self.log(f'SELL CREATE (Profit Taking/Trend Reversal), Close: {self.data0.close[0]:.2f}, FastSMA: {self.fast_sma[0]:.2f}, SlowSMA: {self.slow_sma[0]:.2f}')
                self.order = self.sell()
            # Stop-loss is handled by its own order type in notify_order.

# Conceptual Comments for Strategy Section:
# - Other Indicators: MACD (`bt.indicators.MACD`), PSAR (`bt.indicators.ParabolicSAR`), RSI (`bt.indicators.RSI`). [Source: MACD/PSAR 46-50, RSI 35, 36, 51-53]
# - Parameter Passing: Override in `cerebro.addstrategy(SMACrossoverStrategy, fast_sma_period=15)`. [Source: Backtrader docs on cerebro.addstrategy]
# - Order Execution: `self.close()`, other types like `bt.Order.Limit`, `bt.Order.StopTrail`. [Source: e.g., exectype param in 97, Backtrader docs on Order Types]

# --- III. Cerebro Setup & Backtest Execution Section ---
def run_backtest():
    cerebro = bt.Cerebro() # [Source: 64, 69, 82]

    data_feed = GenericCSV_IMFData( # [Source: 64, 69, 82 for adding data]
        dataname='sample_imf_data.csv',
        fromdate=datetime.datetime(2020, 1, 1),
        todate=datetime.datetime(2020, 1, 24) # Adjusted to sample data range
    )
    cerebro.adddata(data_feed)
    cerebro.addstrategy(SMACrossoverStrategy, fast_sma_period=5, slow_sma_period=15) # [Source: 64, 69, 82 for adding strategy]

    cerebro.broker.setcash(100000.0) # [Source: cash in 64, 69, 82]
    cerebro.broker.setcommission(commission=0.001) # [Source: commperc 65, 82, or comm 134]
    cerebro.addsizer(bt.sizers.FixedSize, stake=10) # [Source: stake in 63, 65, 87, 100, 104]

    # Add Analyzers [Source: General Analyzer section 112-120, Sharpe 113, 116, SQN 113, 119, TradeAnalyzer 113, 118]
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio', timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())
    results = cerebro.run() # [Source: 64, 70, 83]
    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # Print Analyzer Results
    if results and len(results) > 0:
        strat = results[0]
        sharpe_analysis = strat.analyzers.sharpe_ratio.get_analysis()
        sqn_analysis = strat.analyzers.sqn.get_analysis()
        trade_analysis = strat.analyzers.trade_analyzer.get_analysis()

        print(f"\nSharpe Ratio: {sharpe_analysis.get('sharperatio', 'N/A')}")
        print(f"SQN: {sqn_analysis.get('sqn', 'N/A')}")
        if trade_analysis:
            print(f"Total Trades: {trade_analysis.total.get('total', 0)}, Winning: {trade_analysis.won.get('total', 0)}, Losing: {trade_analysis.lost.get('total', 0)}")
            pnl_net_total = trade_analysis.pnl.net.total if hasattr(trade_analysis.pnl, 'net') else 0.0
            print(f"Net PnL: {pnl_net_total:.2f}")
        else: print("No trades to analyze.")
    else: print("No strategy results to analyze.")

    # Plotting [Source: 65-67, style/volume options 28, 33-37, 66-73]
    try:
        # cerebro.plot(style='candlestick', volume=True) # Uncomment to plot
        print("\nPlotting disabled. Uncomment 'cerebro.plot(...)' in script to enable.")
    except Exception as e:
        print(f"\nError during plotting: {e}. Plotting may require a GUI or specific backend.")

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
