import json
from collections.abc import AsyncIterator

import websockets


class BrokerClient:
    def __init__(self, app_id: int, api_token: str, endpoint: str):
        self.url = f"{endpoint}?app_id={app_id}"
        self.api_token = api_token

    async def authorize(self, websocket) -> dict:
        await websocket.send(json.dumps({"authorize": self.api_token}))
        return json.loads(await websocket.recv())

    async def stream_ticks(self, symbol: str) -> AsyncIterator[dict]:
        async with websockets.connect(self.url) as websocket:
            if self.api_token:
                await self.authorize(websocket)
            await websocket.send(json.dumps({"ticks": symbol, "subscribe": 1}))
            async for message in websocket:
                yield json.loads(message)

    async def buy_contract(
        self,
        symbol: str,
        contract_type: str,
        amount: float,
        duration: int,
        currency: str,
        price: float,
    ) -> dict:
        payload = {
            "buy": 1,
            "price": price,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": currency,
                "duration": duration,
                "duration_unit": "t",
                "symbol": symbol,
            },
        }
        async with websockets.connect(self.url) as websocket:
            await self.authorize(websocket)
            await websocket.send(json.dumps(payload))
            return json.loads(await websocket.recv())

    async def get_balance(self) -> dict:
        payload = {"balance": 1, "account": "all"}
        async with websockets.connect(self.url) as websocket:
            await self.authorize(websocket)
            await websocket.send(json.dumps(payload))
            return json.loads(await websocket.recv())

    async def get_open_positions(self) -> dict:
        payload = {"portfolio": 1}
        async with websockets.connect(self.url) as websocket:
            await self.authorize(websocket)
            await websocket.send(json.dumps(payload))
            return json.loads(await websocket.recv())

