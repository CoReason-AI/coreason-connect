# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

# Mock Confex Client Library
# This simulates an external library that the adapter would wrap.


class ConfexError(Exception):
    pass


class ConfexClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def search_abstracts(self, conference_id: str, keywords: list[str]) -> list[dict]:
        """Mock search for abstracts."""
        if conference_id == "INVALID":
            raise ConfexError("Invalid conference ID")

        if conference_id == "EMPTY":
            return []

        return [
            {"id": "abs_123", "title": f"Advances in {keywords[0] if keywords else 'Science'}", "author": "Dr. Smith"},
            {"id": "abs_456", "title": "Novel Approaches", "author": "Dr. Jones"},
        ]

    def get_session_details(self, session_id: str) -> dict:
        """Mock retrieval of session details."""
        if session_id == "missing":
            return {}  # Or raise, depending on API behavior. Let's return empty to test handling.

        if session_id == "sess_999":
            return {
                "id": "sess_999",
                "title": "Keynote: The Future",
                "location": "Grand Ballroom",
                "start_time": "2023-10-15T09:00:00Z",
                "speakers": ["Elon M.", "Sam A."],
            }

        raise ConfexError(f"Session {session_id} not found")
