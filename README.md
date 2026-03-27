# 📚 AMANDLA Documentation Index

**Welcome!** This guide helps you navigate the AMANDLA Desktop project documentation.

---

## 🚀 Start Here

### 1️⃣ **Brand New to This Project?**
→ Read: **[QUICKSTART.md](QUICKSTART.md)** (5 minutes)
- 30-second startup instructions
- Quick test procedure
- Common issues & fixes

### 2️⃣ **Want to Understand the Setup?**
→ Read: **[SETUP_COMPLETE.md](SETUP_COMPLETE.md)** (15 minutes)
- What was installed
- How everything is configured
- File structure & architecture

### 3️⃣ **Ready to Start Development?**
→ Read: **[PROJECT_SETUP_SUMMARY.md](PROJECT_SETUP_SUMMARY.md)** (20 minutes)
- Complete project overview
- How to run services
- Development workflow
- Architecture & data flow

### 4️⃣ **Need to Verify Setup?**
→ Read: **[SETUP_VERIFICATION.md](SETUP_VERIFICATION.md)** (10 minutes)
- Verification checklist
- Quick test procedure
- Troubleshooting guide

---

## 📖 Reference Documentation

### Technical Specifications
- **[AGENTS.md](AGENTS.md)** — AI agent coding guidelines (what follows in this project)
- **[AMANDLA_FINAL_BLUEPRINT.md](AMANDLA_FINAL_BLUEPRINT.md)** — Complete avatar.js spec (1571 lines, detailed implementation guide)
- **[AMANDLA_MISSING_PIECES.md](AMANDLA_MISSING_PIECES.md)** — Backend integration gaps and solutions

---

## 🎯 Choose Your Path

### Path 1: I Just Want to Run It
1. Read: **QUICKSTART.md** (5 min)
2. Run: `npm start` (in 3 terminals)
3. Test: Send a message from hearing → deaf window

### Path 2: I Want to Understand It
1. Read: **SETUP_COMPLETE.md** (understand setup)
2. Read: **PROJECT_SETUP_SUMMARY.md** (understand architecture)
3. Read: **AGENTS.md** (understand coding guidelines)
4. Explore: The code files

### Path 3: I Want to Build Features
1. Read: **QUICKSTART.md** (startup)
2. Run: `npm start` (get it working)
3. Read: **AMANDLA_FINAL_BLUEPRINT.md** (for avatar feature)
4. Read: **AMANDLA_MISSING_PIECES.md** (for backend features)
5. Code: Implement your feature

### Path 4: Something's Broken
1. Check: **SETUP_VERIFICATION.md** → Troubleshooting section
2. Check: **QUICKSTART.md** → Common Issues
3. Check: Console logs (F12 in Electron, terminal for backend)
4. Check: The error message in detail

---

## 📋 Documentation Overview

| Document | Purpose | Read Time | Best For |
|----------|---------|-----------|----------|
| **QUICKSTART.md** | 30-second startup | 5 min | Running the app immediately |
| **SETUP_COMPLETE.md** | Detailed setup breakdown | 15 min | Understanding what's installed |
| **PROJECT_SETUP_SUMMARY.md** | Complete project overview | 20 min | Full project understanding |
| **SETUP_VERIFICATION.md** | Verification checklist | 10 min | Confirming setup is correct |
| **AGENTS.md** | AI coding guidelines | 10 min | Writing code that matches style |
| **AMANDLA_FINAL_BLUEPRINT.md** | Avatar specification | 30 min | Implementing 3D animation |
| **AMANDLA_MISSING_PIECES.md** | Backend integration | 30 min | Building backend features |

---

## 🔍 Quick Lookup

### "How do I start the app?"
→ **QUICKSTART.md** → "30-Second Startup"

### "What files do I edit?"
→ **PROJECT_SETUP_SUMMARY.md** → "Key Files to Edit"

### "How does communication work?"
→ **PROJECT_SETUP_SUMMARY.md** → "Architecture & Data Flow"

### "What's this WebSocket thing?"
→ **SETUP_COMPLETE.md** → "WebSocket Communication Pipeline"

### "How do I implement the avatar?"
→ **AMANDLA_FINAL_BLUEPRINT.md** → Complete spec with code template

### "How do I integrate Whisper?"
→ **AMANDLA_MISSING_PIECES.md** → Gap 5 section

### "Something's not working"
→ **SETUP_VERIFICATION.md** → "Troubleshooting Checklist"

### "What are the coding standards?"
→ **AGENTS.md** → "Project-Specific Conventions"

---

## 🚦 Reading Recommendation Order

### First Time (1 hour total)
1. **QUICKSTART.md** (5 min) — Get it running
2. **SETUP_COMPLETE.md** (15 min) — Understand setup
3. **AGENTS.md** (10 min) — Learn coding style
4. **PROJECT_SETUP_SUMMARY.md** (30 min) — Deep dive

### Before Development (30 min)
1. **AGENTS.md** — Coding guidelines
2. **AMANDLA_FINAL_BLUEPRINT.md** or **AMANDLA_MISSING_PIECES.md** — For your specific feature
3. Jump to code

### When Debugging (varies)
1. **SETUP_VERIFICATION.md** → Troubleshooting section
2. **QUICKSTART.md** → Common Issues
3. Check terminal output / DevTools console

---

## 📞 Support Resources by Topic

### Backend Development
- Backend setup: **SETUP_COMPLETE.md** → Backend section
- Backend architecture: **PROJECT_SETUP_SUMMARY.md** → "Architecture Overview"
- Whisper integration: **AMANDLA_MISSING_PIECES.md** → Gap 5
- WebSocket patterns: **AMANDLA_MISSING_PIECES.md** → Gap 4

### Frontend Development
- Frontend setup: **SETUP_COMPLETE.md** → Frontend section
- Frontend architecture: **PROJECT_SETUP_SUMMARY.md** → "Architecture Overview"
- Window communication: **AGENTS.md** → "Critical Communication Pattern"
- Avatar implementation: **AMANDLA_FINAL_BLUEPRINT.md**

### Issues & Troubleshooting
- Quick fixes: **QUICKSTART.md** → Common Issues
- Detailed troubleshooting: **SETUP_VERIFICATION.md** → Troubleshooting Checklist
- Setup verification: **SETUP_VERIFICATION.md** → Verification Tests

### Architecture & Design
- Overall architecture: **PROJECT_SETUP_SUMMARY.md** → "Architecture & Data Flow"
- Data flow: **PROJECT_SETUP_SUMMARY.md** → "User Journey"
- Communication: **AGENTS.md** → "Critical Communication Pattern"
- Constraints: **AGENTS.md** → "Project Overview"

---

## 🎓 Learning Path by Skill Level

### Beginner
1. Start with: **QUICKSTART.md**
2. Then read: **SETUP_COMPLETE.md**
3. Focus on: Getting app to run, testing basic communication
4. Keep nearby: **SETUP_VERIFICATION.md** for troubleshooting

### Intermediate
1. Read: **PROJECT_SETUP_SUMMARY.md**
2. Read: **AGENTS.md**
3. Review: Architecture in PROJECT_SETUP_SUMMARY.md
4. Explore: The code files, especially backend/main.py

### Advanced
1. Read: **AMANDLA_FINAL_BLUEPRINT.md** (for specific feature)
2. Read: **AMANDLA_MISSING_PIECES.md** (for integration details)
3. Read: **AGENTS.md** (for conventions)
4. Code: Implement your feature with specification as reference

---

## ⚡ Quick Commands

```powershell
# Start development
npm start

# Start just backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Start just Ollama
ollama serve

# Check backend health
curl http://localhost:8000/health

# Check Ollama models
ollama list

# Verify dependencies
npm list
pip list | grep fastapi
```

---

## 📌 Key Concepts to Understand

### Session ID
- Unique identifier for a conversation between hearing and deaf users
- Generated by Electron main process
- Shared with both windows via IPC
- Used in WebSocket URL: `ws://localhost:8000/ws/{sessionId}/{role}`

### WebSocket
- Two-way communication between browser and server
- Used to send messages from hearing window to deaf window
- Auto-reconnects if connection drops
- Not HTTP — persistent connection

### Whisper
- Speech-to-text engine (local, no API key needed)
- Converts audio file (WAV) to text
- Runs on CPU (~3-5s per 10s) or GPU (much faster)
- Part of FastAPI backend

### Ollama
- Local LLM server (runs models locally)
- The `amandla` model recognizes SASL signs
- Accessible at port 11434
- Used by backend for sign language recognition

### Avatar
- 3D character that animates signs
- Not yet implemented (template provided)
- Will be Three.js-based
- Consumes sign queue from backend

---

## ✅ Before You Code

1. [ ] Read **AGENTS.md** for project conventions
2. [ ] Run `npm start` and verify both windows open
3. [ ] Send a test message from hearing → deaf
4. [ ] Check browser DevTools (F12) for WebSocket logs
5. [ ] Read the specific feature doc (**AMANDLA_FINAL_BLUEPRINT.md** or **AMANDLA_MISSING_PIECES.md**)

---

## 🆘 I'm Stuck

1. **Check the docs**: Use the lookup table above
2. **Check troubleshooting**: **SETUP_VERIFICATION.md** has common issues
3. **Check the logs**: 
   - Frontend: Open F12 in Electron window
   - Backend: Watch the terminal running `uvicorn`
4. **Verify setup**: Run the quick test in **SETUP_VERIFICATION.md**

---

## 📬 Document Files Location

All documents are in the root directory of the project:
- `C:\Users\Admin\amandla-desktop\QUICKSTART.md`
- `C:\Users\Admin\amandla-desktop\SETUP_COMPLETE.md`
- `C:\Users\Admin\amandla-desktop\PROJECT_SETUP_SUMMARY.md`
- `C:\Users\Admin\amandla-desktop\SETUP_VERIFICATION.md`
- `C:\Users\Admin\amandla-desktop\AGENTS.md`
- `C:\Users\Admin\amandla-desktop\AMANDLA_FINAL_BLUEPRINT.md`
- `C:\Users\Admin\amandla-desktop\AMANDLA_MISSING_PIECES.md`

---

## 🎯 Success Checklist

Before considering setup complete:

- [ ] `npm start` launches without errors
- [ ] Both windows open side-by-side
- [ ] DevTools shows WebSocket connected
- [ ] Message sent from hearing → appears in deaf window
- [ ] Terminal shows no Python errors
- [ ] Backend responds to `/health` check
- [ ] Ollama lists amandla model

---

**Happy coding!** 🚀

Start with **[QUICKSTART.md](QUICKSTART.md)** if you haven't already!

---

*Last Updated: March 24, 2026*  
*Status: Setup Complete ✅*

