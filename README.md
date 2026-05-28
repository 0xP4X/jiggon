# Jiggon CLI Trading Bot 📈

Welcome to **Jiggon**, an open-source, fully interactive Command Line Interface (CLI) quantitative trading bot. Jiggon is designed for both novices looking to start algorithmic trading and experts who want a highly strict, risk-first approach to trading on Deriv.

Unlike many open-source bots that use "mock" features or paper-trading simulations, Jiggon is **ready for real live trading out of the box** using the Deriv WebSocket API.

---

## 🚀 Features

*   **Real Financial Execution:** Connects directly to the Deriv API to execute Binary Option (Rise/Fall) contracts in real-time.
*   **Premium Terminal User Interface (TUI):** A beautiful, high-contrast dark theme (Catppuccin Macchiato) UI directly in your terminal.
*   **AI & Logic Gates:** Trades are only executed if they pass:
    *   Technical Analysis constraints (EMA, RSI, ATR).
    *   Risk Management gates (Max Drawdown, Consecutive Losses, Safe Mode).
    *   AI Probability engine.
*   **Dual Environments:** Seamlessly switch between **Demo** (Paper Trading with a Demo token) and **Live** (Real Funds) from the startup wizard.

## 🛠️ Quick Start Guide for Novices

### 1. Prerequisites

You need Python installed on your computer.
*   [Download Python (Windows/Mac/Linux)](https://www.python.org/downloads/)

### 2. Get a Deriv API Token

To trade (even in Demo mode), Jiggon needs an API token to connect to your Deriv account.
1.  Go to [Deriv.com](https://deriv.com/) and create a free account.
2.  Switch to your **Demo Account**.
3.  Go to **Settings > API Token**.
4.  Create a new token with **Read** and **Trade** permissions. Name it `JiggonDemo`.
5.  Copy the generated token.

### 3. Installation

Open your terminal or command prompt and run these commands:

```powershell
# 1. Navigate to the project directory (or clone it first)
cd C:\Users\0day\Desktop\jiggon

# 2. Create a virtual environment to keep things clean
python -m venv .venv

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install required libraries
python -m pip install -r requirements.txt
```

### 4. Running the Bot

Jiggon is a Terminal UI app. To launch the interactive interface:

```powershell
python -m app.main
```

### 5. Using the Onboarding Wizard

When the bot launches, you will see a popup wizard.
1.  **Environment**: Select "Demo" to trade with virtual money.
2.  **API Token**: Paste the Deriv token you created in step 2.
3.  **Strategy**: Select "Master PDF Algorithm".
4.  Click **Launch Terminal**.

## 📊 Navigating the Terminal

Once launched, the terminal is divided into several panels:

*   **Price Chart (Center):** Displays real-time live candlestick data for the selected asset (R_100 index by default).
*   **System Log (Bottom):** Watch the bot's "brain" in real-time. It will explain why trades are taken or vetoed.
*   **Confidence Table (Top Left):** Shows the real-time checklist. A trade needs all green checkmarks to fire.
*   **Risk Engine (Top Middle):** Displays your current Drawdown limit, active signal direction, and the AI's risk evaluation.
*   **Portfolio (Top Right):** Your live account balance, win rate, and session profit/loss.

### Keyboard Shortcuts

*   Press `s` to instantly toggle **Safe Mode**. When Safe Mode is ON, the bot will analyze the market but block all real money trades.
*   Press `w` to reopen the startup Wizard.
*   Press `q` or `Ctrl+C` to quit the bot safely.

## 🛡️ Risk Management (Safety First)

Jiggon is built to protect your capital. It enforces strict risk limits:

*   **Max Daily Drawdown:** If your account drops by a certain percentage (default 5%), the bot goes into permanent lockdown for the session.
*   **Abnormal Volatility Filter:** If the ATR (Average True Range) exceeds the normal threshold, the market is considered too chaotic and trades are blocked.
*   **AI Veto:** The internal RuleBasedPredictor evaluates the momentum and MTF (Multi-Timeframe) alignment. If probability drops below 75%, it vetoes the trade.

## 🤝 Contributing

This is an open-source project. If you are an algorithmic trader, data scientist, or Python developer, pull requests are welcome! 
Focus areas:
*   Adding new Strategy Parsers in `app.strategy`.
*   Expanding the AI Predictor (`app.ai.predictor`) to use Machine Learning (XGBoost/Scikit-Learn).
*   Adding support for Forex CFDs instead of just Binary Options.

---

## ⚖️ Legal Disclaimer & Liability (READ BEFORE USE)

**Jiggon is provided strictly for educational and informational purposes only.**

By downloading, installing, or using this software, you explicitly agree to the following:
1. **No Financial Advice:** Nothing in this repository constitutes financial, investment, or trading advice. The algorithms and risk models provided are experimental.
2. **Assumption of Risk:** Trading in financial markets, especially algorithmic trading of derivatives or binary options, carries a high level of risk and may not be suitable for all investors. You could lose some or all of your initial investment. 
3. **No Warranty:** This software is provided "AS IS", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.
4. **Limitation of Liability:** In no event shall the authors, contributors, or copyright holders be liable for any claim, damages, financial loss, or other liability, whether in an action of contract, tort or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

**You are solely responsible for your own trading decisions and any financial losses that may result from using this bot.** We strongly recommend using the built-in **Demo Mode** extensively before ever considering connecting a Live API token.

---
## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
