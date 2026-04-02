from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

fake_mcp = ModuleType("mcp")
fake_mcp_server = ModuleType("mcp.server")
fake_mcp_fastmcp = ModuleType("mcp.server.fastmcp")
fake_mcp_client = ModuleType("mcp.client")
fake_mcp_stdio = ModuleType("mcp.client.stdio")


class FakeFastMCP:
    def __init__(self, *_args, **_kwargs):
        pass

    def tool(self):
        def decorator(func):
            return func

        return decorator

    def run(self, **_kwargs):
        return None


fake_mcp_fastmcp.FastMCP = FakeFastMCP
fake_mcp.ClientSession = object
fake_mcp_stdio.StdioServerParameters = object
fake_mcp_stdio.stdio_client = object
sys.modules.setdefault("mcp", fake_mcp)
sys.modules.setdefault("mcp.server", fake_mcp_server)
sys.modules.setdefault("mcp.server.fastmcp", fake_mcp_fastmcp)
sys.modules.setdefault("mcp.client", fake_mcp_client)
sys.modules.setdefault("mcp.client.stdio", fake_mcp_stdio)

from mcp_servers import browser_mcp


class BrowserMCPTests(unittest.TestCase):
    def test_twitter_draft_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "X_Summary.md"
            with patch.object(browser_mcp, "_social_summary_path", return_value=summary_path):
                result = asyncio.run(
                    browser_mcp.browser_post_social(
                        platform="twitter",
                        mode="draft",
                        post_text="New customer invoice completed.",
                        requires_hitl=False,
                    )
                )

            self.assertEqual(result["status"], "draft_ready")
            self.assertTrue(summary_path.exists())
            self.assertIn("New customer invoice completed.", summary_path.read_text(encoding="utf-8"))

    def test_twitter_publish_requires_credentials(self) -> None:
        with patch.dict(browser_mcp.os.environ, {}, clear=False):
            browser_mcp.os.environ.pop("TWITTER_USERNAME", None)
            browser_mcp.os.environ.pop("TWITTER_PASSWORD", None)
            with self.assertRaisesRegex(ValueError, "TWITTER_USERNAME and TWITTER_PASSWORD"):
                asyncio.run(
                    browser_mcp.browser_post_social(
                        platform="twitter",
                        mode="publish",
                        post_text="Shipping our Gold Tier automation stack.",
                        requires_hitl=False,
                    )
                )


if __name__ == "__main__":
    unittest.main()
