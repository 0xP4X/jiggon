import json
import asyncio
import httpx
import websockets
from collections import deque
from datetime import datetime

class DerivWebSocket:
    def __init__(self, app_id="36544", symbol="R_100", granularity=60):
        self.app_id = app_id
        self.url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        self.symbol = symbol
        self.granularity = granularity
        
        self.price = 0.0
        self.opens = deque(maxlen=200)
        self.highs = deque(maxlen=200)
        self.lows = deque(maxlen=200)
        self.closes = deque(maxlen=200)
        self.dates = deque(maxlen=200)
        
        self.is_connected = False
        self._ws = None

    async def connect_and_listen(self, on_tick_callback=None, api_token=None, account_id=None, on_error_callback=None):
        while True:
            try:
                ws_url = self.url
                is_otp_auth = False
                
                if api_token and account_id:
                    api_token = api_token.strip()
                    account_id = account_id.strip()
                    rest_url = f"https://api.derivws.com/trading/v1/options/accounts/{account_id}/otp"
                    headers = {
                        "Authorization": f"Bearer {api_token}",
                        "Deriv-App-ID": str(self.app_id).strip(),
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.post(rest_url, headers=headers)
                            if resp.status_code == 200:
                                data = resp.json()
                                fetched_url = data.get("data", {}).get("url")
                                if fetched_url:
                                    ws_url = fetched_url
                                    is_otp_auth = True
                            else:
                                err_msg = f"OTP Fetch Failed: {resp.status_code} {resp.text}"
                                if on_error_callback: on_error_callback(err_msg)
                    except Exception as e:
                        err_msg = f"OTP REST Exception: {e}"
                        if on_error_callback: on_error_callback(err_msg)

                async with websockets.connect(ws_url, ping_interval=None, close_timeout=10) as ws:
                    self._ws = ws
                    self.is_connected = True
                    
                    if api_token and not is_otp_auth:
                        auth_req = {"authorize": api_token}
                        await ws.send(json.dumps(auth_req))
                    
                    subscribe_req = {
                        "ticks_history": self.symbol,
                        "adjust_start_time": 1,
                        "count": 50,
                        "end": "latest",
                        "start": 1,
                        "style": "candles",
                        "subscribe": 1,
                        "granularity": self.granularity
                    }
                    await ws.send(json.dumps(subscribe_req))
                    
                    async def ping_loop():
                        try:
                            while self.is_connected and self._ws == ws:
                                await ws.send(json.dumps({"ping": 1}))
                                await asyncio.sleep(30)
                        except Exception:
                            pass
                            
                    ping_task = asyncio.create_task(ping_loop())
                    try:
                        async for message in ws:
                            data = json.loads(message)
                            
                            if "error" in data:
                                print(f"WebSocket Error: {data['error']['message']}")
                                continue
                                
                            if "ping" in data or data.get("msg_type") == "ping":
                                continue
                                
                            if "candles" in data:
                                candles = data["candles"]
                                self.opens.clear()
                                self.highs.clear()
                                self.lows.clear()
                                self.closes.clear()
                                self.dates.clear()
                                
                                for c in candles[-50:]:
                                    self.opens.append(float(c["open"]))
                                    self.highs.append(float(c["high"]))
                                    self.lows.append(float(c["low"]))
                                    self.closes.append(float(c["close"]))
                                    
                                    dt = datetime.fromtimestamp(c["epoch"])
                                    self.dates.append(dt.strftime("%d/%m/%Y %H:%M:%S"))
                                    
                                self.price = self.closes[-1]
                                if on_tick_callback:
                                    on_tick_callback()
                                    
                            elif "ohlc" in data:
                                c = data["ohlc"]
                                
                                dt = datetime.fromtimestamp(c["open_time"])
                                date_str = dt.strftime("%d/%m/%Y %H:%M:%S")
                                
                                if len(self.dates) == 0 or self.dates[-1] != date_str:
                                    self.opens.append(float(c["open"]))
                                    self.highs.append(float(c["high"]))
                                    self.lows.append(float(c["low"]))
                                    self.closes.append(float(c["close"]))
                                    self.dates.append(date_str)
                                else:
                                    self.highs[-1] = float(c["high"])
                                    self.lows[-1] = float(c["low"])
                                    self.closes[-1] = float(c["close"])
                                    
                                self.price = float(c["close"])
                                
                                if on_tick_callback:
                                    on_tick_callback()
                            else:
                                if on_error_callback:
                                    on_error_callback(f"Unknown WS Message: {list(data.keys())}")
                    finally:
                        ping_task.cancel()
            except Exception as e:
                self.is_connected = False
                self._ws = None
                if on_error_callback:
                    on_error_callback(f"WebSocket Error: {e}")
                await asyncio.sleep(3) # Wait before reconnecting
