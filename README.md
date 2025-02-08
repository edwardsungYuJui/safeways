# Scam Prevention Chat Monitor

Real-time chat monitoring system with AI-powered scam detection using OpenAI. Features parent monitoring interface and dual chat windows for conversation simulation.

# Download OLLAMA
go to [text](https://ollama.com/download) and download ollama
Activate ollama
In your terminal, run `ollama pull <model_name>"

## Quick Start

1. **Setup Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure OpenAI**
   Link: https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/tree/main
   - Create `.env` file:
   ```
   OPENAI_API_KEY=""
   LLAMA_MODEL_PATH=""
   EMAIL_API_KEY=""
   PHONE_API_KEY=""
   SAFE_BROWSING_API_KEY=""
   NUMVERIFY_PHONE_API_KEY=""
   TRESTLE_PHONE_API_KEY=""
   ABSTRACT_PHONE_API_KEY=""
   ```

3. **Run Application**
   ```bash
   python start.py
   ```

   To run the client, run the following command:
   ```bash
   cd client
   python messenger_chat.py
   ```

   To run the server, run the following command:
   ```bash
   python server.py
   ```

## Features
- Real-time chat monitoring
- AI scam detection
- Parent monitoring interface
- Dual chat windows
- Detailed logging system
