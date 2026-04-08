#!/usr/bin/env python3
"""System Prompt Integrity Verification Script (Spec A-02)."""

import argparse
import hashlib
import sys
from pathlib import Path


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file contents."""
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def verify_system_prompt(prompt_dir: Path) -> bool:
    """Verify system prompt integrity."""
    prompt_file = prompt_dir / "system_prompt.txt"
    hash_file = prompt_dir / "system_prompt.hash"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"System prompt file not found: {prompt_file}")
    
    if not hash_file.exists():
        raise FileNotFoundError(f"Hash file not found: {hash_file}")
    
    current_hash = compute_sha256(prompt_file)
    expected_hash = hash_file.read_text(encoding="utf-8").strip()
    
    return current_hash == expected_hash


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify system prompt integrity against recorded hash"
    )
    parser.add_argument(
        "--prompt-dir",
        type=Path,
        default=None,
        help="Directory containing system_prompt.txt and system_prompt.hash"
    )
    args = parser.parse_args()
    
    if args.prompt_dir is None:
        script_dir = Path(__file__).resolve().parent
        prompt_dir = script_dir.parent / "agent_client" / "src" / "llm"
    else:
        prompt_dir = args.prompt_dir.resolve()
    
    try:
        is_valid = verify_system_prompt(prompt_dir)
        
        if is_valid:
            hash_file = prompt_dir / "system_prompt.hash"
            expected_hash = hash_file.read_text(encoding="utf-8").strip()
            print(f"System prompt integrity verified")
            print(f"  Hash: {expected_hash[:16]}...")
            print(f"  Location: {prompt_dir / 'system_prompt.txt'}")
            return 0
        else:
            prompt_file = prompt_dir / "system_prompt.txt"
            hash_file = prompt_dir / "system_prompt.hash"
            
            current_hash = compute_sha256(prompt_file)
            expected_hash = hash_file.read_text(encoding="utf-8").strip()
            
            print("System prompt integrity check FAILED", file=sys.stderr)
            print(f"  The system prompt has been modified.", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"  Expected hash: {expected_hash}", file=sys.stderr)
            print(f"  Actual hash:   {current_hash}", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"  To fix:", file=sys.stderr)
            print(f"    1. If intentional: Update the hash file", file=sys.stderr)
            print(f"    2. If unauthorized: Revert changes to system_prompt.txt", file=sys.stderr)
            return 1
            
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
