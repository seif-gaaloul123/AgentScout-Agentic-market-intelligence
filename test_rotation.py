import sys
import types
from unittest import mock

sys.path.insert(0, ".")

# Stub heavy optional deps that tools.py imports at module level but only uses at runtime.
tavily_mod = types.ModuleType("tavily")
tavily_mod.TavilyClient = object
sys.modules["tavily"] = tavily_mod
scrapling_mod = types.ModuleType("scrapling")
sys.modules.setdefault("scrapling", scrapling_mod)
fetchers_mod = types.ModuleType("scrapling.fetchers")
fetchers_mod.Fetcher = object
sys.modules["scrapling.fetchers"] = fetchers_mod

import tools

creds = [
    ("acc1", "key1"),
    ("acc2", "key2"),
    ("acc3", "key3"),
]
model = tools.CloudflareRotateChatModel(model_name="test-model", credentials=creds)


class FakeResp:
    def __init__(self, status, json_data=None):
        self.status_code = status
        self._json = json_data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


calls = []


def fake_post(url, headers=None, json=None):
    calls.append((url, headers))
    idx = len(calls) - 1
    if idx == 0:
        return FakeResp(429)  # rate limit -> rotate
    if idx == 1:
        return FakeResp(403)  # rate limit -> rotate
    return FakeResp(200, {"result": {"response": "ok response"}})


from langchain_core.messages import HumanMessage

with mock.patch("tools.requests.post", side_effect=fake_post):
    res = model._generate([HumanMessage(content="hi")])

print("RESULT:", res.generations[0].message.content)
print("CALLS:")
for i, (url, headers) in enumerate(calls):
    print(f"  {i}: account={url.split('/accounts/')[1].split('/ai')[0]} auth={headers['Authorization']}")

assert res.generations[0].message.content == "ok response", "should return last response"
assert "acc1" in calls[0][0] and calls[0][1]["Authorization"] == "Bearer key1"
assert "acc2" in calls[1][0] and calls[1][1]["Authorization"] == "Bearer key2"
assert "acc3" in calls[2][0] and calls[2][1]["Authorization"] == "Bearer key3"
print("\nPASS: account ID and API key rotate together on every rate-limit.")
print("PARSED CREDENTIALS COUNT:", len(tools.load_cloudflare_credentials()))
