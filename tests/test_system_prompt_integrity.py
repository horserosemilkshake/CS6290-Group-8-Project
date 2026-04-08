"""
Tests for System Prompt Integrity (Spec A-02).

Ensures the system prompt is:
1. Stored in a dedicated file (not inline in code)
2. Immutable (hash-verified)
3. Any changes trigger a verification failure
"""

import hashlib
import pytest
from pathlib import Path


class TestSystemPromptIntegrity:
    """TDD Tests for system prompt immutability."""
    
    def test_system_prompt_file_exists(self):
        """System prompt should be stored in a dedicated file, not inline in code."""
        prompt_file = Path(__file__).resolve().parents[1] / "agent_client" / "src" / "llm" / "system_prompt.txt"
        assert prompt_file.exists(), f"System prompt file not found at {prompt_file}"
    
    def test_system_prompt_hash_matches_expected(self):
        """System prompt hash must match the expected hash recorded in the codebase."""
        # Load the system prompt file
        prompt_file = Path(__file__).resolve().parents[1] / "agent_client" / "src" / "llm" / "system_prompt.txt"
        if not prompt_file.exists():
            pytest.skip("System prompt file not yet created (TDD phase)")
        
        current_prompt = prompt_file.read_text(encoding="utf-8")
        current_hash = hashlib.sha256(current_prompt.encode("utf-8")).hexdigest()
        
        # Load the expected hash from the hash file
        hash_file = Path(__file__).resolve().parents[1] / "agent_client" / "src" / "llm" / "system_prompt.hash"
        if not hash_file.exists():
            pytest.skip("Hash file not yet created (TDD phase)")
        
        expected_hash = hash_file.read_text(encoding="utf-8").strip()
        
        assert current_hash == expected_hash, (
            f"System prompt has been modified!\n"
            f"Expected hash: {expected_hash}\n"
            f"Actual hash:   {current_hash}\n"
            f"If you intentionally modified the prompt, update the hash file."
        )
    
    def test_system_prompt_hash_verification_script_exists(self):
        """A verification script should exist for CI integration."""
        script_file = Path(__file__).resolve().parents[1] / "scripts" / "verify_system_prompt.py"
        assert script_file.exists(), f"Verification script not found at {script_file}"
    
    def test_inline_system_prompt_removed(self):
        """The inline SYSTEM_PROMPT constant should be removed from llm_planner.py."""
        planner_file = Path(__file__).resolve().parents[1] / "agent_client" / "src" / "llm" / "llm_planner.py"
        content = planner_file.read_text(encoding="utf-8")
        
        # After refactoring, SYSTEM_PROMPT should be loaded from file, not defined inline
        # We allow the variable name but it should be loaded from file
        lines = content.split("\n")
        prompt_start = None
        for i, line in enumerate(lines):
            if 'SYSTEM_PROMPT = """' in line:
                prompt_start = i
                break
        
        if prompt_start is not None:
            # Check if it's loading from file (new way) or inline definition (old way)
            next_lines = "\n".join(lines[prompt_start:prompt_start+5])
            if '"""' in next_lines and "You are a" in next_lines:
                pytest.fail(
                    "SYSTEM_PROMPT is still defined inline in llm_planner.py. "
                    "It should be loaded from system_prompt.txt file instead."
                )


class TestSystemPromptVerificationScript:
    """Tests for the verification script itself."""
    
    def test_verification_script_returns_zero_on_valid_hash(self):
        """Script should return exit code 0 when hash matches."""
        import subprocess
        import sys
        
        script_file = Path(__file__).resolve().parents[1] / "scripts" / "verify_system_prompt.py"
        if not script_file.exists():
            pytest.skip("Verification script not yet created (TDD phase)")
        
        result = subprocess.run(
            [sys.executable, str(script_file)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, (
            f"Verification script failed with exit code {result.returncode}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
    
    def test_verification_script_returns_nonzero_on_modified_prompt(self, tmp_path):
        """Script should return non-zero exit code when prompt is modified."""
        import subprocess
        import sys
        
        script_file = Path(__file__).resolve().parents[1] / "scripts" / "verify_system_prompt.py"
        if not script_file.exists():
            pytest.skip("Verification script not yet created (TDD phase)")
        
        # Create a temporary modified prompt
        temp_dir = tmp_path / "test_integrity"
        temp_dir.mkdir()
        
        modified_prompt = temp_dir / "system_prompt.txt"
        modified_prompt.write_text("MODIFIED PROMPT CONTENT")
        
        # Create hash file with original hash (simulating unupdated hash)
        original_hash = hashlib.sha256(b"ORIGINAL CONTENT").hexdigest()
        hash_file = temp_dir / "system_prompt.hash"
        hash_file.write_text(original_hash)
        
        # Run verification script with modified files
        result = subprocess.run(
            [sys.executable, str(script_file), "--prompt-dir", str(temp_dir)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0, (
            "Verification script should fail when prompt is modified but hash is not updated"
        )
