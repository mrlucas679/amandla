import asyncio
import json
import websockets

URI_BASE = 'ws://127.0.0.1:8000/ws'

async def deaf_client():
    uri = f"{URI_BASE}/demo/deaf"
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
    uri = f"{URI_BASE}/demo/hearing"
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

