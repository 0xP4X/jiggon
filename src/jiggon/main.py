import sys
import os
import asyncio
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import random
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass
from dotenv import set_key, load_dotenv

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Log, Input, Button, Label, RadioSet, RadioButton, TextArea, Select, Markdown
from textual.containers import Horizontal, Vertical
from textual_plotext import PlotextPlot

from jiggon.analysis.market import analyze_market
from jiggon.strategy.confidence import calculate_confidence, is_trade_approved
from jiggon.strategy.signals import evaluate_best_strategy
from jiggon.risk.engine import RiskState, evaluate_risk, RiskDecision
from typing import Optional

from jiggon import __version__
from jiggon.data.deriv_ws import DerivWebSocket
from jiggon.execution.engine import validate_execution, TradeSignal
from jiggon.ai.predictor import RuleBasedPredictor, Prediction
from jiggon.strategy.parser import parse_jiggon_strategy
from jiggon.broker.client import BrokerClient

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(ENV_PATH)

class CandlestickChart(PlotextPlot):
    def update_chart(self, dates, opens, highs, lows, closes, trade_markers=None, theme="classic"):
        self.plt.clear_figure()
        self.plt.theme('dark')
        self.plt.canvas_color((54, 58, 79))
        self.plt.axes_color((54, 58, 79))
        self.plt.ticks_color((202, 211, 245))
        self.plt.date_form('d/m/Y H:M:S')
        data = {
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes
        }
        
        if theme == "catppuccin":
            candle_colors = [(166, 218, 149), (237, 135, 150)]
        elif theme == "neon":
            candle_colors = [(0, 255, 255), (255, 0, 255)]
        elif theme == "mono":
            candle_colors = [(255, 255, 255), (100, 100, 100)]
        else:
            candle_colors = ["green", "red"]
            
        self.plt.candlestick(dates, data, colors=candle_colors)
        
        if trade_markers:
            buy_dates = [m["date"] for m in trade_markers if m["direction"] in ["BUY", "CALL"]]
            buy_prices = [m["price"] for m in trade_markers if m["direction"] in ["BUY", "CALL"]]
            sell_dates = [m["date"] for m in trade_markers if m["direction"] in ["SELL", "PUT"]]
            sell_prices = [m["price"] for m in trade_markers if m["direction"] in ["SELL", "PUT"]]
            
            if buy_dates:
                self.plt.scatter(buy_dates, buy_prices, color="green", marker="^")
            if sell_dates:
                self.plt.scatter(sell_dates, sell_prices, color="red", marker="v")
                
        self.refresh()

class SplashScreen(Screen):
    def compose(self) -> ComposeResult:
        SPLASH_ART = f"""
                                                                                
                         _   ___  _____  _____  _____  _   _                    
                        | | |_ _||  __ \|  __ \|  _  || \ | |                   
                        | |  | | | |  \/| |  \/| | | ||  \| |                   
                    _   | |  | | | | __ | | __ | | | || . ` |                   
                   | |__| | _| |_| |_\ \| |_\ \\ \_/ /| |\  |                   
                    \____/  \___/ \____/ \____/ \___/ \_| \_/                   
                                                                                
                            Created by Prince Ofori (0xP4X)                     
                                Version: v{__version__}                         
                                                                                
"""
        yield Vertical(
            Label(SPLASH_ART, id="splash_logo"),
            Label("Initializing Quant Engine...", id="splash_text"),
            id="splash_container"
        )
        
    def on_mount(self) -> None:
        self.set_timer(2.0, self.finish_splash)
        
    def finish_splash(self) -> None:
        self.app.pop_screen()
        
        # Check for existing configuration to skip wizard
        config_path = os.path.join(os.path.expanduser("~"), ".jiggon_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                if cfg.get("api_token"):
                    self.app.max_drawdown = float(cfg.get("drawdown", "5.0"))
                    self.app.take_profit = float(cfg.get("take_profit", "0.0"))
                    self.app.abnormal_atr = float(cfg.get("atr", "80.0"))
                    self.app.stake_size = float(cfg.get("stake", "10.0"))
                    self.app.duration = int(cfg.get("duration", "5"))
                    self.app.symbol = cfg.get("symbol", "R_100")
                    if not self.app.symbol.startswith("R_") and self.app.symbol.isdigit():
                        self.app.symbol = f"R_{self.app.symbol}"
                    self.app.aggression = cfg.get("aggression", "bal")
                    self.app.chart_theme = cfg.get("chart_theme", "catppuccin")
                    self.app.timeframe = int(cfg.get("timeframe", "60"))
                    self.app.account_id = cfg.get("account_id", "")
                    self.app.api_token = cfg.get("api_token", "")
                    self.app.app_id = cfg.get("app_id", os.environ.get("DERIV_APP_ID", "36544"))
                    self.app.env_name = "Live" if self.app.api_token else "Demo"
                    
                    self.app.start_engine()
                    return
        except Exception:
            pass
            
        self.app.push_screen("wizard")

class OnboardingWizard(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Close Wizard"),
    ]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Welcome to Jiggon", id="wizard_title"),
            
            Label("Environment", classes="wizard_label"),
            RadioSet(
                RadioButton("Demo (Paper Trading)", id="env_demo", value=True),
                RadioButton("Live (Real Funds)", id="env_live"),
                id="env_radios"
            ),
            
            Label("API Token", classes="wizard_label"),
            Input(placeholder="Enter Deriv API Token...", password=True, id="token_input"),
            
            Label("App ID (Optional for PAT)", classes="wizard_label"),
            Input(placeholder="Enter App ID...", id="app_id_input"),
            
            Label("Account ID (e.g. DOT12345)", classes="wizard_label"),
            Input(placeholder="Enter Account ID...", id="account_input"),
            
            Label("Strategy", classes="wizard_label"),
            RadioSet(
                RadioButton("Default Strategy (VWAP + Trend)", id="strat_master", value=True),
                RadioButton("Custom .jiggon Script", id="strat_custom"),
                id="strat_radios"
            ),
            
            Horizontal(
                Vertical(
                    Label("Max Drawdown (%)", classes="wizard_label"),
                    Input(value="5.0", placeholder="e.g. 5.0", id="drawdown_input"),
                    classes="input_col"
                ),
                Vertical(
                    Label("Take Profit ($)", classes="wizard_label"),
                    Input(value="0.0", placeholder="e.g. 50.0", id="tp_input"),
                    classes="input_col"
                ),
                Vertical(
                    Label("ATR Threshold", classes="wizard_label"),
                    Input(value="80.0", placeholder="e.g. 80.0", id="atr_input"),
                    classes="input_col"
                )
            ),
            Horizontal(
                Vertical(
                    Label("Strategy Aggression", classes="wizard_label"),
                    Select(
                        options=[("Conservative", "cons"), ("Balanced", "bal"), ("Aggressive", "agg")],
                        value="bal",
                        id="aggression_select"
                    ),
                    classes="input_col"
                ),
                Vertical(
                    Label("Chart Theme", classes="wizard_label"),
                    Select(
                        options=[("Jiggon Midnight", "catppuccin"), ("Jiggon Cyberpunk", "neon"), ("Classic Terminal", "classic"), ("Jiggon Monochrome", "mono")],
                        value="catppuccin",
                        id="theme_select"
                    ),
                    classes="input_col"
                )
            ),
            Horizontal(
                Vertical(
                    Label("Stake ($)", classes="wizard_label"),
                    Input(value="10.0", placeholder="e.g. 10.0", id="stake_input"),
                    classes="input_col"
                ),
                Vertical(
                    Label("Volatility Index", classes="wizard_label"),
                    Select(
                        options=[("Vol 10", "10"), ("Vol 25", "25"), ("Vol 50", "50"), ("Vol 75", "75"), ("Vol 100", "100"), ("Vol 10 (1s)", "1HZ10V"), ("Vol 100 (1s)", "1HZ100V")],
                        value="100",
                        id="symbol_input"
                    ),
                    classes="input_col"
                ),
                Vertical(
                    Label("Duration (Ticks)", classes="wizard_label"),
                    Input(value="5", placeholder="e.g. 5", id="duration_input"),
                    classes="input_col"
                ),
                Vertical(
                    Label("Timeframe", classes="wizard_label"),
                    Select(
                        options=[("1 Minute", "60"), ("5 Minutes", "300"), ("15 Minutes", "900"), ("1 Hour", "3600"), ("1 Day", "86400")],
                        value="60",
                        id="timeframe_select"
                    ),
                    classes="input_col"
                )
            ),
            
            Label("Custom Algorithm", classes="wizard_label", id="custom_script_label"),
            TextArea("IF RSI < 30 and CLOSE < BB_LOWER and STOCH_K > STOCH_D THEN BUY\nIF RSI > 70 and CLOSE > BB_UPPER and STOCH_K < STOCH_D THEN SELL", id="custom_script_area"),
            
            Horizontal(
                Button("Launch Terminal", variant="primary", id="launch_btn"),
                Button("Cancel", variant="default", id="cancel_btn"),
            ),
            id="wizard_dialog"
        )

    def on_mount(self) -> None:
        config_path = os.path.join(os.path.expanduser("~"), ".jiggon_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                self.query_one("#drawdown_input", Input).value = str(cfg.get("drawdown", "5.0"))
                self.query_one("#tp_input", Input).value = str(cfg.get("take_profit", "0.0"))
                self.query_one("#atr_input", Input).value = str(cfg.get("atr", "80.0"))
                self.query_one("#stake_input", Input).value = str(cfg.get("stake", "10.0"))
                self.query_one("#symbol_input", Select).value = str(cfg.get("symbol", "100"))
                self.query_one("#duration_input", Input).value = str(cfg.get("duration", "5"))
                self.query_one("#timeframe_select", Select).value = str(cfg.get("timeframe", "60"))
                self.query_one("#aggression_select", Select).value = cfg.get("aggression", "bal")
                self.query_one("#theme_select", Select).value = cfg.get("chart_theme", "catppuccin")
                self.query_one("#account_input", Input).value = str(cfg.get("account_id", ""))
                self.query_one("#token_input", Input).value = str(cfg.get("api_token", ""))
                self.query_one("#app_id_input", Input).value = str(cfg.get("app_id", "36544"))
                sys_log = self.app.query_one("#system_log", Log)
                sys_log.write_line("[SYSTEM] Loaded configuration from disk.")
            except Exception:
                pass

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "strat_radios":
            is_custom = event.pressed.id == "strat_custom"
            self.query_one("#custom_script_label").display = is_custom
            self.query_one("#custom_script_area").display = is_custom

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch_btn":
            try:
                drawdown_val = float(self.query_one("#drawdown_input", Input).value)
                tp_val = float(self.query_one("#tp_input", Input).value)
                atr_val = float(self.query_one("#atr_input", Input).value)
                stake_val = float(self.query_one("#stake_input", Input).value)
                dur_val = int(self.query_one("#duration_input", Input).value)
                self.app.max_drawdown = drawdown_val
                self.app.take_profit = tp_val
                self.app.abnormal_atr = atr_val
                self.app.stake_size = stake_val
                self.app.duration = min(dur_val, 10)
            except ValueError:
                self.app.max_drawdown = 5.0
                self.app.take_profit = 0.0
                self.app.abnormal_atr = 80.0
                self.app.stake_size = 10.0
                self.app.duration = 5
                
            raw_symbol = self.query_one("#symbol_input", Select).value
            if not raw_symbol.startswith("R_") and raw_symbol.isdigit():
                self.app.symbol = f"R_{raw_symbol}"
            else:
                self.app.symbol = raw_symbol
                
            self.app.aggression = self.query_one("#aggression_select", Select).value
            self.app.chart_theme = self.query_one("#theme_select", Select).value
            self.app.timeframe = int(self.query_one("#timeframe_select", Select).value)
            self.app.api_token = self.query_one("#token_input", Input).value
            self.app.account_id = self.query_one("#account_input", Input).value
            app_id_val = self.query_one("#app_id_input", Input).value.strip()
            self.app.app_id = app_id_val if app_id_val else os.environ.get("DERIV_APP_ID", "36544")
            self.app.custom_script_text = self.query_one("#custom_script_area", TextArea).text
            
            strat_radios = self.query_one("#strat_radios", RadioSet)
            self.app.use_custom_strat = (strat_radios.pressed_index == 1)
            
            env_radios = self.query_one("#env_radios", RadioSet)
            self.app.env_name = "Demo" if env_radios.pressed_index == 0 else "Live"
            
            # Save config
            cfg = {
                "drawdown": self.app.max_drawdown,
                "take_profit": self.app.take_profit,
                "atr": self.app.abnormal_atr,
                "stake": self.app.stake_size,
                "symbol": raw_symbol,
                "duration": self.app.duration,
                "timeframe": self.app.timeframe,
                "aggression": self.app.aggression,
                "chart_theme": self.app.chart_theme,
                "account_id": getattr(self.app, "account_id", ""),
                "api_token": getattr(self.app, "api_token", ""),
                "app_id": getattr(self.app, "app_id", "36544")
            }
            try:
                config_path = os.path.join(os.path.expanduser("~"), ".jiggon_config.json")
                with open(config_path, "w") as f:
                    json.dump(cfg, f)
            except Exception:
                pass
            
            
            self.app.pop_screen()
            self.app.start_engine()
        elif event.button.id == "cancel_btn":
            self.app.pop_screen()

class HelpScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Close Help")]
    
    def compose(self) -> ComposeResult:
        help_text = """
# Jiggon Quant Terminal Help

## Global Hotkeys
- `+` / `-` : Zoom the chart in and out
- `w` : Reopen the Configuration Wizard
- `s` : Toggle Safe Mode (pause bot trading manually)
- `q` : Quit the application
- `?` : Open this Help menu
- `ESC` : Close dialogs (Wizard, Help)

## Chart Markers
- 🟢 **Upward Green Triangle (^)** : Represents a BUY or CALL trade executed by the bot.
- 🔴 **Downward Red Triangle (v)** : Represents a SELL or PUT trade executed by the bot.

## Wizard Settings
- **Timeframe**: Changes the granularity of each candlestick (e.g. 1 minute per candle).
- **Duration (Ticks)**: How long the bot's trade lasts in ticks (Deriv limits this to 5-10 ticks max).
- **Aggression**: 
  - *Balanced*: Requires high confidence across multiple indicators.
  - *Aggressive*: Triggers trades much more frequently on minor momentum swings.
- **Max Drawdown**: The maximum percentage of your balance you are willing to lose. If hit, the bot enters Safe Mode permanently.

*Press `ESC` to return to the terminal.*
"""
        yield Vertical(
            Markdown(help_text),
            id="help_dialog"
        )

class JiggonTerminal(App):
    TITLE = "Jiggon Quant Terminal"
    SUB_TITLE = "Core by 0xP4X"
    
    CSS = """
    Screen {
        background: #24273a;
    }
    #splash_container {
        align: center middle;
        height: 100%;
        background: #1e2030;
    }
    #splash_logo {
        text-align: center;
        color: #8aadf4;
        text-style: bold;
    }
    #splash_text {
        text-align: center;
        color: #cad3f5;
        margin-top: 2;
    }
    #main_container {
        width: 100%;
        height: 100%;
        layout: grid;
        grid-size: 3 3;
        grid-rows: 10 3fr 1fr;
        grid-columns: 1fr 1fr 1fr;
    }
    .panel {
        border: round #8aadf4;
        background: #363a4f;
        height: 100%;
        width: 100%;
    }
    #conf_panel { row-span: 1; column-span: 1; }
    #risk_panel { row-span: 1; column-span: 1; }
    #portfolio_panel { row-span: 1; column-span: 1; }
    
    #price_panel {
        row-span: 1;
        column-span: 3;
        border: solid #a6da95;
    }
    #log_panel {
        row-span: 1;
        column-span: 3;
        border: dashed #eed49f;
        layout: vertical;
    }
    #log_header {
        height: 3;
        width: 100%;
        background: #24273a;
        padding: 0 2;
        align: left middle;
    }
    #log_title {
        color: #eed49f;
        text-style: bold;
        width: 1fr;
        height: 100%;
        content-align: left middle;
    }
    #copy_logs_btn {
        min-width: 15;
        height: 100%;
        background: #eed49f;
        color: #1e2030;
        border: none;
    }
    #system_log {
        height: 1fr;
        background: #1e2030;
        color: #cad3f5;
    }
    
    DataTable {
        background: #363a4f;
        color: #cad3f5;
    }
    
    OnboardingWizard {
        align: center middle;
        background: rgba(36, 39, 58, 0.6);
    }
    #wizard_dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        background: #363a4f;
        border: heavy #8aadf4;
    }
    #wizard_title {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
        text-style: bold;
        color: #cad3f5;
    }
    .wizard_label {
        text-style: bold;
        color: #a5adcb;
    }
    RadioSet {
        border: none;
        padding: 0;
        margin-bottom: 1;
    }
    Horizontal {
        height: auto;
    }
    .input_col {
        width: 1fr;
        margin-right: 1;
        height: auto;
    }
    #launch_btn {
        margin-top: 1;
        width: 100%;
    }
    #custom_script_label {
        display: none;
    }
    #custom_script_area {
        display: none;
        height: 6;
        margin-bottom: 1;
        border: solid #8aadf4;
        background: #1e2030;
    }
    .input_col {
        width: 1fr;
        margin-right: 1;
        height: auto;
    }
    
    HelpScreen {
        align: center middle;
        background: rgba(36, 39, 58, 0.8);
    }
    #help_dialog {
        width: 80;
        height: 80%;
        padding: 1 2;
        background: #363a4f;
        border: heavy #a6da95;
        overflow-y: scroll;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "toggle_safe_mode", "Toggle Safe Mode"),
        ("w", "push_screen('wizard')", "Reopen Wizard"),
        ("?", "push_screen('help')", "Help"),
        ("+", "zoom_in", "Zoom In"),
        ("-", "zoom_out", "Zoom Out"),
        ("c", "copy_logs", "Copy Logs"),
    ]

    def __init__(self):
        super().__init__()
        self.app_id = os.environ.get("DERIV_APP_ID", "36544")
        self.market = None
        self.risk_state = RiskState(daily_drawdown_pct=0.0, daily_profit=0.0, consecutive_losses=0, safe_mode_active=False, safe_mode_reason="")
        self.ai_predictor = RuleBasedPredictor()
        self.broker = None
        self.use_custom_strat = False
        
        self.max_drawdown = float(os.environ.get("MAX_DAILY_DRAWDOWN", "5.0"))
        self.abnormal_atr = float(os.environ.get("ABNORMAL_ATR_THRESHOLD", "80.0"))
        self.stake_size = 10.0
        self.take_profit = 0.0
        self.daily_profit = 0.0
        self.aggression = "bal"
        self.symbol = "R_100"
        self.duration = 5
        self.custom_script_text = ""
        self.chart_theme = "catppuccin"
        self.timeframe = 60
        
        self.portfolio_balance = 0.0
        self.trades_won = 0
        self.trades_lost = 0
        self.active_trades = 0
        self.api_token = os.environ.get("DERIV_API_TOKEN", "")
        self.account_id = os.environ.get("DERIV_ACCOUNT_ID", "")
        self.env_name = "Demo"
        self.trade_in_progress = False
        self.trade_history = []
        self.chart_zoom = 50

    def on_mount(self) -> None:
        self.title = f"Jiggon Quant Terminal (v{__version__})"
        self.install_screen(SplashScreen(), name="splash")
        self.install_screen(OnboardingWizard(), name="wizard")
        self.install_screen(HelpScreen(), name="help")
        self.push_screen("splash")
        
        conf_table = self.query_one("#confidence_table", DataTable)
        conf_table.add_columns("Metric", "Weight", "Status")
        conf_table.add_row("Waiting for data...", "-", "-")
        
        risk_table = self.query_one("#risk_table", DataTable)
        risk_table.add_columns("Risk Metric", "Value")
        risk_table.add_row("Live Price", "Loading...")
        risk_table.add_row("Drawdown Limit", f"{self.max_drawdown}%")
        
        port_table = self.query_one("#portfolio_table", DataTable)
        port_table.add_columns("Account", "Value")
        port_table.add_row("Balance", f"Loading...")
        port_table.add_row("Win Rate", "0.0%")
        port_table.add_row("Active Trades", "0")
        
    def start_engine(self) -> None:
        sys_log = self.query_one("#system_log", Log)
        sys_log.write_line(f"[SYSTEM] Booting in {self.env_name} Mode.")
        sys_log.write_line(f"[SYSTEM] Risk Config: Drawdown {self.max_drawdown}%, ATR {self.abnormal_atr}.")
        sys_log.write_line(f"[SYSTEM] Strategy: {'Custom DSL' if self.use_custom_strat else 'Default (VWAP + Trend)'}")
        
        if self.api_token and getattr(self, "account_id", ""):
            sys_log.write_line("[SYSTEM] API Token & Account ID detected. Initializing Broker Client.")
            self.broker = BrokerClient(app_id=self.app_id, api_token=self.api_token, account_id=self.account_id)
            self.run_worker(self.fetch_initial_balance())
        else:
            sys_log.write_line("[SYSTEM] Missing API Token or Account ID. Executions will be BLOCKED.")
            
        def log_err(msg):
            sys_log.write_line(f"[ERROR] {msg}")
            
        sys_log.write_line(f"[SYSTEM] Terminal Booted. Connecting to Deriv Live WebSocket for {self.symbol} ({self.timeframe}s candles)...")
        self.market = DerivWebSocket(app_id=str(self.app_id), symbol=self.symbol, granularity=self.timeframe)
        self.run_worker(self.market.connect_and_listen(on_tick_callback=self._trigger_tick, api_token=self.api_token, account_id=getattr(self, "account_id", ""), on_error_callback=log_err))

    def action_zoom_in(self) -> None:
        if self.chart_zoom > 10:
            self.chart_zoom -= 10
            sys_log = self.query_one("#system_log", Log)
            sys_log.write_line(f"[SYSTEM] Chart Zoomed IN: showing {self.chart_zoom} candles.")

    def action_zoom_out(self) -> None:
        if self.chart_zoom < 200:
            self.chart_zoom += 10
            sys_log = self.query_one("#system_log", Log)
            sys_log.write_line(f"[SYSTEM] Chart Zoomed OUT: showing {self.chart_zoom} candles.")

    def action_copy_logs(self) -> None:
        try:
            import os
            from datetime import datetime
            sys_log = self.query_one("#system_log", Log)
            log_text = "\n".join([line if isinstance(line, str) else line.text for line in sys_log.lines])
            
            # Try to copy to clipboard natively
            try:
                self.app.clipboard = log_text
            except Exception:
                pass
                
            # Always save to desktop as a fallback
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filename = f"jiggon_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(desktop, filename)
            
            with open(filepath, "w") as f:
                f.write(log_text)
                
            self.notify(f"Logs saved to Desktop ({filename})!")
        except Exception as e:
            self.notify(f"Could not save logs: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy_logs_btn":
            self.action_copy_logs()

    async def fetch_initial_balance(self):
        try:
            sys_log = self.query_one("#system_log", Log)
            res = await self.broker.get_balance()
            if "balance" in res:
                self.portfolio_balance = float(res["balance"]["balance"])
                sys_log.write_line(f"[BROKER] Initial balance loaded: ${self.portfolio_balance:,.2f}")
                self.update_portfolio_table()
            elif "error" in res:
                sys_log.write_line(f"[ERROR] Broker balance fetch failed: {res['error']['message']}")
                self.broker = None
        except Exception as e:
            sys_log = self.query_one("#system_log", Log)
            sys_log.write_line(f"[ERROR] Exception during balance fetch: {e}")
            self.broker = None

    def _trigger_tick(self):
        try:
            sys_log = self.query_one("#system_log", Log)
            if not hasattr(self, "_debug_trigger"):
                sys_log.write_line("[DEBUG] _trigger_tick called by websocket")
                self._debug_trigger = True
        except: pass
        self.call_later(self.on_tick)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical(id="main_container"):
            with Vertical(classes="panel", id="conf_panel"):
                yield DataTable(id="confidence_table")
            with Vertical(classes="panel", id="risk_panel"):
                yield DataTable(id="risk_table")
            with Vertical(classes="panel", id="portfolio_panel"):
                yield DataTable(id="portfolio_table")
            with Vertical(classes="panel", id="price_panel"):
                yield CandlestickChart(id="price_chart")
            with Vertical(classes="panel", id="log_panel"):
                with Horizontal(id="log_header"):
                    yield Label("System Logs", id="log_title")
                    yield Button("📋 Copy Logs", id="copy_logs_btn", variant="default")
                yield Log(id="system_log", max_lines=50)
                
        yield Footer()

    def action_toggle_safe_mode(self) -> None:
        sys_log = self.query_one("#system_log", Log)
        if self.risk_state.safe_mode_active:
            self.risk_state.safe_mode_active = False
            self.risk_state.safe_mode_reason = ""
            sys_log.write_line("[WARNING] Safe Mode manually DISABLED.")
        else:
            self.risk_state.safe_mode_active = True
            self.risk_state.safe_mode_reason = "Manual Override"
            sys_log.write_line("[CRITICAL] Safe Mode manually ENABLED.")

    async def execute_trade(self, direction: str, stake: float):
        sys_log = self.query_one("#system_log", Log)
        self.trade_in_progress = True
        self.active_trades = 1
        self.update_portfolio_table()
        
        try:
            sys_log.write_line(f"[EXECUTE] Requesting {direction} contract on {self.symbol} for ${stake:.2f} ({self.duration} ticks)")
            # Deriv Contract Type: CALL or PUT
            contract_type = "CALL" if direction in ["BUY", "CALL"] else "PUT"
            
            res = await self.broker.buy_contract(
                symbol=self.symbol,
                contract_type=contract_type,
                amount=stake,
                duration=self.duration,
                currency="USD",
                price=stake
            )
            
            if "error" in res:
                sys_log.write_line(f"[ERROR] Trade rejected: {res['error'].get('message', '')} {res['error'].get('details', '')}")
            else:
                buy_details = res.get("buy", {})
                price_paid = float(buy_details.get('buy_price', stake))
                sys_log.write_line(f"[SUCCESS] Trade {buy_details.get('contract_id')} opened at {price_paid}.")
                
                # Record trade for chart markers
                self.trade_history.append({
                    "date": self.market.dates[-1],
                    "price": self.market.closes[-1] if direction in ["SELL", "PUT"] else self.market.closes[-1] - (self.market.closes[-1] * 0.0001), 
                    "direction": direction
                })
                
                # Await resolution natively (mock 5 ticks time ~ 10 seconds)
                sys_log.write_line("[WAIT] Waiting 10 seconds for 5-tick contract expiration...")
                await asyncio.sleep(10)
                
                # Re-fetch balance to determine win/loss
                bal_res = await self.broker.get_balance()
                trade_result = "UNKNOWN"
                if "balance" in bal_res:
                    new_balance = float(bal_res["balance"]["balance"])
                    profit_delta = new_balance - self.portfolio_balance
                    self.daily_profit += profit_delta
                    
                    if new_balance > self.portfolio_balance:
                        self.trades_won += 1
                        sys_log.write_line(f"[PROFIT] Trade Won! Old: ${self.portfolio_balance:,.2f} -> New: ${new_balance:,.2f}")
                        self.risk_state.consecutive_losses = 0
                        trade_result = "WIN"
                    else:
                        self.trades_lost += 1
                        sys_log.write_line(f"[LOSS] Trade Lost. Old: ${self.portfolio_balance:,.2f} -> New: ${new_balance:,.2f}")
                        self.risk_state.consecutive_losses += 1
                        trade_result = "LOSS"
                    
                    self.portfolio_balance = new_balance
                    
                # CSV Logging to Desktop
                try:
                    import csv
                    csv_path = os.path.join(os.path.expanduser("~"), "Desktop", "trade_history.csv")
                    file_exists = os.path.exists(csv_path)
                    with open(csv_path, "a", newline="") as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["Time", "Symbol", "Direction", "Stake", "Result", "Balance"])
                        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.symbol, direction, stake, trade_result, self.portfolio_balance])
                except Exception as ex:
                    sys_log.write_line(f"[SYSTEM] Could not log trade: {ex}")
                    
        except Exception as e:
            sys_log.write_line(f"[ERROR] Execution fault: {e}")
            
        finally:
            self.trade_in_progress = False
            self.active_trades = 0
            self.update_portfolio_table()

    def update_portfolio_table(self):
        try:
            port_table = self.query_one("#portfolio_table", DataTable)
            port_table.clear()
            port_table.add_row("Balance", f"${self.portfolio_balance:,.2f}" if self.portfolio_balance > 0 else "N/A")
            
            total_trades = self.trades_won + self.trades_lost
            win_rate = (self.trades_won / total_trades * 100) if total_trades > 0 else 0.0
            port_table.add_row("Win Rate", f"{win_rate:.1f}%")
            port_table.add_row("Active Trades", str(self.active_trades))
        except Exception:
            pass

    def on_tick(self) -> None:
        try:
            sys_log = self.query_one("#system_log", Log)
            chart = self.query_one("#price_chart", CandlestickChart)
        except Exception:
            return  # Skip tick if UI is not yet fully mounted
            
        if not self.market.is_connected or len(self.market.closes) < 50:
            if not hasattr(self, "_debug_skipped"):
                sys_log.write_line(f"[DEBUG] Tick skipped. connected={self.market.is_connected}, len_closes={len(self.market.closes)}")
                self._debug_skipped = True
            return
            
        if not hasattr(self, "_debug_executed"):
            sys_log.write_line(f"[DEBUG] on_tick running! len_closes={len(self.market.closes)}")
            self._debug_executed = True
            
        # Synthesize volume from tick count for real operation
        # In a generic OHLC scenario, we assume each minute candle has roughly 30 ticks
        synthetic_volumes = [30.0 + random.uniform(-10, 10)] * len(self.market.closes)
        
        snapshot = analyze_market(
            opens=list(self.market.opens),
            highs=list(self.market.highs),
            lows=list(self.market.lows),
            closes=list(self.market.closes),
            volumes=synthetic_volumes,
            atr_low_threshold=0.0,
            atr_high_threshold=self.abnormal_atr
        )
        
        self.risk_state.daily_drawdown_pct = 0.0
        self.risk_state.daily_profit = self.daily_profit
        self.risk_state = evaluate_risk(
            self.risk_state, 
            snapshot.atr, 
            abnormal_atr_threshold=self.abnormal_atr, 
            max_daily_drawdown=self.max_drawdown,
            target_profit=self.take_profit
        )
        
        total_trades = self.trades_won + self.trades_lost
        is_profitable = (self.trades_won >= self.trades_lost) if total_trades > 0 else True
        
        if getattr(self, "use_custom_strat", False):
            direction = parse_jiggon_strategy(
                self.custom_script_text, 
                snapshot, 
                self.market.opens[-1], 
                self.market.highs[-1], 
                self.market.lows[-1], 
                self.market.closes[-1]
            )
            strategy_name = "Jiggon Custom DSL"
            
            candle_is_strong = direction != "NONE"
            conf = calculate_confidence(
                ema_aligned=True,
                rsi_confirmed=True,
                atr_valid=True,
                session_profitable=is_profitable,
                candle_strong=candle_is_strong,
                momentum_valid=True
            )
        else:
            strategy_name, direction = evaluate_best_strategy(
                snapshot,
                self.market.opens[-1],
                self.market.closes[-1],
                self.market.highs[-1],
                self.market.lows[-1]
            )
            
            if self.aggression == "cons":
                rsi_ok = (snapshot.rsi > 65 or snapshot.rsi < 35)
            elif self.aggression == "agg":
                rsi_ok = (snapshot.rsi > 50 or snapshot.rsi < 50)
            else:
                rsi_ok = (snapshot.rsi > 55 or snapshot.rsi < 45)
                
            candle_is_strong = direction != "NONE"
            conf = calculate_confidence(
                ema_aligned=snapshot.trend != "mixed",
                rsi_confirmed=rsi_ok,
                atr_valid=snapshot.atr < self.abnormal_atr,
                session_profitable=is_profitable,
                candle_strong=candle_is_strong,
                momentum_valid=snapshot.momentum != "neutral"
            )
        
        approved = is_trade_approved(conf)
        
        # Build Trade Signal Object
        signal = TradeSignal(
            approved=approved and direction != "NONE",
            direction=direction,
            reason=[f"Confidence: {conf.total}/100", f"Strategy: {strategy_name}"]
        )
        
        # Build Risk Decision Object
        risk_decision = RiskDecision(
            allowed=not self.risk_state.safe_mode_active,
            stake=self.stake_size,
            reason=["Safe Mode Active"] if self.risk_state.safe_mode_active else ["Risk Passed"]
        )
        
        # Run AI Predictor (Mathematical Synthetic MTF)
        if snapshot.trend == "bullish":
            mtf_aligned = self.market.closes[-1] > snapshot.ema50
        elif snapshot.trend == "bearish":
            mtf_aligned = self.market.closes[-1] < snapshot.ema50
        else:
            mtf_aligned = False
            
        prediction = self.ai_predictor.predict(conf.total, snapshot.volatility_state, mtf_aligned)
        
        # Final Execution Engine Validation
        decision = validate_execution(signal, risk_decision, prediction)
        
        if decision.execute and not self.trade_in_progress:
            if not self.broker:
                sys_log.write_line(f"[BLOCKED] Signal for {decision.direction} generated, but NO API TOKEN to execute.")
            else:
                self.run_worker(self.execute_trade(decision.direction, decision.stake))
        elif signal.direction != "NONE" and not decision.execute and not self.trade_in_progress:
            reasons_str = " | ".join(decision.reason)
            sys_log.write_line(f"[VETOED] {signal.direction} blocked: {reasons_str}")

        chart.update_chart(
            list(self.market.dates)[-self.chart_zoom:],
            list(self.market.opens)[-self.chart_zoom:],
            list(self.market.highs)[-self.chart_zoom:],
            list(self.market.lows)[-self.chart_zoom:],
            list(self.market.closes)[-self.chart_zoom:],
            trade_markers=self.trade_history,
            theme=self.chart_theme
        )

        conf_table = self.query_one("#confidence_table", DataTable)
        conf_table.clear()
        
        def fmt_pf(val): return "[bold green]PASS[/]" if val else "[bold red]FAIL[/]"
        
        conf_table.add_row("EMA Alignment", "20", fmt_pf(conf.ema_aligned))
        conf_table.add_row("RSI Confirmation", "15", fmt_pf(conf.rsi_confirmed))
        conf_table.add_row("ATR Valid", "15", fmt_pf(conf.atr_valid))
        conf_table.add_row("Session Profitable", "20", fmt_pf(conf.session_profitable))
        conf_table.add_row("Candle Strong", "15", fmt_pf(conf.candle_strong))
        conf_table.add_row("Momentum Valid", "15", fmt_pf(conf.momentum_valid))
        
        ai_rec_color = "bold green" if prediction.recommendation == "EXECUTE" else "bold red"
        conf_table.add_row("AI Recommendation", "100", f"[{ai_rec_color}]{prediction.recommendation}[/]")
        
        score_color = "bold green" if conf.total >= 80 else "bold yellow" if conf.total >= 50 else "bold red"
        conf_table.add_row("TOTAL SCORE", "100", f"[{score_color}]{conf.total}/100[/]")

        risk_table = self.query_one("#risk_table", DataTable)
        risk_table.clear()
        risk_table.add_row("Live Price", f"${self.market.price:,.2f}")
        risk_table.add_row("Active Strategy", f"[cyan]{strategy_name}[/]")
        
        dir_color = "bold green" if direction in ["BUY", "CALL"] else "bold red" if direction in ["SELL", "PUT"] else "dim white"
        risk_table.add_row("Signal", f"[{dir_color}]{direction}[/]")
        
        prob_color = "bold green" if prediction.trade_probability >= 0.75 else "bold yellow" if prediction.trade_probability >= 0.5 else "bold red"
        risk_table.add_row("AI Probability", f"[{prob_color}]{prediction.trade_probability:.1%}[/]")
        risk_table.add_row("AI Risk Eval", f"[yellow]{prediction.risk_level}[/]")
        
        safe_mode_str = "[bold red]ACTIVE (BLOCKED)[/]" if self.risk_state.safe_mode_active else "[bold green]OFF (SAFE)[/]"
        risk_table.add_row("Safe Mode", safe_mode_str)
        risk_table.add_row("Consecutive Losses", str(self.risk_state.consecutive_losses))
        
        self.update_portfolio_table()

def main():
    app = JiggonTerminal()
    app.run()

if __name__ == "__main__":
    main()
