import json
import asyncio
import websockets
from collections import deque
from datetime import datetime

class DerivWebSocket:
    def __init__(self, app_id="1089", symbol="R_100"):
        self.url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        self.symbol = symbol
        
        self.price = 0.0
        self.opens = deque(maxlen=200)
        self.highs = deque(maxlen=200)
        self.lows = deque(maxlen=200)
        self.closes = deque(maxlen=200)
        self.dates = deque(maxlen=200)
        
        self.is_connected = False
        self._ws = None

    async def connect_and_listen(self, on_tick_callback=None, api_token=None):
        while True:
            try:
                async with websockets.connect(self.url, ping_interval=20, ping_timeout=20, close_timeout=10) as ws:
                    self._ws = ws
                    self.is_connected = True
                    
                    if api_token:
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
                        "granularity": 60
                    }
                    await ws.send(json.dumps(subscribe_req))
                    
                    async for message in ws:
                        data = json.loads(message)
                        
                        if "error" in data:
                            print(f"WebSocket Error: {data['error']['message']}")
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
            except Exception:
                self.is_connected = False
                self._ws = None
                await asyncio.sleep(3) # Wait before reconnecting
