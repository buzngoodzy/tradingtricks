# Backtrader Stock Trading Bot - Tutorial

## Introduction

Welcome to the Backtrader Stock Trading Bot tutorial! This guide will walk you through setting up, understanding, running, and customizing the Backtrader bot provided in the `backtrader_app.py` script. The bot is designed to demonstrate a Simple Moving Average (SMA) crossover strategy and introduce you to the core concepts of algorithmic trading with Backtrader.

---

## Section 1: Setup and Installation

This section covers the initial steps to get the bot running on your system.

### 1.1. Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.7+:** Backtrader and `matplotlib` are compatible with modern Python versions.
*   **pip:** The Python package installer, usually included with Python installations.

### 1.2. Download the Code

*   **Clone the Repository:** If you have Git installed, you can clone the repository:
    ```bash
    git clone <repository_url>
    ```
    (Replace `<repository_url>` with the actual URL of the repository).
*   **Download Files:** Alternatively, download the project files (`backtrader_app.py`, `sample_imf_data.csv`, `README.md`) directly.

### 1.3. Setting up a Virtual Environment (Recommended)

Using a virtual environment is highly recommended to isolate project dependencies and avoid conflicts with other Python projects or your global Python installation.

*   **Why use a virtual environment?**
    *   It creates an isolated environment for your project, so packages installed for this bot won't affect other projects.
    *   It helps manage different versions of packages for different projects.

*   **Commands:**
    1.  Navigate to your project directory in the terminal.
    2.  Create the virtual environment (commonly named `venv`):
        ```bash
        python -m venv venv
        ```
        (For Linux/macOS, you might need to use `python3` explicitly: `python3 -m venv venv`)
    3.  Activate the virtual environment:
        *   **On Linux/macOS:**
            ```bash
            source venv/bin/activate
            ```
        *   **On Windows (Command Prompt/PowerShell):**
            ```bash
            venv\Scripts\activate
            ```
        Your terminal prompt should now indicate that the virtual environment is active (e.g., `(venv) Your-Computer:...`).

### 1.4. Installing Libraries

With your virtual environment active (if you created one), install the necessary Python libraries:

```bash
pip install backtrader matplotlib
```

This command installs:
*   `backtrader`: The core algorithmic trading framework.
*   `matplotlib`: Used by Backtrader for plotting charts.

### 1.5. Verifying the Setup (Optional)

To quickly check if Backtrader is installed correctly, you can run the following command in your terminal (with the virtual environment active):

```bash
python -c "import backtrader; print(backtrader.__version__)"
```

This should print the installed version of Backtrader, e.g., `1.9.76.123`.

---

## Section 2: Understanding the Code (`backtrader_app.py`)

This section breaks down the structure and key components of the `backtrader_app.py` script.

### 2.1. High-Level Script Structure

The `backtrader_app.py` script is organized into several main parts:

1.  **Imports:** Necessary libraries like `backtrader`, `datetime`, and `matplotlib`.
2.  **`GenericCSV_IMFData` Class:** A custom class for loading data from CSV files in a specific format.
3.  **`SMACrossoverStrategy` Class:** The core trading strategy logic.
4.  **`run_backtest()` Function:** Sets up and runs the Backtrader engine (Cerebro), including data loading, strategy configuration, broker settings, analyzers, and plotting.
5.  **Main Execution Block (`if __name__ == '__main__':`)**: Calls `run_backtest()` when the script is executed.
6.  **Conceptual Comments:** Sections at the end of the script provide insights into live trading, and comparisons with other frameworks like QuantConnect LEAN and Freqtrade.

### 2.2. Data Handling (`GenericCSV_IMFData` class)

*   **Purpose:** This class inherits from `bt.feeds.GenericCSVData` and is tailored to load OHLCV (Open, High, Low, Close, Volume) stock data from CSV files.
*   **Key `params`:** These parameters within the class tell Backtrader how to map the columns in your CSV file to the data fields it expects:
    *   `('dtformat', ('%Y-%m-%d'))`: Specifies the date format in the CSV (e.g., "2020-01-01").
    *   `('datetime', 0)`: The index of the column containing the date/datetime (0 means the first column).
    *   `('open', 1)`: Index of the 'Open' price column.
    *   `('high', 2)`: Index of the 'High' price column.
    *   `('low', 3)`: Index of the 'Low' price column.
    *   `('close', 4)`: Index of the 'Close' price column.
    *   `('volume', 5)`: Index of the 'Volume' column.
    *   `('openinterest', 6)`: Index of the 'Open Interest' column. If not present in your CSV, it can be set to `-1` or your CSV should have a placeholder column (e.g., filled with zeros).
*   **Instantiation in `run_backtest()`:**
    ```python
    data_feed = GenericCSV_IMFData(
        dataname='sample_imf_data.csv',  # Name of the CSV file
        fromdate=datetime.datetime(2020, 1, 1), # Start date for backtest
        todate=datetime.datetime(2020, 1, 24)    # End date for backtest
    )
    ```
    The `sample_imf_data.csv` file is used by default, with a specific date range.

### 2.3. Strategy Definition (`SMACrossoverStrategy` class)

This class contains the logic for the trading strategy.

*   **Inheritance:** `class SMACrossoverStrategy(bt.Strategy):` indicates it's a Backtrader strategy.
*   **`params`:**
    ```python
    params = (
        ('fast_sma_period', 10),  # Period for the fast SMA
        ('slow_sma_period', 30),  # Period for the slow SMA
        ('stop_loss_perc', 0.05), # Percentage for stop-loss (0.05 = 5%)
    )
    ```
    These define configurable parameters for the strategy. You can change their default values here or when adding the strategy to Cerebro.
*   **`__init__(self)` (Constructor):**
    *   `self.data0 = self.datas[0]`: A reference to the primary data feed.
    *   **Indicator Creation:**
        *   `self.fast_sma = bt.indicators.SimpleMovingAverage(self.data0.close, period=self.p.fast_sma_period)`: Creates a fast SMA based on the closing prices of the data feed, using the `fast_sma_period` parameter.
        *   `self.slow_sma = bt.indicators.SimpleMovingAverage(self.data0.close, period=self.p.slow_sma_period)`: Creates a slow SMA.
        *   `self.sma_crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)`: This indicator signals when the fast SMA crosses above (`> 0`) or below (`< 0`) the slow SMA.
    *   **Order Tracking:**
        *   `self.order = None`: Stores the currently pending order.
        *   `self.buyprice = None`: Stores the execution price of the last buy order (used for P/L calculation in logs and for stop-loss calculation).
        *   `self.stop_loss_order = None`: Specifically tracks the stop-loss order associated with an open position.
*   **`log(self, txt, dt=None)`:** A utility method to print log messages with the current simulation date/time.
*   **`notify_order(self, order)`:** This method is called by Backtrader whenever there's an update to an order's status.
    *   It tracks the lifecycle: `Submitted`, `Accepted`, `Completed`, `Canceled`, `Margin`, `Rejected`.
    *   **Stop-Loss Logic:**
        1.  When a `BUY` order is `Completed`:
            *   The buy price (`self.buyprice`) is recorded.
            *   A stop-loss price is calculated (e.g., 5% below `self.buyprice` using `self.p.stop_loss_perc`).
            *   A `SELL` order of type `bt.Order.Stop` is placed at this stop_price. This order `self.stop_loss_order` remains pending until the price drops to that level or the position is closed by another signal.
        2.  If the `SELL` order that gets `Completed` was the `self.stop_loss_order`, it's logged as such.
*   **`notify_trade(self, trade)`:** Called when a trade is opened or closed. The script uses it to log the profit or loss when a trade is closed.
*   **`next(self)`:** This is the heart of the strategy, called on each new bar of data (e.g., each day).
    *   `if self.order: return`: If an order is already pending, do nothing.
    *   `if not self.position:`: Checks if the strategy is currently holding a position.
        *   **Buy Condition:** `if self.sma_crossover[0] > 0:`: If not in a position and the fast SMA has crossed above the slow SMA (crossover indicator is positive), a buy order is created: `self.order = self.buy()`.
    *   `else:` (If already in a position):
        *   **Sell Condition:** `if self.sma_crossover[0] < 0:`: If in a position and the fast SMA has crossed below the slow SMA (crossover indicator is negative), a sell order is created to close the position: `self.order = self.sell()`.
        *   The stop-loss order (if active) will automatically trigger a sell if its price condition is met, independently of this crossover logic.

### 2.4. Backtesting Engine (`run_backtest()` function & Cerebro)

This function orchestrates the backtest.

*   `cerebro = bt.Cerebro()`: `Cerebro` is the central engine or "brain" in Backtrader.
*   `cerebro.adddata(data_feed)`: Adds the prepared data feed to Cerebro.
*   `cerebro.addstrategy(SMACrossoverStrategy, fast_sma_period=5, slow_sma_period=15)`: Adds the strategy to Cerebro. Notice how parameters like `fast_sma_period` can be overridden here from their defaults in the strategy class.
*   **Broker Settings:**
    *   `cerebro.broker.setcash(100000.0)`: Sets the initial portfolio cash.
    *   `cerebro.broker.setcommission(commission=0.001)`: Sets a commission rate (e.g., 0.1% per trade).
*   **Sizer:**
    *   `cerebro.addsizer(bt.sizers.FixedSize, stake=10)`: Determines how many shares/units to trade. `FixedSize` means it will trade a fixed number of `stake` (e.g., 10 shares) per trade.
*   **Analyzers:** These tools evaluate the strategy's performance.
    *   `cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio', ...)`: Calculates the Sharpe Ratio, a measure of risk-adjusted return.
    *   `cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')`: Provides detailed statistics about individual trades (total trades, wins, losses, profit/loss per trade, etc.).
    *   `cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')`: Calculates the System Quality Number, which assesses the "quality" of the trading system.
    *   **Accessing Results:** After running Cerebro, analyzer results are accessed like this: `results[0].analyzers.analyzer_name.get_analysis()`.
*   `results = cerebro.run()`: Starts the backtesting process. `results` will contain a list of strategy instances, each holding its analyzer data.
*   `cerebro.plot(style='candlestick', volume=True)`: Generates a plot showing:
    *   Candlestick price bars.
    *   Volume bars.
    *   SMA indicator lines.
    *   Buy (up arrow) and Sell (down arrow) markers on the chart.
    *   (Note: This line is commented out by default in `backtrader_app.py` to allow running in headless environments. You can uncomment it to see the plot.)

---

## Section 3: Customizing the Strategy

You can modify the strategy to test different ideas.

### 3.1. Adjusting Parameters

*   **In `SMACrossoverStrategy.params`:** Change the default values directly in the strategy class:
    ```python
    class SMACrossoverStrategy(bt.Strategy):
        params = (
            ('fast_sma_period', 15),  # Changed from 10
            ('slow_sma_period', 40),  # Changed from 30
            ('stop_loss_perc', 0.03), # Changed from 0.05
        )
        # ... rest of the class
    ```
*   **When Adding Strategy to Cerebro:** Override parameters dynamically in `run_backtest()`:
    ```python
    cerebro.addstrategy(SMACrossoverStrategy, 
                        fast_sma_period=15, 
                        slow_sma_period=40, 
                        stop_loss_perc=0.03)
    ```
    This is often preferred for quick experiments or parameter optimization.

### 3.2. Using Different Indicators

Refer to the conceptual comments in `backtrader_app.py` for ideas (e.g., RSI, MACD).
General steps:

1.  **Instantiate in `__init__`:**
    ```python
    # Example: Adding RSI
    self.rsi = bt.indicators.RelativeStrengthIndex(period=14) 
    ```
2.  **Use in `next()`:**
    ```python
    # Hypothetical example: Buy if RSI < 30 and SMA crossover
    if not self.position:
        if self.sma_crossover[0] > 0 and self.rsi[0] < 30:
            self.log(f'BUY CREATE (SMA Crossover & RSI Oversold), Close: {self.data0.close[0]:.2f}, RSI: {self.rsi[0]:.2f}')
            self.order = self.buy()
    ```

### 3.3. Modifying Trading Logic in `next()`

*   **Changing Conditions:** You can alter the conditions for `self.sma_crossover`. For instance, if you were implementing a strategy that could also short-sell, you might use `self.sma_crossover[0] < 0` as a short signal (though the current bot is long-only).
*   **Adding Complexity:** Combine signals from multiple indicators, or add conditions based on price levels, volume, or other market data.
    ```python
    # Example: Require SMA crossover AND close price above slow SMA
    if not self.position:
        if self.sma_crossover[0] > 0 and self.data0.close[0] > self.slow_sma[0]:
            self.log(f'BUY CREATE (SMA Crossover & Close > SlowSMA), Close: {self.data0.close[0]:.2f}')
            self.order = self.buy()
    ```

---

## Section 4: Running Backtests and Interpreting Results

### 4.1. How to Run

Ensure your terminal is in the project directory and your virtual environment (if used) is active. Then run:

```bash
python backtrader_app.py
```

### 4.2. Understanding Console Output

The script will print logs, including:

*   **Strategy Logs:** Messages from the `self.log()` method in the strategy, showing buy/sell signal creations, prices, indicator values, etc.
    *   Example: `2020-01-06 BUY CREATE, Close: 105.00, FastSMA: 103.90, SlowSMA: 102.70`
*   **Order Notifications:** Updates on order status from `notify_order()`.
    *   Example: `2020-01-07 BUY EXECUTED, Price: 105.20, Cost: 1052.00, Comm: 1.05, Size: 10.0`
    *   Example: `2020-01-07 STOP-LOSS SELL ORDER PLACED: Price: 99.94, Ref: 3`
*   **Trade Notifications:** Profit/loss details from `notify_trade()` when a position is closed.
    *   Example: `2020-01-09 TRADE PROFIT, GROSS -2.00, NET -4.10, Commission: 2.10` (This shows a small loss)
*   **Portfolio Values:** Starting and final portfolio values.
*   **Analyzer Results:** Summarized performance metrics.

### 4.3. Interpreting Analyzer Results

*   **Sharpe Ratio:**
    *   Measures risk-adjusted return. A higher Sharpe Ratio is generally better, indicating better returns for the amount of risk taken. Ratios above 1 are often considered acceptable, above 2 good, but this varies by asset class and timeframe.
*   **SQN (System Quality Number):**
    *   A measure of the quality and robustness of a trading system.
    *   Heuristic interpretation:
        *   1.6 - 1.9: Below average, but tradable.
        *   2.0 - 2.4: Average.
        *   2.5 - 2.9: Good.
        *   3.0 - 5.0: Excellent.
        *   > 5.0: Superb.
*   **TradeAnalyzer:**
    *   `Total Trades`: Total number of closed trades.
    *   `Winning Trades`: Number of trades that resulted in a profit.
    *   `Losing Trades`: Number of trades that resulted in a loss.
    *   `Net PnL`: Total profit or loss after commissions.
    *   `Gross PnL`: Total profit or loss before commissions.
    *   `Longest Winning Streak / Longest Losing Streak`: Consecutive winning/losing trades.
    *   `Average Winning Trade / Average Losing Trade`: Average PnL for winning/losing trades.

### 4.4. Viewing the Plot

*   **Enabling the Plot:** If the plot doesn't appear, find this line in `run_backtest()`:
    ```python
    # cerebro.plot(style='candlestick', volume=True)
    ```
    And uncomment it:
    ```python
    cerebro.plot(style='candlestick', volume=True)
    ```
    You might also need to ensure your Python environment can display GUI windows (this can sometimes be an issue in very minimal or server environments).
*   **What to Look For:**
    *   **Candlesticks:** Represent price action (open, high, low, close) for each period.
    *   **Volume Bars:** Show trading volume for each period.
    *   **SMA Lines:** The fast and slow moving average lines plotted over the price.
    *   **Buy/Sell Markers:** Typically, upward-pointing green/blue triangles indicate buy orders, and downward-pointing red triangles indicate sell orders.

---

## Section 5: Using Your Own Data

You can test the strategy on your own historical stock data.

### 5.1. CSV File Format Requirements

Your CSV file should ideally follow this structure:

*   **Header Row:** `Date,Open,High,Low,Close,Volume,OpenInterest`
    *   `OpenInterest` can be a column of zeros if your data doesn't include it or it's not relevant to your strategy.
*   **Date Format:** `YYYY-MM-DD` (e.g., `2021-10-25`). This must match the `dtformat` in `GenericCSV_IMFData`.
*   **Data Cleanliness:** Ensure there are no missing values in the `Date`, `Open`, `High`, `Low`, `Close`, and `Volume` columns for the basic operation of this strategy.

### 5.2. Modifying the Script

In the `run_backtest()` function of `backtrader_app.py`:

1.  **Change `dataname`:**
    Update the `dataname` parameter in the `GenericCSV_IMFData` instantiation to point to your CSV file:
    ```python
    data_feed = GenericCSV_IMFData(
        dataname='path/to/your/custom_data.csv',  # Update this
        # ... other parameters
    )
    ```
2.  **Adjust `fromdate` and `todate`:**
    Modify these `datetime.datetime` objects to match the date range available in your data file for the desired backtesting period.
    ```python
    fromdate=datetime.datetime(YYYY, M, D), # Your start year, month, day
    todate=datetime.datetime(YYYY, M, D)    # Your end year, month, day
    ```

### 5.3. Data Considerations

*   **Sufficient Data:** Ensure you have enough historical data for a meaningful backtest. For daily data, several years might be appropriate depending on the strategy.
*   **Data Quality:** The quality of your data (accuracy, absence of errors or gaps) is crucial for reliable backtest results.

---

## Section 6: Next Steps and Advanced Topics

This bot provides a starting point. Here are ways to continue your learning:

### 6.1. Parameter Optimization

*   **Concept:** Testing a strategy with a range of different parameter values (e.g., various SMA periods) to find combinations that yield better historical performance.
*   **Backtrader Feature:** `cerebro.optstrategy()`. Refer to the conceptual comments in `backtrader_app.py` for a brief introduction. This involves defining ranges for parameters and letting Backtrader run multiple backtests.

### 6.2. Exploring Other Backtrader Features

Backtrader is rich in features. Explore:

*   **Sizers:** More advanced ways to determine trade size (e.g., `PercentSizer` to risk a percentage of portfolio equity).
*   **Observers:** Tools to monitor various aspects during a backtest (e.g., `Broker`, `Trades`, `Value`).
*   **Writers:** To save backtest results (e.g., trade lists) to files.
*   (Refer to the conceptual comments in `backtrader_app.py` for hints and the official documentation.)

### 6.3. Live Trading

*   Transitioning to live trading is a significant step that involves:
    *   Connecting to a brokerage API.
    *   Robust error handling.
    *   Careful risk management.
    *   Ensuring data feeds are live.
*   The conceptual comments on "Live Trading Extension" in `backtrader_app.py` provide a high-level overview of what's involved. **This bot is NOT ready for live trading out-of-the-box.**

### 6.4. Expanding Knowledge

*   **Official Backtrader Documentation:** The most comprehensive resource: [https://www.backtrader.com/docu/](https://www.backtrader.com/docu/)
*   **Other Trading Frameworks:** The comparative notes on QuantConnect LEAN and Freqtrade in `backtrader_app.py` can guide you to explore different platforms.
*   **Financial Markets & Strategy Development:** Continuously learn about financial markets, different types of trading strategies, risk management, and quantitative analysis.

Happy Backtesting!
```
