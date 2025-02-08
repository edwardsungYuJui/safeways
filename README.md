# Scam Prevention Chat Monitor

Real-time chat monitoring system with AI-powered scam detection using OpenAI. Features parent monitoring interface and dual chat windows for conversation simulation.

# Download LLAMA model
go to https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/tree/main and download a model
Add LLAMA_MODEL_PATH in .env file

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
   LLAMA_MODEL_PATH= "path to the model"
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
