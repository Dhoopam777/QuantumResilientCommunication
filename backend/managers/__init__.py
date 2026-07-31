"""
Managers Package for Quantum-Resilient Communication System

This package contains the ConnectionManager for WebSocket connection
lifecycle and message broadcasting.
"""

from managers.connection_manager import ConnectionManager, ConnectionInfo, connection_manager

__all__ = ["ConnectionManager", "ConnectionInfo", "connection_manager"]
