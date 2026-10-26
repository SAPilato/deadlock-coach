"""The only package that talks to deadlock-api.com and Valve's protobuf definitions.

A new patch needs only a cache refresh: every cached row stores the client build
(`patch_version`) it was fetched under, and asset rows older than the live build
are refetched on next use.
"""
