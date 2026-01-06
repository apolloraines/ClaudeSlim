#!/usr/bin/env python3
"""
LoreToken Compression Proxy for Claude Code
Intercepts Anthropic API calls and applies semantic compression.

Usage:
    export ANTHROPIC_BASE_URL="http://localhost:8086"
    python3 loretoken_compression_proxy.py

Target: 2-3x token reduction → 2-3x longer usage before rate limits
"""

import json
import time
import logging
import sys
from flask import Flask, request, Response, jsonify
import requests
from claude_compressor import compress_message, get_stats

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for troubleshooting
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/nova/loretoken_proxy.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
ANTHROPIC_API_URL = "https://api.anthropic.com"
COMPRESSION_ENABLED = True  # ENABLED: Using safe aggressive compression
COMPRESSION_LEVEL = "aggressive"  # Options: minimal, medium, aggressive, extreme
LOG_STATS = True  # Log compression statistics


class CompressionStats:
    """Track compression statistics across requests"""

    def __init__(self):
        self.total_requests = 0
        self.total_original_tokens = 0
        self.total_compressed_tokens = 0
        self.total_savings = 0
        self.compression_errors = 0
        self.passthrough_requests = 0

    def update(self, stats: dict):
        """Update statistics with new compression data"""
        self.total_requests += 1
        self.total_original_tokens += stats.get('original_tokens_est', 0)
        self.total_compressed_tokens += stats.get('compressed_tokens_est', 0)
        self.total_savings += stats.get('token_savings', 0)

    def error(self):
        """Increment error count"""
        self.compression_errors += 1

    def passthrough(self):
        """Increment passthrough count"""
        self.passthrough_requests += 1

    def summary(self):
        """Get summary statistics"""
        if self.total_requests == 0:
            return "No requests processed yet"

        avg_reduction = (self.total_savings / self.total_original_tokens * 100) if self.total_original_tokens > 0 else 0

        return f"""
Compression Statistics:
  Total Requests: {self.total_requests}
  Original Tokens: {self.total_original_tokens:,}
  Compressed Tokens: {self.total_compressed_tokens:,}
  Total Savings: {self.total_savings:,} tokens
  Avg Reduction: {avg_reduction:.1f}%
  Errors: {self.compression_errors}
  Passthrough: {self.passthrough_requests}
"""


# Global stats tracker
stats_tracker = CompressionStats()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "compression_enabled": COMPRESSION_ENABLED,
        "stats": {
            "total_requests": stats_tracker.total_requests,
            "total_savings": stats_tracker.total_savings,
            "errors": stats_tracker.compression_errors
        }
    })


@app.route('/stats', methods=['GET'])
def get_statistics():
    """Get compression statistics"""
    return Response(stats_tracker.summary(), content_type='text/plain')


@app.route('/v1/messages/count_tokens', methods=['POST'])
def proxy_count_tokens():
    """
    Proxy token counting endpoint
    Note: This returns compressed token count, not original
    """
    try:
        original_message = request.json

        # Build URL with query parameters
        url = f"{ANTHROPIC_API_URL}/v1/messages/count_tokens"
        if request.query_string:
            url = f"{url}?{request.query_string.decode('utf-8')}"

        if not COMPRESSION_ENABLED:
            # Passthrough mode
            response = requests.post(
                url,
                json=original_message,
                headers=_get_headers(),
                timeout=30
            )
            stats_tracker.passthrough()
            return Response(response.content, status=response.status_code,
                            content_type=response.headers.get('Content-Type'))

        # Compress and count
        compressed = compress_message(original_message)

        # Forward to Anthropic
        response = requests.post(
            url,
            json=compressed,
            headers=_get_headers(),
            timeout=30
        )

        # Log compression stats
        if LOG_STATS:
            orig_size = len(json.dumps(original_message))
            comp_size = len(json.dumps(compressed))
            comp_stats = {
                'original_tokens_est': orig_size // 4,
                'compressed_tokens_est': comp_size // 4,
                'token_savings': (orig_size - comp_size) // 4,
                'reduction_pct': round(((orig_size - comp_size) / orig_size * 100), 2)
            }
            logger.info(f"Token count - Reduction: {comp_stats['reduction_pct']}% "
                        f"({comp_stats['original_tokens_est']} -> {comp_stats['compressed_tokens_est']} tokens)")
            stats_tracker.update(comp_stats)

        return Response(response.content, status=response.status_code,
                        content_type=response.headers.get('Content-Type'))

    except Exception as e:
        logger.error(f"Error in count_tokens proxy: {e}", exc_info=True)
        stats_tracker.error()
        # Fallback to passthrough
        response = requests.post(
            f"{ANTHROPIC_API_URL}/v1/messages/count_tokens",
            json=request.json,
            headers=_get_headers(),
            timeout=30
        )
        return Response(response.content, status=response.status_code,
                        content_type=response.headers.get('Content-Type'))


@app.route('/v1/messages', methods=['POST'])
def proxy_messages():
    """
    Main proxy endpoint for Claude API messages
    Compresses outgoing, streams responses back
    """
    start_time = time.time()

    try:
        # Parse incoming request
        original_message = request.json

        if not original_message:
            return jsonify({"error": "No JSON body provided"}), 400

        # Log original request (truncated)
        logger.info(f"Received request for model: {original_message.get('model', 'unknown')}")

        if not COMPRESSION_ENABLED:
            # Passthrough mode - no compression
            logger.info("Compression disabled - passthrough mode")
            stats_tracker.passthrough()
            return _forward_request(original_message, start_time)

        # Apply compression
        try:
            compressed_message = compress_message(original_message)

            # Calculate and log compression stats
            orig_size = len(json.dumps(original_message))
            comp_size = len(json.dumps(compressed_message))
            comp_stats = {
                'original_tokens_est': orig_size // 4,
                'compressed_tokens_est': comp_size // 4,
                'token_savings': (orig_size - comp_size) // 4,
                'reduction_pct': round(((orig_size - comp_size) / orig_size * 100), 2)
            }

            if LOG_STATS:
                logger.info(f"Compression: {comp_stats['reduction_pct']}% reduction "
                            f"({comp_stats['original_tokens_est']} -> {comp_stats['compressed_tokens_est']} tokens) "
                            f"| Savings: {comp_stats['token_savings']} tokens")

            stats_tracker.update(comp_stats)

        except Exception as e:
            logger.error(f"Compression failed: {e}, falling back to passthrough")
            stats_tracker.error()
            compressed_message = original_message

        # Forward to Anthropic
        return _forward_request(compressed_message, start_time)

    except Exception as e:
        logger.error(f"Error in messages proxy: {e}", exc_info=True)
        stats_tracker.error()
        return jsonify({"error": str(e)}), 500


def _get_headers():
    """Extract headers from incoming request for forwarding"""
    headers = {}

    # Forward ALL headers except host-related ones
    skip_headers = {'Host', 'Connection', 'Content-Length', 'Transfer-Encoding'}

    for header_name, header_value in request.headers:
        if header_name not in skip_headers:
            headers[header_name] = header_value

    # Ensure critical headers are present
    if 'Anthropic-Version' not in headers:
        headers['Anthropic-Version'] = '2023-06-01'

    if 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/json'

    # Debug logging
    logger.debug(f"Forwarding headers: {list(headers.keys())}")

    return headers


def _forward_request(message: dict, start_time: float):
    """Forward request to Anthropic API and stream response"""
    try:
        # Check if streaming is requested
        is_streaming = message.get('stream', False)

        # Build URL with query parameters from original request
        url = f"{ANTHROPIC_API_URL}/v1/messages"
        if request.query_string:
            url = f"{url}?{request.query_string.decode('utf-8')}"
            logger.debug(f"Forwarding with query params: {request.query_string.decode('utf-8')}")

        # Forward to Anthropic
        response = requests.post(
            url,
            json=message,
            headers=_get_headers(),
            stream=is_streaming,  # Enable streaming if requested
            timeout=300  # 5 minute timeout for long responses
        )

        # Check for errors
        if response.status_code != 200:
            logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
            return Response(response.content, status=response.status_code,
                            content_type=response.headers.get('Content-Type', 'application/json'))

        # Log completion time
        elapsed = time.time() - start_time
        logger.info(f"Request completed in {elapsed:.2f}s")

        # Stream response back to client
        if is_streaming:
            def generate():
                """Generator for streaming responses"""
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk

            return Response(
                generate(),
                status=response.status_code,
                content_type=response.headers.get('Content-Type', 'text/event-stream')
            )
        else:
            # Non-streaming response
            return Response(
                response.content,
                status=response.status_code,
                content_type=response.headers.get('Content-Type', 'application/json')
            )

    except requests.exceptions.Timeout:
        logger.error("Request to Anthropic API timed out")
        return jsonify({"error": "Request timed out"}), 504
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to Anthropic API: {e}")
        return jsonify({"error": "Connection error to Anthropic API"}), 502
    except Exception as e:
        logger.error(f"Error forwarding request: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint - show proxy info"""
    info = f"""
LoreToken Compression Proxy for Claude Code
===========================================

Status: {'ACTIVE' if COMPRESSION_ENABLED else 'PASSTHROUGH MODE'}

Endpoints:
  POST /v1/messages           - Main API endpoint (compressed)
  POST /v1/messages/count_tokens - Token counting (compressed)
  GET  /health                - Health check
  GET  /stats                 - Compression statistics

Configuration:
  Compression: {'Enabled' if COMPRESSION_ENABLED else 'Disabled'}
  Logging: {'Enabled' if LOG_STATS else 'Disabled'}
  Forward to: {ANTHROPIC_API_URL}

{stats_tracker.summary()}

To use this proxy with Claude Code:
  export ANTHROPIC_BASE_URL="http://localhost:8086"
"""
    return Response(info, content_type='text/plain')


def main():
    """Start the compression proxy server"""
    logger.info("=" * 80)
    logger.info("LoreToken Compression Proxy for Claude Code")
    logger.info("=" * 80)
    logger.info(f"Compression: {'ENABLED' if COMPRESSION_ENABLED else 'DISABLED'}")
    logger.info(f"Forward to: {ANTHROPIC_API_URL}")
    logger.info(f"Listening on: http://localhost:8086")
    logger.info("=" * 80)

    # Start Flask server
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=8086,
        debug=False,  # Disable debug mode for production
        threaded=True  # Enable threading for concurrent requests
    )


if __name__ == '__main__':
    main()
