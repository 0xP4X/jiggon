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
from textual.widgets import Header, Footer, DataTable, Log, Input, Button, Label, RadioSet, RadioButton, TextArea, Select
from textual.containers import Horizontal, Vertical
from textual_plotext import PlotextPlot

from app.analysis.market import analyze_market
from app.strategy.confidence import calculate_confidence, is_trade_approved
from app.strategy.signals import evaluate_best_strategy
from app.risk.engine import RiskState, evaluate_risk, RiskDecision
from app.data.deriv_ws import DerivWebSocket
from app.execution.engine import validate_execution, TradeSignal
from app.ai.predictor import RuleBasedPredictor, Prediction
from app.strategy.parser import parse_jiggon_strategy
from app.broker.client import BrokerClient

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(ENV_PATH)

class CandlestickChart(PlotextPlot):
    def update_chart(self, dates, opens, highs, lows, closes):
        self.plt.clear_figure()
        self.plt.theme('dark')
        self.plt.date_form('d/m/Y H:M:S')
        data = {
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes
        }
        self.plt.candlestick(dates, data)
        self.refresh()

class OnboardingWizard(Screen):
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
            Label("Strategy Aggression", classes="wizard_label"),
            Select(
                options=[("Conservative", "cons"), ("Balanced", "bal"), ("Aggressive", "agg")],
                value="bal",
                id="aggression_select"
            ),
            Horizontal(
                Vertical(
                    Label("Stake ($)", classes="wizard_label"),
                    Input(value="10.0", placeholder="e.g. 10.0", id="stake_input"),
                    classes="input_col"
                ),
                Vertical(
                    Label("Volatility Index", classes="wizard_label"),
                    Input(value="100", placeholder="e.g. 10, 25, 50, 100", id="symbol_input"),
                    classes="input_col"
                ),
                Vertical(
                    Label("Duration (Ticks)", classes="wizard_label"),
                    Input(value="5", placeholder="e.g. 5", id="duration_input"),
                    classes="input_col"
                )
            ),
            
            Label("Custom Algorithm", classes="wizard_label", id="custom_script_label"),
            TextArea("IF RSI < 45 AND EMA_TREND == BULLISH THEN BUY\nIF RSI > 55 AND EMA_TREND == BEARISH THEN SELL", id="custom_script_area"),
            
            Button("Launch Terminal", variant="primary", id="launch_btn"),
            id="wizard_dialog"
        )

    def on_mount(self) -> None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "jiggon_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                self.query_one("#drawdown_input", Input).value = str(cfg.get("drawdown", "5.0"))
                self.query_one("#tp_input", Input).value = str(cfg.get("take_profit", "0.0"))
                self.query_one("#atr_input", Input).value = str(cfg.get("atr", "80.0"))
                self.query_one("#stake_input", Input).value = str(cfg.get("stake", "10.0"))
                self.query_one("#symbol_input", Input).value = str(cfg.get("symbol", "100"))
                self.query_one("#duration_input", Input).value = str(cfg.get("duration", "5"))
                self.query_one("#aggression_select", Select).value = cfg.get("aggression", "bal")
            except Exception:
                pass

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "strat_radios":
            is_custom = event.pressed.id == "strat_custom"
            self.query_one("#custom_script_label").display = is_custom
            self.query_one("#custom_script_area").display = is_custom

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
                self.app.duration = dur_val
            except ValueError:
                self.app.max_drawdown = 5.0
                self.app.take_profit = 0.0
                self.app.abnormal_atr = 80.0
                self.app.stake_size = 10.0
                self.app.duration = 5
                
            raw_symbol = self.query_one("#symbol_input", Input).value.strip() or "100"
            if not raw_symbol.startswith("R_") and raw_symbol.isdigit():
                self.app.symbol = f"R_{raw_symbol}"
            else:
                self.app.symbol = raw_symbol
                
            self.app.aggression = self.query_one("#aggression_select", Select).value
            self.app.api_token = self.query_one("#token_input", Input).value
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
                "aggression": self.app.aggression
            }
            try:
                config_path = os.path.join(os.path.dirname(__file__), "..", "jiggon_config.json")
                with open(config_path, "w") as f:
                    json.dump(cfg, f)
            except Exception:
                pass
            
            self.app.pop_screen()
            self.app.start_engine()

class JiggonTerminal(App):
    TITLE = "Jiggon Quant Terminal"
    
    CSS = """
    Screen {
        background: #24273a;
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
    }
    
    DataTable {
        background: #363a4f;
        color: #cad3f5;
    }
    Log {
        background: #1e2030;
        color: #cad3f5;
    }
    
    OnboardingWizard {
        align: center middle;
        background: rgba(36, 39, 58, 0.6);
    }
    #wizard_dialog {
        width: 45;
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
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "toggle_safe_mode", "Toggle Safe Mode"),
        ("w", "push_screen('wizard')", "Reopen Wizard"),
        ("+", "zoom_in", "Zoom In"),
        ("-", "zoom_out", "Zoom Out"),
    ]

    def __init__(self):
        super().__init__()
        self.app_id = int(os.environ.get("DERIV_APP_ID", "1089"))
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
        
        self.portfolio_balance = 0.0
        self.trades_won = 0
        self.trades_lost = 0
        self.active_trades = 0
        self.api_token = ""
        self.env_name = "Demo"
        self.trade_in_progress = False
        self.chart_zoom = 50

    def on_mount(self) -> None:
        self.install_screen(OnboardingWizard(), name="wizard")
        self.push_screen("wizard")
        
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
        
        if self.api_token:
            sys_log.write_line("[SYSTEM] API Token detected. Initializing Broker Client.")
            self.broker = BrokerClient(app_id=self.app_id, api_token=self.api_token, endpoint="wss://ws.binaryws.com/websockets/v3")
            self.run_worker(self.fetch_initial_balance())
        else:
            sys_log.write_line("[SYSTEM] No API Token provided. Executions will be BLOCKED.")
            
        sys_log.write_line(f"[SYSTEM] Terminal Booted. Connecting to Deriv Live WebSocket for {self.symbol}...")
        self.market = DerivWebSocket(app_id=str(self.app_id), symbol=self.symbol)
        self.run_worker(self.market.connect_and_listen(on_tick_callback=self._trigger_tick, api_token=self.api_token))

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
        except Exception as e:
            sys_log = self.query_one("#system_log", Log)
            sys_log.write_line(f"[ERROR] Exception during balance fetch: {e}")

    def _trigger_tick(self):
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
                sys_log.write_line(f"[ERROR] Trade rejected: {res['error']['message']}")
            else:
                buy_details = res.get("buy", {})
                sys_log.write_line(f"[SUCCESS] Trade {buy_details.get('contract_id')} opened at {buy_details.get('buy_price')}.")
                
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
            return
            
        # Synthesize volume from tick count for real operation
        # In a generic OHLC scenario, we assume each minute candle has roughly 30 ticks
        synthetic_volumes = [30.0 + random.uniform(-10, 10)] * len(self.market.closes)
        
        snapshot = analyze_market(
            opens=list(self.market.opens),
            highs=list(self.market.highs),
            lows=list(self.market.lows),
            closes=list(self.market.closes),
            volumes=synthetic_volumes,
            atr_low_threshold=5.0,
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
            direction = parse_jiggon_strategy(self.custom_script_text, snapshot)
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
            list(self.market.closes)[-self.chart_zoom:]
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

if __name__ == "__main__":
    app = JiggonTerminal()
    app.run()
