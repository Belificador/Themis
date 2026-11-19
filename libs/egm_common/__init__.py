"""Shared infrastructure helpers for the Themis microservices.

This package intentionally contains only infrastructure concerns (logging,
messaging, outbox, database bootstrapping). Domain models live inside each
service so that no service shares another service's persistence layer.
"""

__version__ = "0.1.0"
