"""Version metadata for the IV&V Python SDK."""

__version__ = "0.1.0"
# Module-registry contract version (mirrors hal.ModuleInfo.version major).
# The SDK refuses to talk to a peer whose ListModules returns module versions
# strictly greater than this value (see zion_sdk._channel.handshake).
__contracts_version__ = 1
