# Buddy - Your Social Life Coach 🐕

A RAG-enabled voice agent built with LiveKit that helps you discover local events and get out more. Buddy is a talking golden retriever with a mission: to cure your hermit tendencies and get you socializing in San Francisco.

## 🎯 The Story

Meet Buddy, a golden retriever who mysteriously gained the ability to speak. Instead of using his newfound power for world domination, he decided to tackle a more personal mission: getting his owner off the couch and into the San Francisco social scene.

**Why This Agent?**

As someone who recently wrapped up a startup, I've spent too many evenings coding alone with just my dog for company. Buddy is designed to solve a real problem in my life - finding interesting local events without the friction of manual searching. He knows San Francisco and can search for live events in real-time.

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────┐
│  React Frontend │
│  (Next.js)      │
└────────┬────────┘
         │ WebRTC
         ↓
┌─────────────────────────────────────────┐
│         LiveKit Server                  │
│  (Voice/Video Orchestration)            │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│      Python Backend (LiveKit Agent)     │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Voice Pipeline                  │  │
│  │  • AssemblyAI (STT)             │  │
│  │  • OpenAI GPT-4.1 (LLM)         │  │
│  │  • ElevenLabs (TTS)             │  │
│  │  • Silero (VAD)                 │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  RAG System (ChromaDB)          │  │
│  │  • Buddy's personality & prefs   │  │
│  │  • SF knowledge                  │  │
│  │  • Semantic search               │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Tool Integration               │  │
│  │  • Linkup API (event search)    │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Component Breakdown

#### 1. **Frontend (React + Next.js)**
- Real-time transcript display
- Call controls (start/end)
- WebRTC connection via LiveKit client SDK
- Located in `frontenddiy/` directory

#### 2. **Backend (Python + LiveKit Agents)**
- **Voice Pipeline**: STT → LLM → TTS with voice activity detection
- **Agent Logic**: Buddy's personality, tool calling, RAG integration
- **Location**: `buddy/` directory

#### 3. **RAG System (ChromaDB)**
- Vector store for Buddy's knowledge base
- Contains personality traits, SF recommendations, and backstory
- Semantic search for contextually relevant information retrieval

#### 4. **External APIs**
- **Linkup**: Real-time search API for event discovery
- **AssemblyAI**: Speech-to-text transcription
- **OpenAI**: GPT-4.1-nano for conversational intelligence
- **ElevenLabs**: High-quality text-to-speech synthesis

## 🧠 RAG Integration Details

### Document Structure

Buddy's knowledge base is stored in `data/All_about_buddy.pdf` and contains:
- **Personality traits**: Enthusiastic, protective, slightly guilt-trippy
- **Preferences**: Outdoor events, food festivals, live music
- **San Francisco knowledge**: Neighborhood recommendations, event venues
- **Backstory**: How Buddy gained the ability to speak

### Chunking Strategy

Located in `scripts/setup_vector_store.py`:

```python
chunk_size = 800 characters
overlap = 100 characters
```

**Why these parameters?**

- **800 chars**: Balances context preservation with retrieval precision. Too small loses coherence; too large reduces specificity.
- **100 char overlap**: Ensures concepts split across chunks remain connected. Critical for maintaining conversational flow when Buddy references his backstory.
- **Sentence boundary detection**: Chunks break at sentence endings when possible to avoid mid-sentence cuts that confuse semantic meaning.

### Retrieval Process

Located in `buddy/rag.py`:

```python
top_k = 3  # Retrieve top 3 most relevant chunks
embedding_model = ChromaDB default (all-MiniLM-L6-v2)
```

**Flow:**
1. User speaks → Speech transcribed to text
2. User message sent to `on_user_turn_completed()` hook
3. RAG retrieval: Query ChromaDB with user's message
4. Top 3 semantically similar chunks returned
5. Chunks injected into conversation context as system message
6. LLM generates response using RAG context + personality prompt

**Key Design Decision:** RAG context is added as an *assistant message* rather than modifying the system prompt. This allows:
- Dynamic context injection per turn
- Conversation history preserved cleanly
- No prompt bloat from unused knowledge

## 🛠️ Tool Integration

### `find_nearby_events` Tool

Located in `buddy/tools.py`:

**Purpose**: Search for real-time events in San Francisco using Linkup API

**Key Features:**
- Single search returns multiple diverse results (no need for multiple calls)
- Async status updates ("Hang on, let me sniff around...")
- Comprehensive error handling with user-friendly messages
- Detailed logging for debugging

**API Choice: Why Linkup?**

Linkup provides:
- Search results across multiple event websites (vs. single source like Eventbrite API)
- Rich content snippets for Buddy to present naturally
- Simple REST API (just API key, no OAuth complexity)


## 🚀 Setup Instructions

### Prerequisites

- Python 3.12+
- Node.js 18+
- Poetry (Python dependency management)
- API Keys (see below)

### 1. Clone and Install Backend

```bash
cd buddy
poetry install

# Download LiveKit models (required!)
poetry run python buddy/main.py download-files

# Setup vector store
poetry run python scripts/setup_vector_store.py
```

### 2. Configure Backend Environment

Create `buddy/.env`:

```properties
ELEVEN_API_KEY=your_elevenlabs_key
OPENAI_API_KEY=your_openai_key
ASSEMBLYAI_API_KEY=your_assemblyai_key
LIVEKIT_API_KEY=your_livekit_key
LIVEKIT_API_SECRET=your_livekit_secret
LIVEKIT_URL=ws://your-livekit-server.com
LINKUP_API_KEY=your_linkup_key
```

### 3. Install Frontend

```bash
cd frontenddiy
npm install
```

### 4. Configure Frontend Environment

Create `frontenddiy/.env`:

```properties
LIVEKIT_API_KEY=your_livekit_key
LIVEKIT_API_SECRET=your_livekit_secret
LIVEKIT_URL=ws://your-livekit-server.com
```

(Same LiveKit credentials as backend)

### 5. Run the Application

**Terminal 1 - Backend:**
```bash
cd buddy
poetry run python buddy/main.py dev
```

**Terminal 2 - Frontend:**
```bash
cd frontenddiy
npm run dev
```

**Terminal 3 - LiveKit Server (if local):**
```bash
livekit-server --dev
```

### 6. Access the App

Open http://localhost:3000 in your browser and click "Start Call" to chat with Buddy!

## 🎨 Design Decisions & Trade-offs

### 1. **STT Provider: AssemblyAI**

**Decision**: Use AssemblyAI for speech-to-text

**Rationale:**
- Cost-effective pricing for voice transcription
- Simple LiveKit integration (works out of the box with LiveKit agents)
- Reliable transcription quality for conversational voice


### 2. **LLM: GPT-4.1-nano (Not GPT-5-nano)**

**Decision**: Use GPT-4.1-nano for the language model

**Rationale:**
- Fast response times crucial for voice conversations
- Lower cost for high-volume usage
- Sufficient intelligence for conversational agent

**Trade-off - Why not GPT-5-nano?** Initially tried GPT-5-nano despite OpenAI documentation claiming it's "the fastest ever," but inference was taking 9+ seconds at times. Multiple users on Reddit forums reported the same issue. Switched to GPT-4.1-nano which is actually faster in practice.

**Alternative Considered:** Initially used LiveKit's cross-provider "inference" API for flexibility, but quickly hit free token limits. Switched to direct provider APIs (minimal code change, better control).

### 3. **TTS: ElevenLabs**

**Decision**: Use ElevenLabs for text-to-speech

**Rationale:**
- Have used ElevenLabs before and familiar with their API
- High-quality, natural-sounding voices that work well for character personalities
- Good voice variety and expressiveness
- Reliable performance

**Trade-off:** One more API dependency and cost, but voice quality is worth it for a character-driven agent like Buddy

### 4. **Chunking Strategy: 800 chars with 100 overlap**

**Decision**: Fixed-size chunks with sentence boundary detection

**Alternatives Considered:**
- Semantic chunking (split by topics)
- Paragraph-based chunking
- Smaller chunks (400 chars)

**Rationale:**
- 800 chars captures complete thoughts without excessive context
- Sentence boundaries prevent mid-thought cuts
- Overlap ensures no information lost at edges
- Simple and predictable behavior

**Trade-off:** Not optimal for all content types, but works well for Buddy's narrative-heavy PDF

### 5. **Vector Store: ChromaDB**

**Decision**: Use ChromaDB with local persistence

**Rationale:**
- Have used ChromaDB before for local-only RAG applications
- Super simple to setup and use
- Has built-in embedding model (all-MiniLM-L6-v2) - no API credits needed
- Zero external dependencies
- Fast local queries (<50ms)
- Perfect for demo/take-home project

**Trade-off:** Not production-scalable for multi-user scenarios, but ideal for single-user agent and eliminates embedding API costs

### 6. **Event Search: Linkup API**

**Decision**: Use Linkup API for event discovery

**Rationale:**
- Aggregates results across multiple event websites (Eventbrite, local event sites, etc.)
- Simpler than managing multiple individual APIs
- Good temporal understanding ("tonight", "this weekend")
- API key authentication (no OAuth complexity)


### 7. **Frontend: Next.js**

**Decision**: Use Next.js framework

**Rationale:**
- Familiar with Next.js from previous projects
- App Router is simple and intuitive

**Trade-off:** Slight overkill for this simple UI, but leverages existing knowledge and sets up well for potential future enhancements


## 🧪 Testing the RAG System

### Testing Buddy's Knowledge

Try these prompts to see RAG in action:

1. **"Tell me about yourself"** 
   - Should retrieve backstory chunks about how Buddy learned to speak

2. **"What kind of events do you think I'd like?"**
   - Should retrieve personality/preference chunks and make recommendations

3. **"Why are you so obsessed with getting me out of the house?"**
   - Should retrieve Buddy's mission statement and concerns about your social life

4. **"Do you have any interesting stories to tell?"**
   - Should retrieve some stories


## 📁 Project Structure

```
buddy-event-voice-agent/
├── buddy/                          # Python backend
│   ├── __init__.py
│   ├── main.py                    # Agent entrypoint & pipeline
│   ├── prompts.py                 # Buddy's personality prompt
│   ├── tools.py                   # Event search tool
│   ├── rag.py                     # RAG retrieval system
│   └── .env                       # Backend API keys
├── data/
│   └── All_about_buddy.pdf        # Buddy's knowledge base
├── chroma_db/                     # Vector store (generated)
├── scripts/
│   ├── setup_vector_store.py     # One-time RAG setup
│   └── test_rag.py               # RAG testing script
├── frontenddiy/                   # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   └── hooks/
│   ├── .env                      # Frontend config
│   └── package.json
├── pyproject.toml                # Python dependencies
└── README.md                     # This file
```

## 🎯 Future Enhancements

If I had more time, I'd add:

1. **Memory Persistence**: Save conversation history to remember past conversations
2. **Multi-user Support**: Deploy on LiveKit Cloud for multiple users
3. **Advanced RAG**: Implement hybrid search (semantic + keyword) for better retrieval
4. **Voice Customization**: Find a better voice model that sounds more dog-like
5. **3d Avater**: Use a 3d puppet avatar for Buddy on the frontend

## 📝 Development Notes

### AI Tooling Used

This project was developed with assistance from:
- **Claude (Anthropic)**: Code architecture, debugging, documentation, writing Buddy's knowledge base.
- **Windsurf**: Exploring and understanding how the livekit default frontend interacted with the server.

All AI suggestions were reviewed, tested, and modified for production quality.

## 🙏 Acknowledgments

- **LiveKit**: Excellent real-time voice infrastructure and agent framework
- **BlueJay Team**: For prompting me to build this creative and technically engaging challenge

## 📧 Contact

Alan Bohannon  
alanbohannon@gmail.com

---

Built with 🐾 by a guy who really does need to get out more