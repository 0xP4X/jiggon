import json
import httpx
from collections.abc import AsyncIterator

import websockets

class BrokerClient:
    def __init__(self, app_id, api_token: str, account_id: str = "", endpoint: str = "wss://ws.binaryws.com/websockets/v3"):
        self.app_id = app_id
        self.api_token = api_token
        self.account_id = account_id
        self.base_url = f"{endpoint}?app_id={app_id}"

    async def _get_ws_url(self) -> tuple[str, bool]:
        if self.api_token and self.account_id:
            api_token = self.api_token.strip()
            account_id = self.account_id.strip()
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
                            return fetched_url, True
            except Exception as e:
                pass
        return self.base_url, False

    async def authorize(self, websocket) -> dict:
        await websocket.send(json.dumps({"authorize": self.api_token}))
        return json.loads(await websocket.recv())

    async def stream_ticks(self, symbol: str) -> AsyncIterator[dict]:
        ws_url, is_otp = await self._get_ws_url()
        async with websockets.connect(ws_url) as websocket:
            if self.api_token and not is_otp:
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
        ws_url, is_otp = await self._get_ws_url()
        symbol_key = "underlying_symbol" if is_otp else "symbol"
        
        proposal_payload = {
            "proposal": 1,
            "amount": amount,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": currency,
            "duration": duration,
            "duration_unit": "t",
            symbol_key: symbol,
        }
        
        async with websockets.connect(ws_url) as websocket:
            if not is_otp:
                await self.authorize(websocket)
                
            import logging
            logging.basicConfig(filename='client_debug.log', level=logging.DEBUG)
            logging.debug(f"Sending proposal: {json.dumps(proposal_payload)}")
            await websocket.send(json.dumps(proposal_payload))
            prop_res = json.loads(await websocket.recv())
            logging.debug(f"Received proposal: {json.dumps(prop_res)}")
            
            if "error" in prop_res:
                return prop_res
                
            prop_id = prop_res.get("proposal", {}).get("id")
            if not prop_id:
                return {"error": {"message": "Failed to get proposal ID"}}
                
            buy_payload = {
                "buy": prop_id,
                "price": price
            }
            logging.debug(f"Sending buy: {json.dumps(buy_payload)}")
            await websocket.send(json.dumps(buy_payload))
            buy_res = json.loads(await websocket.recv())
            logging.debug(f"Received buy: {json.dumps(buy_res)}")
            return buy_res

    async def get_balance(self) -> dict:
        payload = {"balance": 1}
        ws_url, is_otp = await self._get_ws_url()
        async with websockets.connect(ws_url) as websocket:
            if not is_otp:
                await self.authorize(websocket)
            await websocket.send(json.dumps(payload))
            return json.loads(await websocket.recv())

    async def get_open_positions(self) -> dict:
        payload = {"portfolio": 1}
        ws_url, is_otp = await self._get_ws_url()
        async with websockets.connect(ws_url) as websocket:
            if not is_otp:
                await self.authorize(websocket)
            await websocket.send(json.dumps(payload))
            return json.loads(await websocket.recv())
