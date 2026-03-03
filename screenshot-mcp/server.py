"""Screenshot MCP Server for blhackbox.

Provides headless browser screenshot capabilities for bug bounty PoC
documentation and evidence capture during penetration testing engagements.

Tools:
  - take_screenshot     → Capture a web page screenshot via headless Chromium
  - take_element_screenshot → Screenshot a specific element by CSS selector
  - list_screenshots    → List captured screenshots with metadata
  - annotate_screenshot → Add text/box annotations to a screenshot for PoC docs

Transport: FastMCP SSE on port 9004.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("screenshot-mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCREENSHOTS_DIR = Path(os.environ.get("SCREENSHOTS_DIR", "/tmp/screenshots"))
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

MAX_WIDTH = 3840
MAX_HEIGHT = 2160
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
NAVIGATION_TIMEOUT = int(os.environ.get("NAVIGATION_TIMEOUT", "30000"))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT_SCREENSHOTS", "3"))
MCP_PORT = int(os.environ.get("SCREENSHOT_MCP_PORT", "9004"))

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Return the concurrency semaphore, creating it inside the running loop."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    return _semaphore

# ---------------------------------------------------------------------------
# Playwright helpers
# ---------------------------------------------------------------------------

_browser = None
_playwright = None


async def _get_browser():
    """Lazily initialize a shared Chromium browser instance."""
    global _browser, _playwright
    if _browser is None or not _browser.is_connected():
        from playwright.async_api import async_playwright

        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        logger.info("Chromium browser launched (headless)")
    return _browser


def _sanitize_filename(name: str) -> str:
    """Create a safe filename from arbitrary input."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return safe[:100] or "screenshot"


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _build_output_path(url: str, suffix: str = "") -> Path:
    """Generate a unique output path based on URL and timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = _sanitize_filename(parsed.hostname or "local")
    path_part = _sanitize_filename(parsed.path.strip("/").replace("/", "_")[:40])
    name = f"{domain}_{path_part}_{ts}{suffix}.png" if path_part else f"{domain}_{ts}{suffix}.png"
    return SCREENSHOTS_DIR / name


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "screenshot-mcp",
    host="0.0.0.0",
    port=MCP_PORT,
    description=(
        "Headless browser screenshot server for bug bounty PoC evidence capture. "
        "Captures web page screenshots, element screenshots, and supports "
        "annotation for proof-of-concept documentation."
    ),
)


@mcp.tool()
async def take_screenshot(
    url: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    full_page: bool = False,
    wait_for_selector: str = "",
    wait_timeout: int = 0,
    output_path: str = "",
) -> str:
    """Capture a screenshot of a web page via headless Chromium.

    Args:
        url: Web page URL (http:// or https://)
        width: Viewport width in pixels (1-3840, default 1280)
        height: Viewport height in pixels (1-2160, default 720)
        full_page: Capture the full scrollable page (default false)
        wait_for_selector: CSS selector to wait for before capture
        wait_timeout: Extra milliseconds to wait after page load (0-30000)
        output_path: Custom output file path (optional)

    Returns:
        JSON with screenshot path, dimensions, file size, and base64-encoded image.
    """
    if not url.startswith(("http://", "https://")):
        return json.dumps({"error": "URL must start with http:// or https://"})

    width = _clamp(width, 1, MAX_WIDTH)
    height = _clamp(height, 1, MAX_HEIGHT)
    wait_timeout = _clamp(wait_timeout, 0, 30000)

    async with _get_semaphore():
        try:
            browser = await _get_browser()
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                ignore_https_errors=True,
            )
            page = await context.new_page()

            await page.goto(url, timeout=NAVIGATION_TIMEOUT, wait_until="networkidle")

            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=NAVIGATION_TIMEOUT)

            if wait_timeout > 0:
                await asyncio.sleep(wait_timeout / 1000)

            dest = Path(output_path) if output_path else _build_output_path(url)
            dest.parent.mkdir(parents=True, exist_ok=True)

            screenshot_bytes = await page.screenshot(full_page=full_page)
            dest.write_bytes(screenshot_bytes)

            title = await page.title()
            page_url = page.url

            await context.close()

            b64 = base64.b64encode(screenshot_bytes).decode("ascii")

            return json.dumps({
                "path": str(dest),
                "url": page_url,
                "title": title,
                "width": width,
                "height": height,
                "full_page": full_page,
                "file_size_bytes": len(screenshot_bytes),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "base64_png": b64[:200] + "..." if len(b64) > 200 else b64,
                "base64_length": len(b64),
            })

        except Exception as exc:
            logger.exception("Screenshot failed for %s", url)
            return json.dumps({"error": str(exc), "url": url})


@mcp.tool()
async def take_element_screenshot(
    url: str,
    selector: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    wait_timeout: int = 0,
    output_path: str = "",
) -> str:
    """Screenshot a specific page element identified by CSS selector.

    Useful for capturing specific vulnerability evidence (e.g., error messages,
    XSS payloads rendered in DOM, exposed admin panels).

    Args:
        url: Web page URL (http:// or https://)
        selector: CSS selector for the target element (e.g., '#error-msg', '.admin-panel')
        width: Viewport width in pixels (1-3840, default 1280)
        height: Viewport height in pixels (1-2160, default 720)
        wait_timeout: Extra milliseconds to wait after page load (0-30000)
        output_path: Custom output file path (optional)

    Returns:
        JSON with screenshot path, element bounding box, and file metadata.
    """
    if not url.startswith(("http://", "https://")):
        return json.dumps({"error": "URL must start with http:// or https://"})

    if not selector:
        return json.dumps({"error": "CSS selector is required"})

    width = _clamp(width, 1, MAX_WIDTH)
    height = _clamp(height, 1, MAX_HEIGHT)
    wait_timeout = _clamp(wait_timeout, 0, 30000)

    async with _get_semaphore():
        try:
            browser = await _get_browser()
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                ignore_https_errors=True,
            )
            page = await context.new_page()

            await page.goto(url, timeout=NAVIGATION_TIMEOUT, wait_until="networkidle")

            if wait_timeout > 0:
                await asyncio.sleep(wait_timeout / 1000)

            element = await page.wait_for_selector(selector, timeout=NAVIGATION_TIMEOUT)
            if element is None:
                await context.close()
                return json.dumps({
                    "error": f"Element not found: {selector}",
                    "url": url,
                })

            bbox = await element.bounding_box()

            dest = Path(output_path) if output_path else _build_output_path(url, "_element")
            dest.parent.mkdir(parents=True, exist_ok=True)

            screenshot_bytes = await element.screenshot()
            dest.write_bytes(screenshot_bytes)

            b64 = base64.b64encode(screenshot_bytes).decode("ascii")

            await context.close()

            return json.dumps({
                "path": str(dest),
                "url": url,
                "selector": selector,
                "bounding_box": bbox,
                "file_size_bytes": len(screenshot_bytes),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "base64_png": b64[:200] + "..." if len(b64) > 200 else b64,
                "base64_length": len(b64),
            })

        except Exception as exc:
            logger.exception("Element screenshot failed for %s [%s]", url, selector)
            return json.dumps({"error": str(exc), "url": url, "selector": selector})


@mcp.tool()
async def list_screenshots(limit: int = 50) -> str:
    """List captured screenshots with metadata.

    Args:
        limit: Maximum number of screenshots to return (1-200, default 50)

    Returns:
        JSON array of screenshot objects with path, size, and creation time.
    """
    limit = _clamp(limit, 1, 200)

    screenshots = sorted(
        SCREENSHOTS_DIR.glob("*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]

    results = []
    for path in screenshots:
        stat = path.stat()
        results.append({
            "path": str(path),
            "filename": path.name,
            "file_size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })

    return json.dumps({
        "total_in_directory": len(list(SCREENSHOTS_DIR.glob("*.png"))),
        "returned": len(results),
        "screenshots": results,
    })


@mcp.tool()
async def annotate_screenshot(
    screenshot_path: str,
    annotations: str,
    output_path: str = "",
) -> str:
    """Add visual annotations to a screenshot for PoC documentation.

    Supports text labels and rectangular highlight boxes to call out
    vulnerabilities, error messages, or other evidence in screenshots.

    Args:
        screenshot_path: Path to the source screenshot PNG file
        annotations: JSON array of annotation objects. Each object can be:
            - {"type": "text", "x": 10, "y": 10, "text": "XSS here!", "color": "red", "size": 20}
            - {"type": "box", "x": 100, "y": 200, "width": 300, "height": 50, "color": "red", "thickness": 3}
        output_path: Path for the annotated output (optional, auto-generated if empty)

    Returns:
        JSON with the annotated screenshot path and metadata.
    """
    src = Path(screenshot_path)
    if not src.exists():
        return json.dumps({"error": f"Screenshot not found: {screenshot_path}"})

    try:
        annotation_list = json.loads(annotations)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid annotations JSON: {exc}"})

    if not isinstance(annotation_list, list):
        return json.dumps({"error": "Annotations must be a JSON array"})

    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(src)
        draw = ImageDraw.Draw(img)

        for ann in annotation_list:
            ann_type = ann.get("type", "text")
            color = ann.get("color", "red")

            if ann_type == "text":
                x = int(ann.get("x", 10))
                y = int(ann.get("y", 10))
                text = str(ann.get("text", ""))
                size = int(ann.get("size", 20))

                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
                except OSError:
                    font = ImageFont.load_default()

                # Draw text shadow for visibility
                draw.text((x + 1, y + 1), text, fill="black", font=font)
                draw.text((x, y), text, fill=color, font=font)

            elif ann_type == "box":
                x = int(ann.get("x", 0))
                y = int(ann.get("y", 0))
                w = int(ann.get("width", 100))
                h = int(ann.get("height", 50))
                thickness = int(ann.get("thickness", 3))

                for i in range(thickness):
                    draw.rectangle(
                        [x + i, y + i, x + w - i, y + h - i],
                        outline=color,
                    )

        dest = Path(output_path) if output_path else src.with_stem(src.stem + "_annotated")
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, "PNG")

        return json.dumps({
            "path": str(dest),
            "source": str(src),
            "annotations_applied": len(annotation_list),
            "file_size_bytes": dest.stat().st_size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as exc:
        logger.exception("Annotation failed for %s", screenshot_path)
        return json.dumps({"error": str(exc), "screenshot_path": screenshot_path})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    logger.info("Starting Screenshot MCP server (%s on port %d)", transport, MCP_PORT)
    mcp.run(transport=transport)
