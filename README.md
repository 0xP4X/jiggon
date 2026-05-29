# Jiggon Quantitative Trading Terminal

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Features & Capabilities](#features--capabilities)
4. [Installation & Setup](#installation--setup)
5. [Operational Guide](#operational-guide)
6. [Risk Management Framework](#risk-management-framework)
7. [Strategy Customization](#strategy-customization)
8. [Legal Disclaimer & Liability](#legal-disclaimer--liability)

---

## Overview

**Jiggon** is an open-source, fully interactive Command Line Interface (CLI) quantitative trading bot. It is engineered to facilitate rigorous algorithmic trading on the [Deriv API](https://api.deriv.com/), executing Binary Options contracts with institutional-grade risk management protocols.

The software is constructed to eliminate emotional trading variables by strictly adhering to quantitative thresholds, multi-timeframe analysis, and automated risk enforcement mechanisms.

## System Architecture

The application is structured around a modular execution pipeline. Key components include:

*   **[DerivWebSocket](src/jiggon/data/deriv_ws.py):** Establishes an asynchronous, persistent WebSocket connection to the Deriv API for real-time tick data ingestion.
*   **[BrokerClient](src/jiggon/broker/client.py):** Manages account authentication, balance verification, and live contract execution routing.
*   **[MarketSnapshot](src/jiggon/analysis/market.py):** Processes raw tick data into synthetically constructed OHLC (Open, High, Low, Close) candles to calculate critical technical indicators (EMA, RSI, ATR, MACD).
*   **[ExecutionEngine](src/jiggon/execution/engine.py):** The central decision matrix that cross-references technical signals with the `RiskState` to authorize or veto pending executions.

## Features & Capabilities

*   **Real-Time Execution:** Low-latency order routing directly to the Deriv WebSocket API for Rise/Fall contracts.
*   **Terminal User Interface (TUI):** A robust interface built on the [Textual](https://textual.textualize.io/) framework, featuring real-time log ingestion, confidence checklists, and [Plotext](https://github.com/piccolomo/plotext) candlestick rendering.
*   **Persistent Configuration:** Runtime parameters are automatically serialized to a local `jiggon_config.json` file to preserve state across application restarts.
*   **Automated Trade Auditing:** All executed transactions, irrespective of outcome, are systematically logged to an external `trade_history.csv` file.

## Installation & Setup

### System Requirements
*   Python 3.10 or higher.
*   A validated Deriv account and associated API Token with `Read` and `Trade` permissions.

### Global Installation (Recommended)

Jiggon is officially distributed via the Python Package Index (PyPI). Ensure you have Python 3.10+ installed.

```powershell
pip install jiggon
```

### Developer Setup (Building from Source)

If you wish to contribute to the open-source repository or modify the source code:

```powershell
git clone https://github.com/0xP4X/jiggon.git
cd jiggon
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Operational Guide

If installed globally via PyPI, simply execute the following command anywhere in your terminal:

```powershell
jiggon
```

Upon initialization, the Onboarding Configuration Wizard will request the following parameters:

*   **Environment:** Select `Demo` for testing algorithms without financial risk, or `Live` for real-capital deployment.
*   **API Token:** Input your secure Deriv token.
*   **Volatility Index**: The specific synthetic market to trade (e.g. `Vol 10`, `Vol 100 (1s)`).
*   **Timeframe**: The granularity of the candlestick chart (from 1 Minute up to 1 Day).
*   **Duration (Ticks)**: The length of the contract (Deriv limits this strictly to 5-10 ticks).
*   **Strategy Aggression:** Modifies the sensitivity of the internal momentum oscillators (RSI). Options include Conservative, Balanced, or Aggressive.
*   **Chart Theme:** Customizes the visual aesthetic of the internal candlestick chart rendering.

### Keyboard Operations
*   `s` : Instantly toggle the Safe Mode kill-switch.
*   `w` : Reinitialize the Onboarding Configuration Wizard.
*   `?` : Open the built-in Help Menu for instructions and configuration details.
*   `+` : Zoom the chart scale in.
*   `-` : Zoom the chart scale out.
*   `q` : Terminate the application thread safely.

## Risk Management Framework

Jiggon is inherently designed to protect principal capital through multiple systemic gates:

1.  **Maximum Daily Drawdown:** The application tracks realized session losses against the total portfolio balance. If the threshold (e.g., 5.0%) is breached, the bot permanently halts execution for the remainder of the session.
2.  **Take-Profit Halting:** Users may define a strict nominal profit target. Upon reaching this target, the system engages Safe Mode to preserve realized gains.
3.  **Abnormal Volatility Rejection:** The [Average True Range (ATR)](src/jiggon/analysis/indicators.py) is monitored constantly. If the current ATR surpasses the configured safe threshold, trading is temporarily suspended due to erratic market conditions.

## Strategy Customization

The bot supports algorithmic customization via a Domain Specific Language (DSL). Users can input custom pseudo-code in the application wizard to override the default strategy.

**Example Custom Algorithm:**
```text
IF RSI < 45 AND EMA_TREND == BULLISH THEN BUY
IF RSI > 55 AND EMA_TREND == BEARISH THEN SELL
```

The underlying parser will translate these constraints and route them through the `calculate_confidence` matrix in [confidence.py](src/jiggon/strategy/confidence.py).

---

## Legal Disclaimer & Liability (READ BEFORE USE)

**Jiggon is provided strictly for educational and informational purposes only.**

By downloading, installing, compiling, or operating this software, you explicitly agree to the following conditions:

1. **No Financial Advice:** Nothing in this repository constitutes financial, investment, or trading advice. The algorithms, mathematical models, and risk parameters provided are strictly experimental and intended for research purposes.
2. **Assumption of Risk:** Trading in financial markets, especially algorithmic execution of derivatives or binary options, carries an exceptionally high level of risk. This software operates autonomously and may incur rapid financial losses. You may lose some or all of your initial investment.
3. **No Warranty:** This software is provided "AS IS", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.
4. **Limitation of Liability:** In no event shall the authors, contributors, or copyright holders be liable for any claim, damages, financial loss, or other liability, whether in an action of contract, tort or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

**You are solely responsible for your own financial decisions, security keys, API tokens, and any direct or indirect losses resulting from the use of this framework.** We highly advise utilizing the built-in `Demo Mode` extensively before transitioning to a production environment with real capital.

Please consult the accompanying [LICENSE](LICENSE) file for further legal stipulations.
