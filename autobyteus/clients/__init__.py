"""
Client utilities for communicating with the Autobyteus LLM server.

Consolidates the previously standalone autobyteus-llm-client package so the
HTTP client can evolve alongside the rest of the framework.
"""

from .autobyteus_client import AutobyteusClient, CertificateError

__all__ = ["AutobyteusClient", "CertificateError"]
