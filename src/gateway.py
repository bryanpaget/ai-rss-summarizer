"""Unified gateway interface for local LLM requests.

ALL local LLM requests (text, embedding, vision) MUST go through this module.
The gateway handles model loading, batching, and queue management automatically.

Architecture principle: Submit requests to the gateway, gateway handles model switching.
DO NOT make direct API calls to LM Studio/Ollama - use the gateway.

For batched operations, submit all requests first (async), then collect responses.
This allows the gateway's queue reorganization to batch by type efficiently.
"""

import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class GatewayError(Exception):
    """Raised when gateway operations fail."""
    pass


class GatewayUnavailableError(GatewayError):
    """Raised when gateway script is not available."""
    pass


@dataclass
class GatewayResponse:
    """Response from a gateway request."""
    content: str  # For text: the generated text. For embedding: JSON string
    request_type: str
    response_path: str


class LocalLLMGateway:
    """Unified interface to the safe-model-load gateway.

    All local LLM requests (text, embedding, vision) go through this gateway.
    The gateway handles:
    - Automatic model loading based on request type
    - Queue management and batching by type
    - Prevention of model switching during in-flight requests

    Usage:
        gateway = LocalLLMGateway()

        # Single request (blocking)
        response = gateway.request_text("Summarize this article...")

        # Batch requests (submit all, then collect)
        handles = []
        for prompt in prompts:
            handles.append(gateway.submit_text(prompt))  # Non-blocking
        responses = gateway.collect_all(handles)  # Wait for all
    """

    # Git Bash path for Windows
    GIT_BASH = "C:/Program Files/Git/usr/bin/bash.exe"

    def __init__(self, timeout: int = 120):
        """Initialize gateway interface.

        Args:
            timeout: Maximum seconds to wait for a response
        """
        self.timeout = timeout
        self._gateway_path = self._find_gateway()
        # IPC directory for queue monitoring (matches safe-model-load.sh)
        self._ipc_dir = Path.home() / '.claude' / 'ipc'

    def _find_gateway(self) -> str:
        """Find the gateway script path.

        ONLY looks in project/scripts - NO FALLBACKS.
        Fallbacks hide incompetence by making broken code appear to work.
        If the project copy is missing, this MUST fail loudly.
        """
        # Project-local path ONLY (for portability - works on any machine)
        project_root = Path(__file__).parent.parent
        project_script = project_root / 'scripts' / 'safe-model-load.sh'

        if project_script.exists():
            return str(project_script)

        # NO FALLBACK - fail loudly so the problem is visible
        raise GatewayUnavailableError(
            f"Gateway script not found at: {project_script}\n\n"
            "This project requires scripts/safe-model-load.sh to exist.\n"
            "The script MUST be in the project directory for portability.\n"
            "NO FALLBACKS - if this file is missing, the project is broken.\n\n"
            "To fix: Copy the gateway script to scripts/safe-model-load.sh"
        )

    def _win_to_msys_path(self, win_path: str) -> str:
        """Convert Windows path to MSYS2 path for Git Bash."""
        if os.name != 'nt':
            return win_path
        # C:\Users\... -> /c/Users/...
        if len(win_path) >= 2 and win_path[1] == ':':
            return '/' + win_path[0].lower() + win_path[2:].replace('\\', '/')
        return win_path.replace('\\', '/')

    def _msys_to_win_path(self, msys_path: str) -> str:
        """Convert MSYS2 path back to Windows path."""
        if os.name != 'nt':
            return msys_path
        # /c/Users/... -> C:\Users\...
        if msys_path.startswith('/') and len(msys_path) >= 3 and msys_path[2] == '/':
            return msys_path[1].upper() + ':' + msys_path[2:].replace('/', '\\')
        return msys_path.replace('/', '\\')

    def is_available(self) -> bool:
        """Check if gateway is available and LM Studio is running."""
        try:
            bash_exe = self.GIT_BASH if os.name == 'nt' else 'bash'
            gateway_path = self._win_to_msys_path(self._gateway_path)

            result = subprocess.run(
                [bash_exe, gateway_path, "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "LM Studio: Running" in result.stdout
        except Exception:
            return False

    def get_queue_depth(self) -> int:
        """Check how many items are pending in the gateway queue.

        Returns:
            Number of pending requests, or -1 if queue file doesn't exist
        """
        queue_file = self._ipc_dir / 'queue.jsonl'
        if not queue_file.exists():
            return -1
        try:
            with open(queue_file, 'r') as f:
                lines = [l for l in f.readlines() if l.strip()]
            return len(lines)
        except Exception:
            return -1

    def _generate_request_id(self) -> str:
        """Generate a unique request ID matching gateway format."""
        import random
        timestamp = int(time.time())
        pid = os.getpid()
        rand = random.randint(0, 32767)
        return f"req_{timestamp}_{pid}_{rand}"

    def _queue_requests_direct(
        self,
        requests: list[dict],
    ) -> list[str]:
        """Write multiple requests directly to queue file (bypasses bash overhead).

        This is MUCH faster than spawning bash subprocesses for each request.
        All requests are written atomically, then processor is triggered once.

        Args:
            requests: List of dicts with keys: type, prompt, system, temperature

        Returns:
            List of response file paths (in same order as requests)
        """
        queue_file = self._ipc_dir / 'queue.jsonl'
        responses_dir = self._ipc_dir / 'responses'

        # Ensure directories exist
        self._ipc_dir.mkdir(parents=True, exist_ok=True)
        responses_dir.mkdir(parents=True, exist_ok=True)

        response_paths = []
        queue_entries = []
        queued_at = int(time.time() * 1000)

        for req in requests:
            req_id = self._generate_request_id()
            response_path = responses_dir / f"{req_id}.json"
            response_paths.append(str(response_path))

            entry = {
                "id": req_id,
                "type": req.get("type", "text"),
                "prompt": req.get("prompt", ""),
                "system": req.get("system", ""),
                "temperature": str(req.get("temperature", 0.3)),
                "max_tokens": "",
                "pipe_path": "",
                "file_path": str(response_path).replace("\\", "/"),
                "stream": "false",
                "queued_at": queued_at,
            }
            queue_entries.append(json.dumps(entry))
            queued_at += 1  # Increment to maintain order

        # Write all entries to queue file atomically
        with open(queue_file, 'a') as f:
            for entry in queue_entries:
                f.write(entry + "\n")

        logger.debug(f"Direct-queued {len(requests)} requests")

        # Trigger the processor (single bash call)
        self._trigger_processor()

        return response_paths

    def _trigger_processor(self):
        """Trigger the gateway processor by making a minimal request.

        The bash script only spawns a processor when a request is made.
        We make a quick status check which ensures the script runs.
        """
        try:
            bash_exe = self.GIT_BASH if os.name == 'nt' else 'bash'
            gateway_path = self._win_to_msys_path(self._gateway_path)

            # Status command is fast and ensures script processes any queued items
            subprocess.Popen(
                [bash_exe, gateway_path, "status"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            logger.warning(f"Failed to trigger processor: {e}")

    def _submit_request(
        self,
        request_type: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Submit a request to the gateway and return response file path.

        Uses subprocess to call the bash script which handles processor spawning.
        Caller must poll/wait for file to be written.

        Args:
            request_type: "text", "embedding", or "vision"
            prompt: The prompt text
            system_prompt: Optional system prompt (text/vision only)
            temperature: Optional temperature override

        Returns:
            Path to response file (will be written when request completes)
        """
        # Write prompt to temp file to avoid shell escaping issues
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(prompt)
            temp_path = f.name

        try:
            bash_exe = self.GIT_BASH if os.name == 'nt' else 'bash'
            gateway_path = self._win_to_msys_path(self._gateway_path)
            temp_path_msys = self._win_to_msys_path(temp_path)

            cmd = [bash_exe, gateway_path, "request", request_type,
                   "--prompt-file", temp_path_msys]

            if system_prompt:
                cmd.extend(["--system", system_prompt])
            if temperature is not None:
                cmd.extend(["--temperature", str(temperature)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            if result.returncode != 0:
                raise GatewayError(f"Gateway submit failed: {result.stderr or result.stdout}")

            stdout = result.stdout.strip()
            if not stdout.startswith('FILE='):
                raise GatewayError(f"Unexpected gateway output: {stdout}")

            response_path_msys = stdout[5:]
            return self._msys_to_win_path(response_path_msys)

        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    def _wait_for_response(self, response_path: str) -> dict:
        """Wait for response file and parse it.

        Args:
            response_path: Path to response file

        Returns:
            Parsed JSON response
        """
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            if os.path.exists(response_path):
                try:
                    file_size = os.path.getsize(response_path)
                    if file_size == 0:
                        time.sleep(0.5)
                        continue

                    with open(response_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    if not content.strip():
                        time.sleep(0.5)
                        continue

                    response = json.loads(content)

                    # Clean up response file
                    try:
                        os.unlink(response_path)
                    except Exception:
                        pass

                    if "error" in response:
                        raise GatewayError(f"Gateway error: {response['error']}")

                    return response

                except json.JSONDecodeError:
                    # File might still be being written
                    time.sleep(0.5)
                    continue

            time.sleep(1)

        raise GatewayError(f"Timeout waiting for gateway response after {self.timeout}s")

    # =========================================================================
    # TEXT REQUESTS
    # =========================================================================

    def request_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """Make a text generation request (blocking).

        Args:
            prompt: The prompt text
            system_prompt: Optional system prompt
            temperature: Temperature for generation

        Returns:
            Generated text
        """
        response_path = self._submit_request(
            "text", prompt, system_prompt, temperature
        )
        response = self._wait_for_response(response_path)

        # Extract text from chat completion response
        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]

        raise GatewayError(f"Unexpected text response format: {list(response.keys())}")

    def submit_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """Submit a text request without waiting (for batching).

        Returns the response file path - use collect_text() to get result.
        """
        return self._submit_request("text", prompt, system_prompt, temperature)

    def collect_text(self, response_path: str) -> str:
        """Collect result from a submitted text request."""
        response = self._wait_for_response(response_path)

        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]

        raise GatewayError(f"Unexpected text response format: {list(response.keys())}")

    # =========================================================================
    # EMBEDDING REQUESTS
    # =========================================================================

    def request_embedding(self, text: str) -> list[float]:
        """Make an embedding request (blocking).

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        response_path = self._submit_request("embedding", text)
        response = self._wait_for_response(response_path)

        # Extract embedding from response
        if "data" in response and len(response["data"]) > 0:
            return response["data"][0]["embedding"]
        elif "embedding" in response:
            return response["embedding"]

        raise GatewayError(f"Unexpected embedding response format: {list(response.keys())}")

    def submit_embedding(self, text: str) -> str:
        """Submit an embedding request without waiting (for batching).

        Returns the response file path - use collect_embedding() to get result.
        """
        return self._submit_request("embedding", text)

    def collect_embedding(self, response_path: str) -> list[float]:
        """Collect result from a submitted embedding request."""
        response = self._wait_for_response(response_path)

        if "data" in response and len(response["data"]) > 0:
            return response["data"][0]["embedding"]
        elif "embedding" in response:
            return response["embedding"]

        raise GatewayError(f"Unexpected embedding response format: {list(response.keys())}")

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def batch_text(
        self,
        prompts: list[str],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> list[str]:
        """Process multiple text requests in a batch.

        Uses direct queue writing to submit all requests atomically,
        ensuring the queue is fully saturated before processing begins.

        Args:
            prompts: List of prompts
            system_prompt: Optional system prompt (same for all)
            temperature: Temperature for generation

        Returns:
            List of generated texts (same order as prompts)
        """
        if not prompts:
            return []

        batch_start = time.time()
        logger.debug(f"batch_text: starting {len(prompts)} requests (direct queue)")

        # Build request list
        requests = [
            {
                "type": "text",
                "prompt": prompt,
                "system": system_prompt or "",
                "temperature": temperature,
            }
            for prompt in prompts
        ]

        # Submit all at once via direct queue write
        submit_start = time.time()
        handles = self._queue_requests_direct(requests)
        submit_time = time.time() - submit_start
        queue_depth = self.get_queue_depth()
        logger.debug(f"batch_text: all {len(prompts)} queued in {submit_time:.3f}s, queue={queue_depth}")

        # Collect all responses
        results = []
        collect_start = time.time()
        for i, handle in enumerate(handles):
            t0 = time.time()
            result = self.collect_text(handle)
            results.append(result)
            logger.debug(f"  collect {i+1}/{len(handles)}: {time.time()-t0:.3f}s")

        collect_time = time.time() - collect_start
        total_time = time.time() - batch_start
        logger.debug(f"batch_text: collected in {collect_time:.2f}s, total={total_time:.2f}s")

        return results

    def batch_embedding(self, texts: list[str]) -> list[list[float]]:
        """Process multiple embedding requests in a batch.

        Uses direct queue writing to submit all requests atomically,
        ensuring the queue is fully saturated before processing begins.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (same order as texts)
        """
        if not texts:
            return []

        batch_start = time.time()
        logger.debug(f"batch_embedding: starting {len(texts)} requests (direct queue)")

        # Build request list
        requests = [
            {
                "type": "embedding",
                "prompt": text,
                "temperature": 0.0,
            }
            for text in texts
        ]

        # Submit all at once via direct queue write
        submit_start = time.time()
        handles = self._queue_requests_direct(requests)
        submit_time = time.time() - submit_start
        queue_depth = self.get_queue_depth()
        logger.debug(f"batch_embedding: all {len(texts)} queued in {submit_time:.3f}s, queue={queue_depth}")

        # Collect all responses
        results = []
        collect_start = time.time()
        for i, handle in enumerate(handles):
            t0 = time.time()
            result = self.collect_embedding(handle)
            results.append(result)
            logger.debug(f"  collect {i+1}/{len(handles)}: {time.time()-t0:.3f}s")

        collect_time = time.time() - collect_start
        total_time = time.time() - batch_start
        logger.debug(f"batch_embedding: collected in {collect_time:.2f}s, total={total_time:.2f}s")

        return results

    # =========================================================================
    # CLEANUP OPERATIONS
    # =========================================================================

    def clear_queue(self) -> bool:
        """Clear the gateway queue and stop processing.

        Use this when cancelling work to prevent orphaned requests.

        Returns:
            True if successful, False otherwise
        """
        try:
            bash_exe = self.GIT_BASH if os.name == 'nt' else 'bash'
            gateway_path = self._win_to_msys_path(self._gateway_path)

            result = subprocess.run(
                [bash_exe, gateway_path, "clear-queue"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.returncode == 0
        except Exception:
            return False

    def unload(self) -> bool:
        """Unload all models to free VRAM.

        Also clears the queue to prevent orphaned requests.

        Returns:
            True if successful, False otherwise
        """
        try:
            bash_exe = self.GIT_BASH if os.name == 'nt' else 'bash'
            gateway_path = self._win_to_msys_path(self._gateway_path)

            result = subprocess.run(
                [bash_exe, gateway_path, "unload"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False


# Module-level singleton for convenience
_gateway: Optional[LocalLLMGateway] = None


def get_gateway() -> LocalLLMGateway:
    """Get or create the gateway singleton."""
    global _gateway
    if _gateway is None:
        _gateway = LocalLLMGateway()
    return _gateway
