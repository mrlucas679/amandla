import asyncio
import json
import websockets
import urllib.request

URI_BASE = 'ws://127.0.0.1:8000/ws'


def _fetch_session_secret():
    """Fetch the session secret from the backend /auth/session-secret endpoint."""
    with urllib.request.urlopen('http://127.0.0.1:8000/auth/session-secret') as resp:
        return json.loads(resp.read().decode())['session_secret']


async def deaf_client():
    token = _fetch_session_secret()
    uri = f"{URI_BASE}/demo/deaf?token={token}"
    async with websockets.connect(uri) as ws:
        print('[Test] Deaf connected')
        try:
            async for msg in ws:
                print('[Test][Deaf] Recv:', msg)
        except Exception as e:
            print('[Test][Deaf] Error:', e)

async def hearing_client():
    # wait a short moment to allow deaf to connect
    await asyncio.sleep(0.5)
    token = _fetch_session_secret()
    uri = f"{URI_BASE}/demo/hearing?token={token}"
    async with websockets.connect(uri) as ws:
        print('[Test] Hearing connected')
        payload = { 'type': 'text', 'text': 'Hello, how are you?', 'sender': 'hearing' }
        await ws.send(json.dumps(payload))
        print('[Test][Hearing] Sent text payload')
        # keep connection alive briefly
        await asyncio.sleep(2.0)

async def main():
    await asyncio.gather(deaf_client(), hearing_client())

if __name__ == '__main__':
    asyncio.run(main())

