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

The script also uses built-in Python libraries like `os` (for operating system interactions like file path checking) and `glob` (for finding files using patterns), which are part of the standard Python installation and do not require separate installs.

---

## Section 2: Understanding the Code (`backtrader_app.py`)

This section breaks down the structure and key components of the `backtrader_app.py` script.

### 2.1. High-Level Script Structure

The `backtrader_app.py` script is organized into several main parts:

1.  **Imports:** Necessary libraries like `backtrader`, `datetime`, `matplotlib`, `os`, and `glob`.
2.  **`GenericCSV_IMFData` Class:** A custom class for loading data from CSV files in a specific format.
3.  **`SMACrossoverStrategy` Class:** The core trading strategy logic.
4.  **`run_backtest()` Function:** Sets up and runs the Backtrader engine (Cerebro), including data loading, strategy configuration, broker settings, analyzers, and plotting.
5.  **Main Execution Block (`if __name__ == '__main__':`)**: Calls `run_backtest()` when the script is executed.
6.  **Conceptual Comments:** Sections at the end of the script provide insights into live trading, and comparisons with other frameworks like QuantConnect LEAN and Freqtrade.

### 2.2. Data Handling (`GenericCSV_IMFData` class & `run_backtest` data loading)

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
        dataname=dataname,  # Name of the CSV file (dynamically determined)
        fromdate=fromdate, # Start date for backtest
        todate=todate    # End date for backtest
    )
    ```
    The actual `dataname`, `fromdate`, and `todate` are determined by the dynamic CSV file search logic.

#### Dynamic CSV File Search Logic (in `run_backtest()`)

The script implements a dynamic way to find and use a CSV data file:

1.  **Preferred File:** It first checks if a `preferred_dataname` (set to `sample_imf_data.csv`) exists using `os.path.exists(preferred_dataname)`. If found, this file is used.
2.  **Alternative Search:** If the preferred file isn't found, the script uses `glob.glob('*.csv')` to find all files ending with `.csv` in the current directory.
3.  **Auto-Selection:**
    *   If multiple CSV files are found, it sorts them alphabetically and picks the first one. A message is printed indicating which file was selected and lists other available CSV files.
    *   If only one CSV file is found, it's used.
4.  **Error Handling:** If no CSV files are found in the directory (neither the preferred one nor any other), the script prints a critical error message and exits, as it cannot proceed without data.
5.  **Data Sufficiency & Date Range:**
    *   The script attempts to automatically set `fromdate` and `todate` based on the selected CSV file's content (by reading the first and last date entries).
    *   It's crucial that the selected CSV file has enough data points for the indicators used in the strategy (e.g., at least as many data points as the `slow_sma_period`). The script includes error handling for `IndexError` during `cerebro.run()`, which often indicates insufficient data for indicator calculation.

### 2.3. Strategy Definition (`SMACrossoverStrategy` class)

This class contains the logic for the trading strategy.

*   **Inheritance:** `class SMACrossoverStrategy(bt.Strategy):` indicates it's a Backtrader strategy.
*   **`params`:**
    ```python
    params = (
        ('fast_sma_period', 10),
        ('slow_sma_period', 30),
        ('stop_loss_perc', 0.05), # 5% stop-loss
        ('printlog', True),      # New parameter to enable/disable logging
    )
    ```
    The `printlog` parameter allows you to control whether the strategy's `log()` messages are printed to the console.
*   **`__init__(self)` (Constructor):**
    *   `self.data_close = self.datas[0].close`: A reference to the closing prices of the primary data feed.
    *   `self.data_datetime = self.datas[0].datetime`: A reference to the datetime line of the primary data feed.
    *   **Indicator Creation:** SMAs and Crossover are created as before, using `self.data_close`.
    *   **Order Tracking:** `self.order`, `self.buyprice`, `self.buycomm`, and `self.stop_loss_order` are initialized. `buycomm` is added to track commission for the buy trade.
*   **`log(self, txt, dt=None, doprint=False)`:**
    *   The `doprint` parameter, if `True`, forces the message to print regardless of `self.p.printlog`.
    *   The actual printing is controlled by: `if self.p.printlog or doprint:`. This allows selective logging.
*   **`notify_order(self, order)`:** This method handles order status updates with refined logic:
    *   **Submitted/Accepted:** Logs the order type, status, reference, size, and price.
    *   **Completed Buy Order:**
        *   Logs execution details (price, cost, commission, size).
        *   Stores `self.buyprice = order.executed.price` and `self.buycomm = order.executed.comm`.
        *   Calculates `stop_price` based on `self.buyprice` and `self.p.stop_loss_perc`.
        *   Places a `SELL` order of type `bt.Order.Stop` at `stop_price`, using `parent=order` to link it to the buy order. `self.stop_loss_order` tracks this stop order.
        *   Logs the placement of the stop-loss order.
    *   **Completed Sell Order:**
        *   Logs execution details.
        *   If it was the `self.stop_loss_order` that executed, it logs "STOP-LOSS ORDER EXECUTED" and clears `self.stop_loss_order`.
        *   If it was a regular sell (profit-taking), it logs "PROFIT-TAKING SELL EXECUTED". If there was an active `self.stop_loss_order`, it cancels it using `self.cancel(self.stop_loss_order)` and logs the cancellation.
    *   **Other Statuses (`Canceled`, `Margin`, `Rejected`, `Expired`):**
        *   Logs the order status and reference.
        *   If the affected order was the `self.stop_loss_order`, it logs this fact and clears `self.stop_loss_order`.
    *   `self.order = None`: This line is executed if the order is not `Accepted` or `Submitted` (i.e., it has reached a final state like `Completed`, `Canceled`, etc.), ensuring the strategy can place new orders.
*   **`notify_trade(self, trade)`:**
    *   Called when a trade is opened or closed.
    *   If a trade is closed (`trade.isclosed`), it logs the gross P&L, net P&L (including commissions), and total commission for that trade.
    *   Resets `self.buyprice = None` and `self.buycomm = None` after a trade is closed, preparing for the next potential trade.
*   **`next(self)`:** This is the core strategy logic.
    *   A commented-out line `self.log(f'Close: {self.data_close[0]:.2f}, FastSMA: {self.fast_sma[0]:.2f}, SlowSMA: {self.slow_sma[0]:.2f}, Crossover: {self.sma_crossover[0]:.2f}')` provides an example of detailed logging for debugging.
    *   `if self.order: return`: If an order is pending, do nothing.
    *   `if not self.position:`: Checks if the strategy is holding a position.
        *   **Buy Condition:** `if self.sma_crossover[0] > 0:` (Fast SMA crosses above Slow SMA), logs the buy signal and places a market buy order: `self.order = self.buy()`.
    *   `else:` (If already in a position):
        *   **Sell Condition:** `if self.sma_crossover[0] < 0:` (Fast SMA crosses below Slow SMA), logs the sell signal (profit-taking/trend reversal) and places a market sell order: `self.order = self.sell()`.
        *   When this regular sell order is executed, the `notify_order` method will handle the cancellation of any active stop-loss order.

### 2.4. Backtesting Engine (`run_backtest()` function & Cerebro)

This function orchestrates the backtest.

*   `enable_plotting = True`: A variable at the start of the function to easily toggle plotting.
*   `cerebro = bt.Cerebro()`: Initializes Cerebro.
*   **Adding Strategy:**
    ```python
    cerebro.addstrategy(SMACrossoverStrategy, 
                        fast_sma_period=5, 
                        slow_sma_period=10, 
                        stop_loss_perc=0.03, 
                        printlog=True)
    ```
    The strategy is added with specific parameters: `fast_sma_period=5`, `slow_sma_period=10`, `stop_loss_perc=0.03`, and `printlog=True`.
*   **Sizer:**
    *   `cerebro.addsizer(bt.sizers.FixedSize, stake=100)`: The stake (number of shares) has been updated to 100.
*   **Analyzers:**
    *   `DrawDown`: Measures the largest peak-to-trough decline during the backtest.
    *   `AnnualReturn`: Calculates the return for each year in the backtest.
    *   (SharpeRatio, TradeAnalyzer, SQN are still included).
*   **Running the Backtest:**
    *   The `cerebro.run()` call is wrapped in a `try-except IndexError` block. This is important because if the data period is too short for the indicator periods (e.g., asking for a 30-period SMA with only 20 data points), Backtrader will raise an `IndexError`. The `except` block catches this, prints an informative error message about data sufficiency, and allows the script to exit gracefully.
    *   A general `except Exception` block is also included to catch other unexpected errors during the backtest execution.
*   **Printing Analyzer Results:**
    *   **DrawDown:** Prints `drawdown.max.drawdown` (percentage) and `drawdown.max.moneydown` (monetary value).
    *   **AnnualReturn:** Prints the dictionary of yearly returns (e.g., `{2020: 0.152}`).
    *   The script uses more robust checks like `trade_analysis.total.get('total', 0)` to avoid errors if certain analysis attributes don't exist (e.g., if no trades occurred).
*   **Plotting:**
    *   Plotting is now conditional on `enable_plotting` and whether any trades occurred.
    *   The plot is saved to `backtest_plot.png` using `savefig=True` and `figfilename='backtest_plot.png'`.
    *   `figscale=1.2` is used to potentially adjust the plot size/resolution.
    *   A `try-except` block handles potential errors during plotting, especially in headless environments, and advises the user accordingly.

---

## Section 4: Running Backtests and Interpreting Results

### 4.3. Interpreting Analyzer Results

*   **Sharpe Ratio:** (Explanation remains the same)
*   **SQN (System Quality Number):** (Explanation remains the same)
*   **DrawDown:**
    *   **Maximum Drawdown (%):** The largest percentage drop from a portfolio peak to a subsequent trough during the backtest. It indicates the potential downside risk.
    *   **Maximum Drawdown (Money):** The monetary value of the largest peak-to-trough decline.
*   **AnnualReturn:**
    *   Provides a dictionary where keys are years and values are the percentage returns for those respective years (e.g., `2020: 0.10` means a 10% return in 2020). This helps assess year-over-year performance consistency.
*   **TradeAnalyzer:** (Explanation remains largely the same, but reflects robust attribute access)

### 4.4. Viewing the Plot

The backtest plot is automatically saved as `backtest_plot.png` in your project directory if `enable_plotting` is `True` in the script and the backtest completes successfully with at least one trade. You can open this image file to view the results.

*   **What to Look For:** (Explanation remains the same: Candlesticks, Volume, SMA Lines, Buy/Sell Markers)

---

## Section 6: Next Steps and Advanced Topics

This bot serves as a foundational example. You can extend and enhance it in numerous ways:

*   **Explore Conceptual Comments:** Dive into the conceptual comments within `backtrader_app.py`. They offer insights into:
    *   **Parameter Optimization:** Using `cerebro.optstrategy()` for testing various parameter sets (e.g., SMA periods, stop-loss percentages).
    *   **Alternative Indicators:** Incorporating other technical indicators like RSI, MACD, Bollinger Bands.
    *   **Advanced Sizers:** Implementing different position sizing strategies beyond `FixedSize` (e.g., `PercentSizer`).
    *   **Additional Analyzers & Observers:** Utilizing tools like `DrawDown`, `AnnualReturn`, or `PyFolio` for deeper performance insights, and Observers like `Broker` or `Trades` for visual feedback.
    *   **Live Trading Adaptations:** Understanding the high-level considerations for transitioning to live trading, including broker integration, real-time data handling, and robust error management.
    *   **Cerebro Writers:** Learning how to use `cerebro.addwriter()` to save backtest results to files.
    *   **Alternative Backtrader Frameworks:** The conceptual comparisons to QuantConnect LEAN and Freqtrade provide context on different algorithmic trading system architectures.

*   **Consult `TUTORIAL.md`:** This document provides a detailed, step-by-step guide on using, understanding the internal workings of, and customizing the bot's components. It's an excellent resource for a deeper dive into the script's functionality.

*   **Official Backtrader Documentation:** For comprehensive information on its API, all features, and advanced usage, the official documentation is invaluable: [https://www.backtrader.com/docu/](https://www.backtrader.com/docu/)

*   **Expand Financial & Programming Knowledge:**
    *   Continuously learn about financial markets, diverse trading strategies, quantitative analysis techniques, and robust risk management practices.
    *   Strengthen your Python programming skills, as this will enable more complex strategy development and customization.

Happy Backtesting!
```
