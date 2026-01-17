#!/usr/bin/env python3
"""Diagnostic script to test queue saturation behavior."""

import logging
import sys

# Enable debug logging for gateway
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

from src.gateway import get_gateway, GatewayUnavailableError

def main():
    try:
        gateway = get_gateway()
    except GatewayUnavailableError as e:
        print(f"Gateway unavailable: {e}")
        return 1

    if not gateway.is_available():
        print("LM Studio not running - start it first")
        return 1

    print("Testing queue saturation with 3 text requests...")
    print("Watch for queue depth during submit phase.\n")

    # Small batch of simple prompts
    prompts = [
        "What is 2+2? Reply with just the number.",
        "What is 3+3? Reply with just the number.",
        "What is 4+4? Reply with just the number.",
    ]

    results = gateway.batch_text(prompts, temperature=0.1)

    print("\nResults:")
    for i, result in enumerate(results):
        print(f"  {i+1}: {result.strip()[:50]}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
