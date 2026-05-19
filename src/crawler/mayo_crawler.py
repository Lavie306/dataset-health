import asyncio
import time
import json
import os
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError

BASE       = "https://www.mayoclinic.org"
OUTPUT_DIR = "../../data/raw"
CONCURRENT = 5
BATCH_SIZE = 30

async def fetch(context, url, retries=3):
    for attempt in range(retries):
        page = None
        try:
            page = await context.new_page()
            await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())
            response = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            if response and response.status == 200:
                html = await page.content()
                if "Just a moment" not in html and "Cloudflare" not in html:
                    return html
                else:
                    await page.wait_for_timeout(5000)
                    return await page.content()
            elif response and response.status in [403, 429, 503]:
                await page.wait_for_timeout(3000 * (attempt + 1))
            else:
                return None
        except PlaywrightError as e:
            await asyncio.sleep(2)
        finally:
            if page:
                await page.close()
    return None

async def warmup(context):
    page = await context.new_page()
    await page.goto(BASE)
    await page.wait_for_timeout(8000)
    html = await page.content()
    await page.close()
    if "Cloudflare" in html or "Just a moment" in html:
        return False
    else:
        return True

async def get_links(context):
    all_links = []
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["0-9"]
    for letter in letters:
        url  = f"{BASE}/diseases-conditions/index?letter={letter}"
        html = await fetch(context, url)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        count_for_letter = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/diseases-conditions/" in href and "/symptoms-causes/" in href:
                full = href if href.startswith("http") else BASE + href
                all_links.append(full)
                count_for_letter += 1
    all_links = list(dict.fromkeys(all_links))
    return all_links

def extract_section(container, *keywords):
    for keyword in keywords:
        for h in container.find_all(["h2", "h3", "h4"]):
            if keyword.lower() in h.get_text().lower():
                parts = []
                for sib in h.find_next_siblings():
                    if sib.name in ["h2", "h3", "h4"]:
                        break
                    text = sib.get_text(" ", strip=True)
                    if text:
                        parts.append(text)
                result = " ".join(parts).strip()
                if len(result.split()) >= 10:
                    return result
                parts = []
                parent = h.parent
                if parent:
                    for sib in parent.find_next_siblings():
                        if sib.name in ["h2", "h3", "h4"] or sib.find(["h2", "h3", "h4"]):
                            break
                        text = sib.get_text(" ", strip=True)
                        if text:
                            parts.append(text)
                result = " ".join(parts).strip()
                if len(result.split()) >= 10:
                    return result
                wrapper = h.find_parent(["section", "article"]) or h.find_parent("div", class_=lambda
                    c: c and "content" in c.lower())
                if wrapper:
                    text_all = wrapper.get_text(" ", strip=True)
                    h_text = h.get_text(" ", strip=True)
                    if text_all.startswith(h_text):
                        text_all = text_all[len(h_text):].strip()
                    if len(text_all.split()) >= 10:
                        return text_all
    return ""

async def crawl(context, url, sem):
    async with sem:
        html = await fetch(context, url)
        if not html:
            return None
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        if "Mayo Clinic" in title:
            title = title.split("-")[0].strip()
        if not title:
            return None
        main = soup.find("article") or soup.find("div", {"id": re.compile(r"main|content", re.I)}) or soup.find(
            "main") or soup
        data = {
            "url": url,
            "disease": title,
            "overview": extract_section(main, "Overview"),
            "symptoms": extract_section(main, "Symptoms", "Signs and symptoms"),
            "causes": extract_section(main, "Causes"),
            "risk_factors": extract_section(main, "Risk factors", "Risk factor"),
            "prevention": extract_section(main, "Prevention"),
            "when_to_see_doc": extract_section(main, "When to see a doctor", "When to see a health care provider"),
        }
        has_content = any(
            len(v.split()) >= 10 for k, v in data.items()
            if isinstance(v, str) and k not in ("url", "disease")
        )
        return data if has_content else None

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        is_safe = await warmup(context)
        if not is_safe:
            await browser.close()
            return
        links = await get_links(context)
        if not links:
            await browser.close()
            return
        sem = asyncio.Semaphore(CONCURRENT)
        tasks = [crawl(context, url, sem) for url in links]
        results = []
        failed = 0
        start = time.time()
        for i in range(0, len(tasks), BATCH_SIZE):
            batch = tasks[i : i + BATCH_SIZE]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, Exception):
                    failed += 1
                elif r is not None:
                    results.append(r)
            done = min(i + BATCH_SIZE, len(tasks))
            elapsed = time.time() - start
            rate = done / elapsed if elapsed > 0 else 0
            eta = (len(tasks) - done) / rate if rate > 0 else 0
            if results and len(results) % BATCH_SIZE == 0:
                with open(f"{OUTPUT_DIR}/mayo_checkpoint.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
        with open(f"{OUTPUT_DIR}/mayo_full.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":

    asyncio.run(main())