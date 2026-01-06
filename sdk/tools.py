"""
SAP SDK - Tool Manager

Manages external binary dependencies (hal-simplicity, simc).
Downloads and caches binaries automatically on first use.
"""

import os
import sys
import platform
import hashlib
import tarfile
import zipfile
import stat
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass
import urllib.request
import urllib.error
import json


@dataclass
class ToolInfo:
    """Information about an external tool."""
    name: str
    version: str
    description: str
    urls: Dict[str, str]  # platform -> url
    checksums: Dict[str, str]  # platform -> sha256


# Tool definitions
# TODO: Update URLs after creating GitHub releases
TOOLS: Dict[str, ToolInfo] = {
    "hal-simplicity": ToolInfo(
        name="hal-simplicity",
        version="1.0.0",
        description="Simplicity PSET toolchain for Liquid",
        urls={
            "linux-x64": "https://github.com/brunocapelao/hal-simplicity/releases/download/v1.0.0/hal-simplicity-linux-x64.tar.gz",
            "darwin-x64": "https://github.com/brunocapelao/hal-simplicity/releases/download/v1.0.0/hal-simplicity-darwin-x64.tar.gz",
            "darwin-arm64": "https://github.com/brunocapelao/hal-simplicity/releases/download/v1.0.0/hal-simplicity-darwin-arm64.tar.gz",
        },
        checksums={
            # TODO: Add actual checksums after building releases
            "linux-x64": "",
            "darwin-x64": "",
            "darwin-arm64": "",
        }
    ),
    "simc": ToolInfo(
        name="simc",
        version="0.5.0",
        description="Simfony compiler (Simfony -> Simplicity)",
        urls={
            "linux-x64": "https://github.com/BlockstreamResearch/simfony/releases/download/v0.5.0/simc-linux-x64.tar.gz",
            "darwin-x64": "https://github.com/BlockstreamResearch/simfony/releases/download/v0.5.0/simc-darwin-x64.tar.gz",
            "darwin-arm64": "https://github.com/BlockstreamResearch/simfony/releases/download/v0.5.0/simc-darwin-arm64.tar.gz",
        },
        checksums={
            "linux-x64": "",
            "darwin-x64": "",
            "darwin-arm64": "",
        }
    ),
}


class ToolError(Exception):
    """Error with tool management."""
    pass


class ToolManager:
    """
    Manages external binary tools required by the SDK.
    
    Downloads and caches binaries to ~/.sap-sdk/bin/ on first use.
    
    Example:
        manager = ToolManager()
        
        # Ensure all tools are installed
        manager.ensure_all_installed()
        
        # Get path to specific tool
        hal_path = manager.get_path("hal-simplicity")
        
        # Check status
        for tool, info in manager.status().items():
            print(f"{tool}: {'✓' if info['installed'] else '✗'}")
    """
    
    DEFAULT_CACHE_DIR = Path.home() / ".sap-sdk"
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize tool manager.
        
        Args:
            cache_dir: Custom cache directory (default: ~/.sap-sdk/)
        """
        self.cache_dir = cache_dir or self.DEFAULT_CACHE_DIR
        self.bin_dir = self.cache_dir / "bin"
        self.platform = self._detect_platform()
    
    def _detect_platform(self) -> str:
        """Detect current platform."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "linux":
            if machine in ("x86_64", "amd64"):
                return "linux-x64"
            elif machine in ("aarch64", "arm64"):
                return "linux-arm64"
        elif system == "darwin":
            if machine in ("x86_64", "amd64"):
                return "darwin-x64"
            elif machine in ("arm64", "aarch64"):
                return "darwin-arm64"
        elif system == "windows":
            return "windows-x64"
        
        raise ToolError(f"Unsupported platform: {system}-{machine}")
    
    def get_path(self, tool_name: str) -> Path:
        """
        Get path to tool binary.
        
        Args:
            tool_name: Name of tool ("hal-simplicity" or "simc")
        
        Returns:
            Path to binary.
        
        Raises:
            ToolError: If tool not found or not installed.
        """
        if tool_name not in TOOLS:
            raise ToolError(f"Unknown tool: {tool_name}")
        
        binary_path = self.bin_dir / tool_name
        if sys.platform == "win32":
            binary_path = binary_path.with_suffix(".exe")
        
        if not binary_path.exists():
            raise ToolError(
                f"Tool '{tool_name}' not installed. "
                f"Run: ToolManager().install('{tool_name}')"
            )
        
        return binary_path
    
    def is_installed(self, tool_name: str) -> bool:
        """Check if tool is installed."""
        try:
            self.get_path(tool_name)
            return True
        except ToolError:
            return False
    
    def status(self) -> Dict[str, dict]:
        """Get status of all tools."""
        result = {}
        for name, info in TOOLS.items():
            installed = self.is_installed(name)
            result[name] = {
                "installed": installed,
                "version": info.version,
                "description": info.description,
                "path": str(self.bin_dir / name) if installed else None,
            }
        return result
    
    def install(self, tool_name: str, force: bool = False) -> Path:
        """
        Install a tool.
        
        Args:
            tool_name: Name of tool to install.
            force: Re-download even if already installed.
        
        Returns:
            Path to installed binary.
        """
        if tool_name not in TOOLS:
            raise ToolError(f"Unknown tool: {tool_name}")
        
        info = TOOLS[tool_name]
        
        # Check if already installed
        binary_path = self.bin_dir / tool_name
        if binary_path.exists() and not force:
            return binary_path
        
        # Get URL for platform
        if self.platform not in info.urls:
            raise ToolError(
                f"Tool '{tool_name}' not available for {self.platform}"
            )
        
        url = info.urls[self.platform]
        expected_checksum = info.checksums.get(self.platform, "")
        
        print(f"📦 Installing {tool_name} v{info.version}...")
        print(f"   Platform: {self.platform}")
        print(f"   Source: {url}")
        
        # Create directories
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        
        # Download
        try:
            download_path = self.cache_dir / f"{tool_name}.download"
            self._download(url, download_path)
            
            # Verify checksum
            if expected_checksum:
                actual = self._checksum(download_path)
                if actual != expected_checksum:
                    download_path.unlink()
                    raise ToolError(
                        f"Checksum mismatch for {tool_name}. "
                        f"Expected {expected_checksum[:16]}..., got {actual[:16]}..."
                    )
            
            # Extract
            self._extract(download_path, self.bin_dir, tool_name)
            
            # Cleanup
            download_path.unlink()
            
            # Make executable
            binary_path.chmod(binary_path.stat().st_mode | stat.S_IEXEC)
            
            print(f"✓ {tool_name} installed to {binary_path}")
            return binary_path
            
        except urllib.error.URLError as e:
            raise ToolError(f"Failed to download {tool_name}: {e}")
    
    def install_all(self, force: bool = False) -> Dict[str, Path]:
        """Install all required tools."""
        result = {}
        for tool_name in TOOLS:
            try:
                result[tool_name] = self.install(tool_name, force)
            except ToolError as e:
                print(f"⚠ Failed to install {tool_name}: {e}")
        return result
    
    def ensure_installed(self, tool_name: str) -> Path:
        """Ensure tool is installed, download if needed."""
        if self.is_installed(tool_name):
            return self.get_path(tool_name)
        return self.install(tool_name)
    
    def ensure_all_installed(self) -> Dict[str, Path]:
        """Ensure all tools are installed."""
        result = {}
        for tool_name in TOOLS:
            result[tool_name] = self.ensure_installed(tool_name)
        return result
    
    def _download(self, url: str, dest: Path) -> None:
        """Download file with progress."""
        def report(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 // total_size)
                print(f"\r   Downloading: {percent}%", end="", flush=True)
        
        urllib.request.urlretrieve(url, dest, reporthook=report)
        print()  # Newline after progress
    
    def _checksum(self, path: Path) -> str:
        """Calculate SHA256 checksum."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _extract(self, archive: Path, dest: Path, binary_name: str) -> None:
        """Extract binary from archive."""
        suffix = archive.suffix.lower()
        
        if suffix == ".gz" or str(archive).endswith(".tar.gz"):
            with tarfile.open(archive, "r:gz") as tar:
                # Find the binary in the archive
                for member in tar.getmembers():
                    if member.name.endswith(binary_name) or binary_name in member.name:
                        # Extract to bin directory
                        member.name = binary_name
                        tar.extract(member, dest)
                        return
                # If not found by name, extract first executable
                for member in tar.getmembers():
                    if member.isfile():
                        member.name = binary_name
                        tar.extract(member, dest)
                        return
        elif suffix == ".zip":
            with zipfile.ZipFile(archive, "r") as zf:
                for name in zf.namelist():
                    if binary_name in name:
                        content = zf.read(name)
                        (dest / binary_name).write_bytes(content)
                        return
        else:
            # Assume it's a raw binary
            (dest / binary_name).write_bytes(archive.read_bytes())


# Convenience function
def ensure_tools() -> Dict[str, Path]:
    """
    Ensure all required tools are installed.
    
    Call this at SDK initialization to auto-download missing tools.
    
    Returns:
        Dict mapping tool names to their paths.
    
    Example:
        from sdk.tools import ensure_tools
        
        paths = ensure_tools()
        print(f"hal-simplicity: {paths['hal-simplicity']}")
    """
    return ToolManager().ensure_all_installed()


def get_tool_path(tool_name: str) -> str:
    """
    Get path to a tool, installing if needed.
    
    Args:
        tool_name: "hal-simplicity" or "simc"
    
    Returns:
        Absolute path to binary as string.
    """
    return str(ToolManager().ensure_installed(tool_name))
