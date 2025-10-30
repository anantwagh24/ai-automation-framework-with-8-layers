from typing import Optional, List
from pathlib import Path
from datetime import datetime
import time
from playwright.async_api import async_playwright
from typing import List, Optional, Tuple

class BrowserController:
    def __init__(self, headless: bool = False, slow_mo: Optional[int] = 100, shots_dir: str = "files/shots"):
        self.headless = headless
        self.slow_mo = slow_mo
        self._pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.shots_dir = Path(shots_dir); self.shots_dir.mkdir(parents=True, exist_ok=True)

    async def launch(self):
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def goto(self, url: str):
        await self.page.goto(url, wait_until="domcontentloaded")

    async def wait_network_idle(self, t: int = 4000):
        try:
            await self.page.wait_for_load_state("networkidle", timeout=t)
        except Exception:
            await self.page.wait_for_timeout(min(1500, t))

    async def settle(self, ms: int = 800):
        await self.page.wait_for_timeout(ms)

    async def wait_processing_done(self, timeout_ms: int = 8000):
        try:
            loc = self.page.get_by_text("Please wait while I process", exact=False)
            if await loc.count():
                try:
                    await loc.first.wait_for(state="hidden", timeout=timeout_ms)
                    return
                except Exception:
                    pass
        except Exception:
            pass
        await self.page.wait_for_timeout(min(1500, timeout_ms))

    def _send_button(self):
        btn = self.page.locator("button[aria-label='Send message']").first
        if btn:
            return btn
        return self.page.get_by_role("button", name="Send message").first

    async def wait_send_enabled(self, timeout_ms: int = 5000) -> bool:
        deadline = time.monotonic() + (timeout_ms / 1000.0)
        btn = self._send_button()
        try:
            if await btn.count():
                await btn.wait_for(state="visible", timeout=min(timeout_ms, 2000))
        except Exception:
            pass
        while time.monotonic() < deadline:
            try:
                if await btn.count() and await btn.is_enabled():
                    return True
            except Exception:
                pass
            await self.page.wait_for_timeout(100)
        return False

    async def try_send_message(self, message: str, prefer_button: bool = True) -> bool:
        selectors = ['textarea', 'input[type="text"]', '[contenteditable="true"]', 'div[role="textbox"]']
        focused = False
        for sel in selectors:
            loc = self.page.locator(sel).first
            if await loc.count():
                try:
                    await loc.click()
                    try:
                        await loc.fill("")
                        await loc.type(message)
                    except Exception:
                        await self.page.keyboard.type(message)
                    focused = True
                    break
                except Exception:
                    continue
        if not focused:
            return False

        btn = self._send_button()
        has_button = await btn.count() > 0
        if prefer_button and has_button:
            if await self.wait_send_enabled(timeout_ms=5000):
                try:
                    await btn.click()
                    return True
                except Exception:
                    try:
                        await self.page.keyboard.press("Enter")
                        return True
                    except Exception:
                        return False
            return False

        try:
            await self.page.keyboard.press("Enter")
            return True
        except Exception:
            return False

    # Replace list_buttons() with a richer collector
    async def list_buttons(self) -> List[str]:
        labels: List[str] = []

        # 1) Real buttons + anchors with button role
        buckets = [
            self.page.get_by_role("button"),
            self.page.get_by_role("link"),  # many CTAs are <a>
        ]
        for loc in buckets:
            try:
                n = await loc.count()
                for i in range(n):
                    el = loc.nth(i)
                    if not await el.is_visible():
                        continue
                    txt = (await el.inner_text()).strip()
                    if not txt:
                        # fallbacks: aria-label / title
                        txt = (await el.get_attribute("aria-label") or "").strip() \
                              or (await el.get_attribute("title") or "").strip()
                    if txt:
                        labels.append(txt)
            except Exception:
                pass

        # 2) Inputs that act like buttons (submit)
        css = self.page.locator("input[type='submit'], input[type='button']")
        try:
            n = await css.count()
            for i in range(n):
                el = css.nth(i)
                if not await el.is_visible():
                    continue
                txt = (await el.get_attribute("value") or "").strip()
                if not txt:
                    txt = (await el.get_attribute("aria-label") or "").strip() \
                          or (await el.get_attribute("title") or "").strip()
                if txt:
                    labels.append(txt)
        except Exception:
            pass

        # 3) Labels that are clickable (radios/checkbox groups)
        lab = self.page.locator("label")
        try:
            n = await lab.count()
            for i in range(n):
                el = lab.nth(i)
                if not await el.is_visible():
                    continue
                txt = (await el.inner_text()).strip()
                if txt:
                    labels.append(txt)
        except Exception:
            pass

        # dedupe preserving order
        seen = set()
        out = []
        for t in labels:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out

    # Make current_buttons() pull y-positions for links/labels too
    async def _collect_visible_buttons_with_y(self) -> List[Tuple[str, float]]:
        items = []

        def _push(label: str, box):
            if label and box:
                cy = box["y"] + box["height"] / 2.0
                items.append((label, cy))

        # buttons + links
        for role in ("button", "link"):
            try:
                loc = self.page.get_by_role(role)
                n = await loc.count()
                for i in range(n):
                    el = loc.nth(i)
                    if not await el.is_visible():
                        continue
                    label = (await el.inner_text()).strip()
                    if not label:
                        label = (await el.get_attribute("aria-label") or "").strip() \
                                or (await el.get_attribute("title") or "").strip()
                    _push(label, await el.bounding_box())
            except Exception:
                pass

        # inputs as buttons
        css = self.page.locator("input[type='submit'], input[type='button']")
        n = await css.count()
        for i in range(n):
            el = css.nth(i)
            if not await el.is_visible():
                continue
            label = (await el.get_attribute("value") or "").strip() \
                    or (await el.get_attribute("aria-label") or "").strip() \
                    or (await el.get_attribute("title") or "").strip()
            _push(label, await el.bounding_box())

        # clickable labels
        lab = self.page.locator("label")
        n = await lab.count()
        for i in range(n):
            el = lab.nth(i)
            if not await el.is_visible():
                continue
            label = (await el.inner_text()).strip()
            _push(label, await el.bounding_box())

        # keep only bottom cluster (last ~220px band)
        best = {}
        for lab, cy in items:
            best[lab] = max(cy, best.get(lab, -1e9))
        pairs = [(lab, cy) for lab, cy in best.items()]
        if not pairs:
            return []
        pairs.sort(key=lambda t: t[1])
        max_y = pairs[-1][1]
        return [(lab, cy) for lab, cy in pairs if (max_y - cy) <= 220]
    async def click_button_by_text(self, text: str, exact: bool = True) -> bool:
        target = self.page.get_by_role("button", name=text, exact=exact)
        if await target.count():
            await target.first.click()
            return True
        return False

    async def current_buttons(self) -> List[str]:
        return await self.list_buttons()

    async def screenshot(self, name_prefix: str = "shot") -> str:
        p = self.shots_dir / f"{name_prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        await self.page.screenshot(path=str(p))
        return str(p)

    async def screenshot(self, name: str):
        path = f"files/screenshots/{name}.png"
        await self.page.screenshot(path=path)
        return path

    # In BrowserController
    async def scroll_down(self, px: int = 800):
        await self.page.mouse.wheel(0, px)
        await self.settle(200)

    async def click_button_by_text(self, text: str, exact: bool = True) -> bool:
        # existing logic first...
        # if it fails, try a text locator and JS click
        try:
            needle = text if exact else f"{text}"
            loc = self.page.locator(f"text={needle}").first
            if await loc.count():
                try:
                    await loc.scroll_into_view_if_needed()
                except Exception:
                    pass
                try:
                    await loc.click()
                    return True
                except Exception:
                    # JS force click
                    try:
                        await loc.evaluate("(el) => el.click()")
                        return True
                    except Exception:
                        pass
        except Exception:
            pass
        return False

    async def close(self):
        try:
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
        finally:
            if self._pw: await self._pw.stop()
