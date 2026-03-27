# AMANDLA Desktop — Quick Start Guide

**Last Updated**: March 24, 2026

---

## ⚡ 30-Second Startup

### Terminal 1: Backend
```powershell
cd C:\Users\Admin\amandla-desktop
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Ollama (if needed)
```powershell
ollama serve
```

### Terminal 3: Electron App
```powershell
cd C:\Users\Admin\amandla-desktop
npm start
```

**Wait for**: Split-screen Electron window with two panes.

---

## 🧪 Test It (1 minute)

1. **Hearing window** (left): Type "Hello, how are you?"
2. **Click Send**
3. **Deaf window** (right): Should display the message
4. **Open DevTools** (F12): Check console for WebSocket messages

Expected console output:
```
[AMANDLA] WebSocket connected: session=amandla-... role=hearing
Recv: {"type":"signs","signs":["HELLO","HOW ARE YOU"],...}
```

---

## 📋 What's Running

| Service | Port | Status |
|---------|------|--------|
| FastAPI Backend | 8000 | ✅ Health check: `http://localhost:8000/health` |
| Ollama LLM | 11434 | ✅ Models: `ollama list` |
| Electron App | — | ✅ Split-screen UI |

---

## 🔧 Development Workflow

### Add a New Message Type

1. **Backend** (`backend/main.py`):
   ```python
   if msg.get('type') == 'my_type':
       # Process here
       await websocket.send_json({'type': 'response', 'data': result})
   ```

2. **Frontend** (hearing or deaf window):
   ```javascript
   window.amandla.onMessage(msg => {
     if (msg.type === 'response') {
       console.log('Received:', msg.data)
     }
   })
   
   // Send it
   window.amandla.send({type: 'my_type', data: 'example'})
   ```

### Fix Avatar Animation

1. Check `src/windows/deaf/avatar.js`
2. Add console logs to `playNext()` function
3. Test with hardcoded sign array: `window.avatarPlaySigns(['HELLO', 'GOODBYE'])`

### Integrate Whisper (Speech→Text)

1. Create `POST /speech` endpoint in `backend/main.py`
2. Use `whisper_service.transcribe_audio()` from `backend/services/whisper_service.py`
3. Return `{"text": "...", "confidence": 0.9}`

---

## 📊 Architecture Overview

```
User speaks/types (Hearing)
    ↓
Electron window sends via WebSocket
    ↓
FastAPI backend processes:
  • Speech → Whisper → Text
  • Text → Signs (via sentence_to_sign_names)
    ↓
Backend broadcasts signs to Deaf window
    ↓
Avatar animates sign sequence
    ↓
TTS reads to blind users (optional)
```

---

## 🐛 Debug Tips

### See all WebSocket messages
```javascript
// In DevTools console:
window.amandla.onMessage(msg => console.log('[WS]', msg))
```

### Check backend logs
Watch the terminal running `uvicorn` — it shows all connections and errors.

### Test WebSocket directly
```powershell
# From scripts/ws_test.py (if available)
python scripts/ws_test.py demo hearing
```

### Mock a sign array
```javascript
// In Deaf window DevTools console:
window.avatarPlaySigns(['HELLO', 'HOW ARE YOU', 'I AM FINE'])
```

---

## 📝 Key Files to Edit

| File | Purpose | Edit When |
|------|---------|-----------|
| `backend/main.py` | Server logic | Adding routes, message handlers |
| `src/windows/hearing/index.html` | Speech UI | Changing hearing interface |
| `src/windows/deaf/index.html` | Avatar UI | Changing deaf interface |
| `src/windows/deaf/avatar.js` | Sign animation | Implementing 3D animation |
| `backend/services/whisper_service.py` | Speech-to-text | Tuning Whisper model |
| `src/preload/preload.js` | IPC bridge | Adding new window communications |
| `.env` | Configuration | Changing Whisper model, ports |

---

## 🚀 Common Commands

```powershell
# Restart backend (from terminal running uvicorn, press Ctrl+C, then re-run)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Kill stuck process
Get-Process python | Stop-Process -Force

# Check if port is in use
Get-NetTCPConnection -LocalPort 8000

# Restart Ollama
# (Windows: just re-run 'ollama serve', or restart the app from system tray)

# Run tests (when available)
npm test

# Build executable
npm run build
```

---

## 💡 Common Issues & Fixes

**Issue**: "WebSocket connection failed"
- **Fix**: Check if backend is running (`http://localhost:8000/health`)
- Check Windows Firewall: Allow Python through the firewall

**Issue**: "Ollama not responding"
- **Fix**: Run `ollama serve` in a separate terminal
- Check `http://localhost:11434/api/tags`

**Issue**: "ffmpeg not found" (when using Whisper with audio)
- **Fix**: Run `ffmpeg -version` to verify installation
- Add `C:\Program Files\ffmpeg\bin` to Windows PATH if missing

**Issue**: Avatar not showing signs
- **Fix**: Check browser console for errors
- Ensure signs library is loaded: `console.log(window.AMANDLA_SIGNS)`
- Check if `avatarPlaySigns()` function exists

**Issue**: "Module 'backend.routers' not found"
- **Fix**: Ensure `backend/routers/__init__.py` exists (empty file OK)
- Run from correct directory: `cd C:\Users\Admin\amandla-desktop`

---

## 📚 References

- **Detailed setup**: See `SETUP_COMPLETE.md`
- **AI agent guide**: See `AGENTS.md`
- **Avatar spec**: See `AMANDLA_FINAL_BLUEPRINT.md`
- **Gap fixes**: See `AMANDLA_MISSING_PIECES.md`

---

## ✅ Verification Checklist

Before reporting a bug, check:

- [ ] Backend is running (`http://localhost:8000/health` returns `{"ok":true}`)
- [ ] Ollama is running (`ollama serve` in terminal)
- [ ] Both windows opened side-by-side
- [ ] DevTools console shows WebSocket connection messages
- [ ] You typed a message and clicked Send
- [ ] You waited 1-2 seconds for backend processing
- [ ] You checked the other window for the message

---

**Need help?** Check the terminal output or open DevTools (F12) to see error messages.

Good luck! 🚀

