# Cursor API Server

A Python REST API server that exposes Cursor Agent functionality via HTTP endpoints.

## Setup

### Quick Setup (Using setup script)

1. Make the setup script executable:
   ```bash
   chmod +x setup.sh
   ```

2. Run the setup script:
   ```bash
   ./setup.sh
   ```

### Manual Setup

1. Activate your virtual environment:
   ```bash
   source ~/dev-tools/myenv/bin/activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Cursor CLI (if not already installed):
   ```bash
   curl https://cursor.com/install -fsS | bash
   ```

4. Get your Cursor API key:
   - Visit [Cursor Settings](https://cursor.com/dashboard?tab=integrations) in your web browser
   - Sign in to your Cursor account if you haven't already
   - Navigate to the API Keys section
   - Generate a new API key or copy an existing one
   - Keep this key secure and don't share it publicly
   - **Note**: The API key is required for the server to communicate with Cursor Agent

5. Set up environment variables:

   **Option A: Using .env file (recommended)**

   Create a `.env` file in the project root (you can copy from `.env.example` if it exists). Replace `your_api_key_here` with your actual Cursor API key obtained from step 4:
   ```bash
   # Create .env file
   cat > .env << 'EOF'
   CURSOR_API_KEY=your_api_key_here
   CURSOR_WORKSPACE=/path/to/your/project
   PORT=9000
   HOST=0.0.0.0
   EOF
   ```

   Or manually create `.env` with:
   ```
   CURSOR_API_KEY=your_api_key_here
   CURSOR_WORKSPACE=/path/to/your/project
   PORT=9000
   HOST=0.0.0.0
   ```

   The application will automatically load variables from `.env` file on startup.

   **Option B: Export environment variables**

   Replace `your_api_key_here` with your actual Cursor API key obtained from step 4:
   ```bash
   export CURSOR_API_KEY=your_api_key_here
   export CURSOR_WORKSPACE=/path/to/your/project  # Optional
   export PORT=9000  # Optional, default is 9000
   export HOST=0.0.0.0  # Optional, default is 0.0.0.0
   ```

6. Run the server:

   **Option A: Using the run script (recommended)**
   ```bash
   ./run.sh
   ```
   
   **Option B: Direct execution (shebang points to virtual env)**
   ```bash
   ./main.py
   ```
   
   **Option C: Manual activation**
   ```bash
   source ~/dev-tools/myenv/bin/activate
   python main.py
   ```

The API will be available at `http://localhost:9000` with interactive docs at `http://localhost:9000/docs`.

## API Endpoints

### POST /api/chat
Send a message to Cursor Agent.

**Request Body:**
{
  "message": "Explain this code",
  "model": "auto",
  "session_id": "optional-session-id",
  "files": ["src/main/java/Example.java"],
  "workspace_path": "/path/to/project"
}**Response:**
{
  "response": "Agent response...",
  "session_id": "uuid",
  "model": "gpt-4",
  "timestamp": "2024-01-01T12:00:00"
}### GET /api/sessions
List all active conversation sessions.

### GET /api/sessions/{session_id}
Get session details and conversation history.

### DELETE /api/sessions/{session_id}
Delete a session.

### GET /api/models
List available models.

### GET /api/health
Health check endpoint.

## Example Usage

### Using curl:sh
# Create a new chat session
curl -X POST http://localhost:9000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain this codebase",
    "model": "auto",
    "files": ["pom.xml"]
  }'

# Continue conversation with session_id
curl -X POST http://localhost:9000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How does sharding work?",
    "session_id": "your-session-id"
  }'### Using Python:
import requests

response = requests.post("http://localhost:9000/api/chat", json={
    "message": "Explain this codebase",
    "model": "gpt-4",
    "files": ["pom.xml", "src/main/java/..."]
})

data = response.json()
print(f"Response: {data['response']}")
print(f"Session ID: {data['session_id']}")## Features

- ✅ Model selection (auto, gpt-4, claude-3, etc.)
- ✅ Conversation session management
- ✅ File/codebase references
- ✅ Conversation history context
- ✅ RESTful API with auto-generated docs
- ✅ CORS support for web interfaces