"""
MedlinePlus Medical Encyclopedia Crawler
----------------------------
Dựa trên kiến trúc: anti-block headers, session warmup,
delay ngẫu nhiên, A-Z index discovery, checkpoint liên tục.
"""

import asyncio
import aiohttp
import random
import time
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE       = "https://medlineplus.gov"
OUTPUT_DIR = "../../data/raw"
CONCURRENT = 5
BATCH_SIZE = 30
DELAY_MIN  = 0.8
DELAY_MAX  = 2.2

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

def get_headers(referer=None):
    h = {
        "User-Agent":                random.choice(USER_AGENTS),
        "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language":           "en-US,en;q=0.9",
        "Accept-Encoding":           "gzip, deflate, br",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":            "document",
        "Sec-Fetch-Mode":            "navigate",
        "Sec-Fetch-Site":            "same-origin" if referer else "none",
        "Sec-Fetch-User":            "?1",
        "Cache-Control":             "max-age=0",
        "DNT":                       "1",
    }
    if referer:
        h["Referer"] = referer
    return h


# =============================================================================
# FETCH
# =============================================================================
async def fetch(session, url, retries=4, referer=None):
    timeout = aiohttp.ClientTimeout(total=30)

    for attempt in range(retries):
        await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        try:
            async with session.get(
                url, headers=get_headers(referer),
                timeout=timeout, allow_redirects=True,
            ) as res:
                if res.status == 200:
                    return await res.text()
                elif res.status == 429:
                    wait = 10 + attempt * 15
                    print(f"  [429] Rate limited, chờ {wait}s...")
                    await asyncio.sleep(wait)
                elif res.status == 403:
                    wait = 5 + attempt * 10
                    print(f"  [403] Bị block, chờ {wait}s: {url[:70]}")
                    await asyncio.sleep(wait)
                elif res.status in (404, 410):
                    return None
        except asyncio.TimeoutError:
            print(f"  [timeout] attempt {attempt+1} – {url[:60]}")
            await asyncio.sleep(3 * (attempt + 1))
        except aiohttp.ClientError as e:
            print(f"  [error] {e}")
            await asyncio.sleep(2)

    return None


# =============================================================================
# SESSION WARMUP
# =============================================================================
async def warmup(session):
    print("[+] Warming up session...")
    html = await fetch(session, BASE + "/encyclopedia.html")
    if html:
        print("[+] Warmup OK – cookie đã được set")
    else:
        print("[!] Warmup thất bại – vẫn tiếp tục")
    await asyncio.sleep(2)


# =============================================================================
# GET LINKS – MedlinePlus A-Z Encyclopedia Index
# =============================================================================
async def get_links(session):
    print("[+] Lấy danh sách link từ MedlinePlus A-Z Encyclopedia...")
    all_links = []
    # MedlinePlus dùng chữ cái in hoa cho index: encyclopedia_A.htm
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    for letter in letters:
        url  = f"{BASE}/ency/encyclopedia_{letter}.htm"
        html = await fetch(session, url, referer=f"{BASE}/encyclopedia.html")

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")

        # Link thường nằm trong thẻ <ul id="index">
        index_list = soup.find("ul", id="index")
        if index_list:
            for a in index_list.find_all("a", href=True):
                href = a["href"]
                if "article/" in href:
                    full = urljoin(url, href)
                    all_links.append(full)

        print(f"  [{letter}] → Thu thập được thêm các link, tổng: {len(all_links)}")

    all_links = list(dict.fromkeys(all_links))
    print(f"[+] Hoàn tất lấy link. Tổng số bài viết: {len(all_links)} links")
    return all_links


# =============================================================================
# EXTRACT SECTION FOR MEDLINEPLUS
# =============================================================================
def extract_section(soup, *keywords):
    """
    DOM của MedlinePlus Encyclopedia:
    <div id="section-1">
        <div class="section-title"><h2>Causes</h2></div>
        <div class="section-body" id="section-1-body"><p>...</p></div>
    </div>
    """
    for keyword in keywords:
        for h2 in soup.find_all(["h2", "h3"]):
            if keyword.lower() in h2.get_text().lower():

                # Ưu tiên tìm trong class section-body của wrapper chứa nó
                parent = h2.find_parent("section") or h2.find_parent("div", class_="section") or h2.find_parent("div", id=lambda x: x and x.startswith("section-"))

                if parent:
                    # Lấy text loại bỏ luôn text của thẻ H2 (tiêu đề)
                    body_div = parent.find("div", class_="section-body") or parent.find("div", id=lambda x: x and x.endswith("-body"))
                    if body_div:
                        return body_div.get_text(" ", strip=True)

                    # Nếu không tìm thấy class/id rõ ràng, lấy text của toàn bộ parent trừ H2
                    h2.extract() # Xóa H2 ra khỏi cây DOM tạm thời
                    return parent.get_text(" ", strip=True)

                # Fallback: Quét các thẻ anh em phía dưới (sibling traversal)
                parts = []
                for sib in h2.find_next_siblings():
                    if sib.name in ["h2", "h3", "h4", "section", "div"] and (sib.get("class") == ["section-title"] or sib.find(["h2", "h3"])):
                        break
                    text = sib.get_text(" ", strip=True)
                    if text:
                        parts.append(text)

                result = " ".join(parts).strip()
                if len(result.split()) >= 10:
                    return result
    return ""


# =============================================================================
# CRAWL 1 ARTICLE
# =============================================================================
async def crawl(session, url, sem):
    async with sem:
        html = await fetch(session, url, referer=f"{BASE}/encyclopedia.html")
        if not html:
            return None

        soup      = BeautifulSoup(html, "lxml")
        title_tag = soup.find("h1")
        title     = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            return None

        # Container chính của MedlinePlus Ency thường là <article> hoặc <div class="page-content">
        main = soup.find("article") or soup.find("div", class_="page-content") or soup.find("div", id="m-article") or soup

        data = {
            "url":                   url,
            "disease":               title,
            "overview":              extract_section(main, "Overview", "Information", "Description"),
            "symptoms":              extract_section(main, "Symptoms"),
            "causes":                extract_section(main, "Causes", "Causes, incidence, and risk factors"),
            "exams_and_tests":       extract_section(main, "Exams and Tests", "Diagnosis"),
            "treatment":             extract_section(main, "Treatment", "Medications"),
            "prognosis":             extract_section(main, "Outlook", "Prognosis"),
            "complications":         extract_section(main, "Possible Complications", "Complications"),
            "when_to_see_doc":       extract_section(main, "When to Contact a Medical Professional", "When to see a doctor"),
            "prevention":            extract_section(main, "Prevention")
        }

        # Chỉ lưu nếu ít nhất một trường quan trọng (ngoài thông tin cơ bản) có dữ liệu
        has_content = any(
            len(v.split()) >= 10
            for k, v in data.items()
            if isinstance(v, str) and k not in ("url", "disease")
        )

        return data if has_content else None


# =============================================================================
# MAIN
# =============================================================================
async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    connector = aiohttp.TCPConnector(
        limit=CONCURRENT,
        limit_per_host=3,
        ttl_dns_cache=300,
    )
    jar = aiohttp.CookieJar()

    async with aiohttp.ClientSession(connector=connector, cookie_jar=jar) as session:

        await warmup(session)
        links = await get_links(session)

        if not links:
            print("\n[!] Không lấy được link nào từ MedlinePlus.")
            return

        sem     = asyncio.Semaphore(CONCURRENT)
        tasks   = [crawl(session, url, sem) for url in links]
        results = []
        failed  = 0
        start   = time.time()

        print(f"\n[+] Bắt đầu Crawling {len(links)} bài viết (CONCURRENT={CONCURRENT})...")

        for i in range(0, len(tasks), BATCH_SIZE):
            batch         = tasks[i : i + BATCH_SIZE]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for r in batch_results:
                if isinstance(r, Exception):
                    failed += 1
                elif r is not None:
                    results.append(r)

            done    = min(i + BATCH_SIZE, len(tasks))
            elapsed = time.time() - start
            rate    = done / elapsed if elapsed > 0 else 0
            eta     = (len(tasks) - done) / rate if rate > 0 else 0

            print(f"  {done}/{len(tasks)} | ok={len(results)} "
                  f"| fail={failed} | {rate:.1f} req/s | ETA {eta/60:.1f}min")

            # Checkpoint mỗi 200 bài
            if results and len(results) % 200 < BATCH_SIZE:
                _save(results, f"{OUTPUT_DIR}/medlineplus_checkpoint.json")

    _save(results, f"{OUTPUT_DIR}/medlineplus_full.json")
    print(f"\n✅ DONE: {len(results)} articles | {failed} failed")


def _save(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → Saved {len(data)} records → {path}")


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())