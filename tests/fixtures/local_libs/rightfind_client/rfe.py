# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect


class RightFindError(Exception):
    pass


class SearchClient:
    def search(self, query):
        if query == "fail":
            raise RightFindError("Search failed")
        return [{"title": "Novel Inhibitors", "doi": "10.1000/1"}]


class OrderClient:
    def place_order(self, content_id):
        if content_id == "fail":
            raise RightFindError("Purchase failed")
        return {"status": "success", "download_url": "http://example.com/pdf"}


class RFEClient:
    def __init__(self, username=None, password=None):
        self.subclients = type("SubClients", (), {})()
        self.subclients.search = SearchClient().search
        self.subclients.orders = OrderClient().place_order
