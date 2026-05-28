# Jiggon Strategy Database 🧠

Welcome to the Jiggon Custom Strategy library! 

The files in this directory end in `.jiggon` and are written using the Jiggon Domain Specific Language (DSL). This allows you to construct robust trading parameters in plain English without needing to know how to write Python code.

## How to use these files:

When you launch the Jiggon Terminal (`python -m app.main`), select **"Custom Algorithm"** in the Onboarding Wizard.
You can then open any of the `.jiggon` files in this folder using a text editor (like Notepad), copy the text, and paste it directly into the Custom Algorithm text box in the Terminal Wizard.

## Available Variables:
You can build custom logic using the following real-time data inputs:
*   `RSI`: Relative Strength Index (0 to 100).
*   `MACD`: The MACD line value.
*   `ATR`: Average True Range (Volatility measurement).
*   `EMA_TREND`: Synthesized Moving Average Trend. Evaluates to `BULLISH`, `BEARISH`, or `MIXED`.

## Available Operators:
*   `AND`, `OR`
*   `>`, `<`, `==`, `>=`, `<=`

## Base Strategies Included:
1.  **`trend_rider.jiggon`**: Rides the predominant moving average trend and triggers on MACD zero-line crosses. Safe and steady.
2.  **`mean_reversion.jiggon`**: Fades extremes. Buys heavy dips (RSI < 25) and sells heavy peaks (RSI > 75).
3.  **`momentum_scalper.jiggon`**: Highly aggressive. Buys directly into volatility spikes without waiting for pullbacks.
4.  **`my_strategy.jiggon`**: A blank template for you to experiment with!
