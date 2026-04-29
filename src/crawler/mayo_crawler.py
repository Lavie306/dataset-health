"""
Mayo Clinic Disease Crawler (Playwright Edition)
----------------------------
Lõi: Sử dụng Playwright (Trình duyệt thật) để vượt 100% Cloudflare/Akamai 503 JS Challenge.
Kiến trúc: Auto Warmup (lấy cookie thông hành), Đa luồng (Multiple Tabs), Checkpoint.
"""

import asyncio
import time
import json
import os
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError

BASE       = "https://www.mayoclinic.org"
OUTPUT_DIR = "../../data/raw"
CONCURRENT = 5  # Số tab chạy cùng lúc (Tùy RAM máy bạn, 5 là an toàn)
BATCH_SIZE = 30

# =============================================================================
# FETCH BẰNG PLAYWRIGHT
# =============================================================================
async def fetch(context, url, retries=3):
    """Mở một tab mới, tải HTML và đóng tab."""
    for attempt in range(retries):
        page = None
        try:
            page = await context.new_page()

            # Chặn tải hình ảnh, font, css để tăng tốc độ cào dữ liệu gấp 3 lần
            await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())

            # domcontentloaded: Chờ HTML tải xong (Không chờ tải ảnh/quảng cáo)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=25000)

            if response and response.status == 200:
                html = await page.content()
                if "Just a moment" not in html and "Cloudflare" not in html:
                    return html
                else:
                    print(f"  [!] Đụng CAPTCHA ở {url}, chờ 5s để tự giải...")
                    await page.wait_for_timeout(5000) # Đợi JS Challenge chạy
                    return await page.content()
            elif response and response.status in [403, 429, 503]:
                print(f"  [{response.status}] Đang bị chặn, thử lại lần {attempt+1}...")
                await page.wait_for_timeout(3000 * (attempt + 1))
            else:
                return None

        except PlaywrightError as e:
            print(f"  [Lỗi Mạng/Timeout] {url[:50]}: {str(e).splitlines()[0]}")
            await asyncio.sleep(2)
        finally:
            if page:
                await page.close()

    return None

# =============================================================================
# WARMUP (LẤY THẺ THÔNG HÀNH CHỐNG BOT)
# =============================================================================
async def warmup(context):
    print("[+] WARMUP: Đang mở trang chủ Mayo Clinic để vượt tường lửa...")
    page = await context.new_page()
    await page.goto(BASE)

    # Dừng lại 8 giây ở trang chủ.
    # NẾU BẠN THẤY HIỆN MÀN HÌNH BẮT TÍCH VÀO Ô "I AM HUMAN", HÃY DÙNG CHUỘT TÍCH VÀO NGAY NHÉ!
    print("[!] Vui lòng nhìn cửa sổ trình duyệt. Đang chờ 8s để lấy thẻ thông hành...")
    await page.wait_for_timeout(8000)

    html = await page.content()
    await page.close()

    if "Cloudflare" in html or "Just a moment" in html:
        print("🚨 THẤT BẠI: Vẫn bị kẹt ở màn hình chống Bot. Hãy thử bật VPN.")
        return False
    else:
        print("✅ THÀNH CÔNG: Đã lấy được Cookie an toàn!")
        return True

# =============================================================================
# GET LINKS (CHỈ TỪ A-Z ĐỂ NHANH)
# =============================================================================
async def get_links(context):
    print("[+] Đang quét các Link bài viết từ A-Z...")
    all_links = []
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["0-9"]

    # Quét tuần tự để tránh bị block ban đầu
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

        print(f"  [{letter}] → Thu thập {count_for_letter} bài")

    all_links = list(dict.fromkeys(all_links))
    print(f"[+] Hoàn tất: {len(all_links)} links hợp lệ")
    return all_links

# =============================================================================
# EXTRACT SECTION & CRAWL ARTICLE
# =============================================================================
# =============================================================================
# EXTRACT SECTION (Đã nâng cấp thuật toán quét DOM nhiều tầng)
# =============================================================================
def extract_section(container, *keywords):
    for keyword in keywords:
        for h in container.find_all(["h2", "h3", "h4"]):
            if keyword.lower() in h.get_text().lower():

                # Chiến lược 1: Thẻ văn bản nằm CÙNG CẤP với thẻ H2
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

                # Chiến lược 2: Thẻ H2 bị bọc trong 1 div riêng lẻ, văn bản nằm dưới div đó
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

                # Chiến lược 3: Thẻ H2 và nội dung nằm chung trong 1 <section> / <div> lớn (Box-model)
                wrapper = h.find_parent(["section", "article"]) or h.find_parent("div", class_=lambda
                    c: c and "content" in c.lower())
                if wrapper:
                    text_all = wrapper.get_text(" ", strip=True)
                    h_text = h.get_text(" ", strip=True)
                    # Xóa phần tiêu đề bị lặp lại ở đầu chuỗi
                    if text_all.startswith(h_text):
                        text_all = text_all[len(h_text):].strip()
                    if len(text_all.split()) >= 10:
                        return text_all

    return ""


# =============================================================================
# CRAWL 1 ARTICLE
# =============================================================================
async def crawl(context, url, sem):
    async with sem:
        html = await fetch(context, url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")

        # Bắt Title linh hoạt hơn nếu Mayo Clinic đổi thẻ H1
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        if "Mayo Clinic" in title:
            title = title.split("-")[0].strip()  # Xóa chữ " - Mayo Clinic" ở đuôi

        if not title:
            return None

        # Container lấy dữ liệu bao quát hơn
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

        # Nới lỏng điều kiện duyệt: Chỉ cần có >= 10 từ (thay vì 15) ở bất kỳ trường nào ngoài url, disease
        has_content = any(
            len(v.split()) >= 10 for k, v in data.items()
            if isinstance(v, str) and k not in ("url", "disease")
        )
        return data if has_content else None

# =============================================================================
# MAIN LUỒNG ĐIỀU KHIỂN
# =============================================================================
async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with async_playwright() as p:
        # headless=False: Bật giao diện để bạn nhìn thấy trình duyệt làm gì
        # Khi nào chạy ổn định, bạn có thể đổi thành True để nó chạy ngầm
        browser = await p.chromium.launch(headless=False)

        # Thiết lập giả lập máy tính bình thường
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )

        # 1. Đi qua bài kiểm tra bảo mật
        is_safe = await warmup(context)
        if not is_safe:
            await browser.close()
            return

        # 2. Lấy danh sách URL
        links = await get_links(context)
        if not links:
            await browser.close()
            return

        # 3. Cào chi tiết dữ liệu đa luồng
        sem = asyncio.Semaphore(CONCURRENT)
        tasks = [crawl(context, url, sem) for url in links]
        results = []
        failed = 0
        start = time.time()

        print(f"\n[+] Bắt đầu cào {len(links)} bài viết (CONCURRENT={CONCURRENT} tabs)...")

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

            print(f"  {done}/{len(tasks)} | ok={len(results)} | fail={failed} | {rate:.1f} req/s | ETA {eta/60:.1f}min")

            if results and len(results) % BATCH_SIZE == 0:
                with open(f"{OUTPUT_DIR}/mayo_checkpoint.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

        with open(f"{OUTPUT_DIR}/mayo_full.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ HOÀN TẤT: Lưu thành công {len(results)} bài viết!")
        await browser.close()

if __name__ == "__main__":

    asyncio.run(main())