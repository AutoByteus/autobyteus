"""
Unit tests for pty_session.py

Note: These tests require a Unix-like system with bash available.
Some tests are marked as integration tests as they spawn real processes.
"""

import asyncio
import os
import pytest
import tempfile

from autobyteus.tools.terminal.pty_session import PtySession


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestPtySession:
    """Unit tests for PtySession class."""
    
    @pytest.mark.asyncio
    async def test_session_id_property(self):
        """Test session_id property returns correct value."""
        session = PtySession("test-123")
        assert session.session_id == "test-123"
    
    @pytest.mark.asyncio
    async def test_is_alive_before_start(self):
        """Test is_alive returns False before starting."""
        session = PtySession("test")
        assert not session.is_alive
    
    @pytest.mark.asyncio
    async def test_write_before_start_raises(self):
        """Test writing before start raises RuntimeError."""
        session = PtySession("test")
        
        with pytest.raises(RuntimeError, match="Session not started"):
            await session.write(b"test")
    
    @pytest.mark.asyncio
    async def test_read_before_start_raises(self):
        """Test reading before start raises RuntimeError."""
        session = PtySession("test")
        
        with pytest.raises(RuntimeError, match="Session not started"):
            await session.read()
    
    @pytest.mark.asyncio
    async def test_resize_before_start_raises(self):
        """Test resize before start raises RuntimeError."""
        session = PtySession("test")
        
        with pytest.raises(RuntimeError, match="Session not started"):
            session.resize(24, 80)
    
    @pytest.mark.asyncio
    async def test_double_start_raises(self, temp_dir):
        """Test starting twice raises RuntimeError."""
        session = PtySession("test")
        await session.start(temp_dir)
        
        try:
            with pytest.raises(RuntimeError, match="already started"):
                await session.start(temp_dir)
        finally:
            await session.close()
    
    @pytest.mark.asyncio
    async def test_close_idempotent(self, temp_dir):
        """Test close can be called multiple times safely."""
        session = PtySession("test")
        await session.start(temp_dir)
        
        await session.close()
        await session.close()  # Should not raise
    
    @pytest.mark.asyncio
    async def test_read_after_close_returns_none(self, temp_dir):
        """Test reading after close returns None."""
        session = PtySession("test")
        await session.start(temp_dir)
        await session.close()
        
        result = await session.read()
        assert result is None
    
    @pytest.mark.asyncio 
    async def test_write_after_close_raises(self, temp_dir):
        """Test writing after close raises RuntimeError."""
        session = PtySession("test")
        await session.start(temp_dir)
        await session.close()
        
        with pytest.raises(RuntimeError, match="closed"):
            await session.write(b"test")


@pytest.mark.integration
class TestPtySessionIntegration:
    """Integration tests that spawn real bash processes."""
    
    @pytest.mark.asyncio
    async def test_start_and_is_alive(self, temp_dir):
        """Test starting a session makes it alive."""
        session = PtySession("test")
        
        try:
            await session.start(temp_dir)
            assert session.is_alive
        finally:
            await session.close()
        
        assert not session.is_alive
    
    @pytest.mark.asyncio
    async def test_write_and_read(self, temp_dir):
        """Test writing a command and reading output."""
        session = PtySession("test")
        
        try:
            await session.start(temp_dir)
            
            # Write a simple command
            await session.write(b"echo hello\n")
            
            # Read output (may need multiple reads)
            output = b""
            for _ in range(20):  # Try up to 2 seconds
                data = await session.read(timeout=0.1)
                if data:
                    output += data
                if b"hello" in output:
                    break
            
            assert b"hello" in output
        finally:
            await session.close()
    
    @pytest.mark.asyncio
    async def test_cd_persistence(self, temp_dir):
        """Test that cd command persists between commands."""
        session = PtySession("test")
        
        # Create a subdirectory
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        
        try:
            await session.start(temp_dir)
            
            # Change directory
            await session.write(b"cd subdir\n")
            await asyncio.sleep(0.2)
            
            # Check current directory
            await session.write(b"pwd\n")
            
            output = b""
            for _ in range(20):
                data = await session.read(timeout=0.1)
                if data:
                    output += data
                if b"subdir" in output:
                    break
            
            assert b"subdir" in output
        finally:
            await session.close()
    
    @pytest.mark.asyncio
    async def test_environment_persistence(self, temp_dir):
        """Test that environment variables persist."""
        session = PtySession("test")
        
        try:
            await session.start(temp_dir)
            
            # Set environment variable
            await session.write(b"export TEST_VAR=hello_world\n")
            await asyncio.sleep(0.2)
            
            # Echo the variable
            await session.write(b"echo $TEST_VAR\n")
            
            output = b""
            for _ in range(20):
                data = await session.read(timeout=0.1)
                if data:
                    output += data
                if b"hello_world" in output:
                    break
            
            assert b"hello_world" in output
        finally:
            await session.close()
    
    @pytest.mark.asyncio
    async def test_resize(self, temp_dir):
        """Test terminal resize doesn't raise errors."""
        session = PtySession("test")
        
        try:
            await session.start(temp_dir)
            session.resize(40, 120)  # Should not raise
        finally:
            await session.close()
