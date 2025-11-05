#!/Users/300074702/dev-tools/myenv/bin/python
"""
Cursor API Server - Exposes REST API endpoints to interact with Cursor Agent via CLI
"""

import os
import subprocess
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cursor_api_server.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Cursor API Server",
    description="REST API to interact with Cursor Agent via CLI",
    version="1.0.0"
)

# CORS middleware for web interface access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (can be replaced with Redis/DB for production)
sessions: Dict[str, Dict[str, Any]] = {}

# Default workspace path (can be overridden via environment variable)
DEFAULT_WORKSPACE = os.getenv("CURSOR_WORKSPACE", os.getcwd())


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message/prompt")
    model: Optional[str] = Field("auto", description="Model to use (e.g., 'gpt-4', 'claude-3', 'auto')")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    files: Optional[List[str]] = Field(None, description="List of file paths to reference in the codebase")
    workspace_path: Optional[str] = Field(None, description="Workspace path (defaults to CURSOR_WORKSPACE env var)")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID")
    model: str = Field(..., description="Model used")
    timestamp: str = Field(..., description="Response timestamp")


class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    last_activity: str
    message_count: int
    model: str
    workspace_path: str


class SessionListResponse(BaseModel):
    sessions: List[SessionInfo]


def build_cursor_command(
        prompt: str,
        model: str = "auto",
        workspace_path: Optional[str] = None,
        files: Optional[List[str]] = None
) -> List[str]:
    """
    Build the cursor-agent CLI command with appropriate arguments.
    """
    cmd = ["cursor-agent", "--print"]

    # Add model selection
    if model and model != "auto":
        cmd.extend(["--model", model])

    # Note: workspace is handled via cwd in subprocess.run(), not as a CLI option
    # Note: file references are included in the prompt text, not as CLI options

    # Add the prompt
    cmd.append(prompt)

    return cmd


def find_cursor_agent() -> Optional[str]:
    """
    Find cursor-agent executable in PATH or common locations.
    Returns the full path to cursor-agent if found, None otherwise.
    """
    logger.debug("Searching for cursor-agent executable")
    
    # Try which/whereis first
    try:
        result = subprocess.run(
            ["which", "cursor-agent"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip()
            logger.info(f"Found cursor-agent via 'which': {path}")
            return path
    except Exception as e:
        logger.debug(f"'which' command failed: {e}")
    
    # Try common installation locations
    common_paths = [
        os.path.expanduser("~/.local/bin/cursor-agent"),
        "/usr/local/bin/cursor-agent",
        "/usr/bin/cursor-agent",
    ]
    
    logger.debug(f"Checking common paths: {common_paths}")
    for path in common_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            logger.info(f"Found cursor-agent at: {path}")
            return path
    
    logger.warning("cursor-agent executable not found")
    return None


def execute_cursor_command(cmd: List[str], workspace_path: Optional[str] = None) -> tuple[str, bool]:
    """
    Execute cursor-agent command and return output.
    Returns (output, success) tuple.
    """
    workspace = workspace_path or DEFAULT_WORKSPACE
    logger.info(f"Executing cursor command in workspace: {workspace}")
    logger.debug(f"Command: {' '.join(cmd[:3])}...")  # Log first 3 parts to avoid logging full prompt

    try:
        # Find cursor-agent executable
        cursor_agent_path = find_cursor_agent()
        if not cursor_agent_path:
            error_msg = "cursor-agent CLI not found. Please install it: curl https://cursor.com/install -fsS | bash"
            logger.error(error_msg)
            return error_msg, False
        
        # Replace 'cursor-agent' in command with full path
        if cmd[0] == "cursor-agent":
            cmd[0] = cursor_agent_path

        # Set environment variables
        env = os.environ.copy()
        # Ensure PATH includes common binary locations
        local_bin = os.path.expanduser("~/.local/bin")
        if local_bin not in env.get("PATH", ""):
            env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
        
        api_key_present = "CURSOR_API_KEY" in env
        logger.debug(f"API key present: {api_key_present}")

        # Execute command in the workspace directory
        logger.debug(f"Running cursor-agent with timeout=300s, cwd={workspace}")
        result = subprocess.run(
            cmd,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env
        )

        if result.returncode == 0:
            logger.info(f"Command completed successfully (output length: {len(result.stdout)} chars)")
            return result.stdout, True
        else:
            # Provide detailed error information
            error_output = result.stderr or result.stdout
            error_msg = f"Cursor CLI error (exit code {result.returncode}): {error_output}"
            logger.error(error_msg)
            return error_msg, False

    except subprocess.TimeoutExpired:
        error_msg = "Command timed out after 5 minutes"
        logger.error(error_msg)
        return error_msg, False
    except FileNotFoundError as e:
        # This should rarely happen now since we check for cursor-agent first
        error_msg = f"cursor-agent CLI not found: {str(e)}. Please ensure it's installed and in your PATH."
        logger.error(error_msg)
        return error_msg, False
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg, False


def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get existing session or create a new one."""
    if session_id and session_id in sessions:
        logger.debug(f"Using existing session: {session_id}")
        return session_id

    new_session_id = str(uuid.uuid4())
    logger.info(f"Creating new session: {new_session_id}")
    sessions[new_session_id] = {
        "session_id": new_session_id,
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
        "messages": [],
        "model": "auto",
        "workspace_path": DEFAULT_WORKSPACE
    }
    return new_session_id


def build_contextual_prompt(message: str, session_messages: List[ChatMessage],
                            files: Optional[List[str]] = None,
                            workspace_path: Optional[str] = None) -> str:
    """
    Build a contextual prompt that includes conversation history and file references.
    """
    prompt_parts = []

    # Add file references context
    if files:
        logger.debug(f"Adding {len(files)} file references to prompt")
        prompt_parts.append("=== Referenced Files ===")
        workspace = workspace_path or DEFAULT_WORKSPACE
        for file_path in files:
            # Resolve file path
            full_path = Path(workspace) / file_path if not Path(file_path).is_absolute() else Path(file_path)
            if full_path.exists() and full_path.is_file():
                try:
                    # Read file contents
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.debug(f"Successfully read file: {file_path} ({len(content)} chars)")
                    prompt_parts.append(f"File: {file_path}")
                    prompt_parts.append("```")
                    prompt_parts.append(content)
                    prompt_parts.append("```")
                    prompt_parts.append("")
                except Exception as e:
                    logger.warning(f"Could not read file {file_path}: {e}")
                    prompt_parts.append(f"File: {file_path} (could not read: {str(e)})")
            else:
                logger.warning(f"File not found: {file_path}")
                prompt_parts.append(f"File: {file_path} (not found)")
        prompt_parts.append("")

    # Add conversation history
    if session_messages:
        history_count = min(len(session_messages), 10)
        logger.debug(f"Adding {history_count} conversation history messages to prompt")
        prompt_parts.append("=== Conversation History ===")
        for msg in session_messages[-10:]:  # Last 10 messages for context
            prompt_parts.append(f"{msg.role}: {msg.content}")
        prompt_parts.append("")

    # Add current message
    prompt_parts.append("=== Current Request ===")
    prompt_parts.append(message)

    return "\n".join(prompt_parts)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to Cursor Agent and get a response.
    Maintains conversation context through session_id.
    """
    logger.info(f"Received chat request - session_id: {request.session_id}, model: {request.model}")
    logger.debug(f"Message preview: {request.message[:100]}...")
    
    # Get or create session
    session_id = get_or_create_session(request.session_id)
    session = sessions[session_id]

    # Update session info
    session["last_activity"] = datetime.now().isoformat()
    if request.model and request.model != "auto":
        session["model"] = request.model
        logger.debug(f"Updated session model to: {request.model}")
    if request.workspace_path:
        session["workspace_path"] = request.workspace_path
        logger.debug(f"Updated session workspace to: {request.workspace_path}")

    # Build contextual prompt with conversation history
    contextual_prompt = build_contextual_prompt(
        request.message,
        session["messages"],
        request.files,
        session["workspace_path"]
    )

    # Build command
    cmd = build_cursor_command(
        prompt=contextual_prompt,
        model=session["model"],
        workspace_path=session["workspace_path"],
        files=request.files
    )

    # Execute command
    output, success = execute_cursor_command(cmd, session["workspace_path"])

    if not success:
        logger.error(f"Chat request failed for session {session_id}: {output}")
        raise HTTPException(status_code=500, detail=output)

    # Store messages in session
    session["messages"].append(ChatMessage(role="user", content=request.message))
    session["messages"].append(ChatMessage(role="assistant", content=output))
    
    logger.info(f"Chat request completed successfully - session: {session_id}, messages: {len(session['messages'])}")

    return ChatResponse(
        response=output,
        session_id=session_id,
        model=session["model"],
        timestamp=datetime.now().isoformat()
    )


@app.get("/api/sessions", response_model=SessionListResponse)
async def list_sessions():
    """List all active sessions."""
    logger.info(f"Listing sessions - total count: {len(sessions)}")
    session_list = []
    for session_id, session_data in sessions.items():
        session_list.append(SessionInfo(
            session_id=session_data["session_id"],
            created_at=session_data["created_at"],
            last_activity=session_data["last_activity"],
            message_count=len(session_data["messages"]),
            model=session_data["model"],
            workspace_path=session_data["workspace_path"]
        ))

    return SessionListResponse(sessions=session_list)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details and conversation history."""
    logger.info(f"Getting session details: {session_id}")
    if session_id not in sessions:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    logger.debug(f"Returning session {session_id} with {len(session['messages'])} messages")
    return {
        "session_id": session["session_id"],
        "created_at": session["created_at"],
        "last_activity": session["last_activity"],
        "messages": [{"role": msg.role, "content": msg.content} for msg in session["messages"]],
        "model": session["model"],
        "workspace_path": session["workspace_path"]
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    logger.info(f"Deleting session: {session_id}")
    if session_id not in sessions:
        logger.warning(f"Session not found for deletion: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    del sessions[session_id]
    logger.info(f"Session deleted successfully: {session_id}")
    return {"message": "Session deleted successfully"}


@app.get("/api/models")
async def list_models():
    """List available models (can be extended to query Cursor CLI)."""
    return {
        "models": [
            "auto",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
            "grok-code-fast-1",
            "gemini-2.5-flash"
        ],
        "default": "auto"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
    cursor_available = False
    cursor_path = find_cursor_agent()
    
    if cursor_path:
        try:
            result = subprocess.run(
                [cursor_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            cursor_available = result.returncode == 0
            if cursor_available:
                logger.debug(f"cursor-agent is available: {cursor_path}")
        except Exception as e:
            logger.warning(f"Failed to check cursor-agent version: {e}")

    status = "healthy" if cursor_available else "degraded"
    logger.info(f"Health check status: {status}, sessions: {len(sessions)}")
    
    return {
        "status": status,
        "cursor_cli_available": cursor_available,
        "cursor_cli_path": cursor_path if cursor_available else None,
        "sessions_count": len(sessions),
        "workspace": DEFAULT_WORKSPACE
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Cursor API Server",
        "version": "1.0.0",
        "endpoints": {
            "chat": "POST /api/chat",
            "sessions": "GET /api/sessions",
            "session": "GET /api/sessions/{session_id}",
            "delete_session": "DELETE /api/sessions/{session_id}",
            "models": "GET /api/models",
            "health": "GET /api/health",
            "docs": "GET /docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    import socket

    port = int(os.getenv("PORT", 9000))
    host = os.getenv("HOST", "0.0.0.0")

    # Check if port is available
    def is_port_available(host: str, port: int) -> bool:
        """Check if a port is available for binding."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return True
            except OSError:
                return False

    if not is_port_available(host, port):
        error_msg = f"Port {port} is already in use"
        logger.error(error_msg)
        print(f"❌ ERROR: {error_msg}!")
        print(f"\nTo fix this, you can:")
        print(f"  1. Stop the process using port {port}")
        print(f"  2. Use a different port by setting PORT environment variable:")
        print(f"     export PORT=9000  # or another available port")
        print(f"  3. Or update your .env file with: PORT=9000")
        print(f"\nTo find what's using port {port}:")
        print(f"  lsof -i :{port}")
        exit(1)

    logger.info(f"Starting Cursor API Server on {host}:{port}")
    logger.info(f"Workspace: {DEFAULT_WORKSPACE}")
    logger.info(f"API Key set: {'CURSOR_API_KEY' in os.environ}")
    
    print(f"Starting Cursor API Server on {host}:{port}")
    print(f"Workspace: {DEFAULT_WORKSPACE}")
    print(f"API Key set: {'CURSOR_API_KEY' in os.environ}")
    print(f"API Documentation: http://{host}:{port}/docs")
    print()

    try:
        uvicorn.run(app, host=host, port=port)
    except OSError as e:
        if "address already in use" in str(e).lower():
            logger.error(f"Port {port} is already in use")
            print(f"\n❌ ERROR: Port {port} is already in use!")
            print(f"Please use a different port or stop the process using port {port}")
            exit(1)
        else:
            logger.error(f"Failed to start server: {e}", exc_info=True)
            raise