import time
import re
from datetime import datetime, date
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from app_comment_sentiment.models import Article, Comment

# pip install undetected-chromedriver
# chrome version needs to be modified!
"""
undetected-chromedriver 是一個 Python 套件，用來啟動經過特殊處理的 Chrome / Chromium 瀏覽器，
目的在於「降低被網站偵測出是自動化工具（Selenium）」的機率。

它本質上是建立在 Selenium 之上，但會額外修改一些瀏覽器特徵（fingerprints），讓網站比較不容易判定你是 bot。
"""


class Command(BaseCommand):
    help = "爬取 Yahoo 政治新聞與留言並存入資料庫 (支援按日爬取與去重機制)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="目標爬取日期 (YYYY-MM-DD)，若未指定則預設為今日",
            default=timezone.localtime().date().strftime("%Y-%m-%d"),
        )
        parser.add_argument(
            "--limit", type=int, help="抓取新聞數量的上限，預設為 2 篇", default=2
        )
        parser.add_argument(
            "--min-comments", type=int, help="最少留言數限制，預設為 20 則", default=20
        )

    def handle(self, *args, **options):
        target_date_str = options["date"]
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        limit = options["limit"]
        min_comments = options["min_comments"]

        self.stdout.write(
            self.style.SUCCESS(
                f"開始爬取任務 - 目標日期: {target_date}, 目標篇數: {limit} 篇 (僅限留言數 >= {min_comments} 則)"
            )
        )

        # 初始化 Undetected WebDriver (必須一開始就開，因為首頁也需要滾動)
        self.stdout.write("初始化 Undetected WebDriver 來抓取列表與留言...")
        options_uc = uc.ChromeOptions()
        options_uc.headless = False
        driver = uc.Chrome(options=options_uc, version_main=149)
        driver.set_window_size(1920, 1080)

        try:
            # 1. 取得政治版新聞列表 URL
            politics_url = "https://tw.news.yahoo.com/politics/"
            news_urls = self.get_news_urls(driver, politics_url, min_comments)
            self.stdout.write(f"從首頁成功取得 {len(news_urls)} 個可能的新聞連結。")

            scraped_count = 0

            for url in news_urls:
                if scraped_count >= limit:
                    self.stdout.write(
                        self.style.SUCCESS(f"已達到目標篇數 {limit}，結束爬取。")
                    )
                    break

                # 2. 去重防呆：檢查資料庫是否已存在
                if Article.objects.filter(url=url).exists():
                    self.stdout.write(
                        self.style.WARNING(f"已存在於資料庫，跳過: {url}")
                    )
                    continue

                self.stdout.write(f"\n[處理中] {url}")

                # 3. 取得新聞內容與發布日期 (依然用 requests 較快)
                news_data = self.get_news_content(url)
                if not news_data:
                    self.stdout.write(self.style.ERROR("無法取得新聞內容，跳過這篇。"))
                    continue

                # 4. 日期過濾比對 (確保是當天新聞)
                if news_data["published_date"] != target_date:
                    self.stdout.write(
                        self.style.NOTICE(
                            f"日期不符跳過 ({news_data['published_date']})"
                        )
                    )
                    continue

                # 5. 使用 Selenium 檢查留言數並抓取留言
                comments = self.scrape_comments(driver, url)

                if comments is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"留言數不足 {min_comments} 則或無法解析，跳過這篇。"
                        )
                    )
                    continue

                # 6. 寫入 Django 資料庫
                try:
                    with transaction.atomic():
                        article_obj = Article.objects.create(
                            title=news_data["title"],
                            category="政治",
                            url=url,
                            published_date=news_data["published_date"],
                            content=news_data["content"],
                        )

                        comment_objects = []
                        for c in comments:
                            upvotes = int(re.sub(r"\\D", "", c["thumbsup"]) or 0)
                            downvotes = int(re.sub(r"\\D", "", c["thumbsdown"]) or 0)
                            replies = int(re.sub(r"\\D", "", c["replies"]) or 0)

                            comment_objects.append(
                                Comment(
                                    article=article_obj,
                                    content=c["text"],
                                    upvotes=upvotes,
                                    downvotes=downvotes,
                                    replies=replies,
                                )
                            )

                        if comment_objects:
                            Comment.objects.bulk_create(comment_objects)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"成功儲存！新聞: {news_data['title'][:15]}... 抓滿留言數: {len(comments)}"
                        )
                    )
                    scraped_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"資料庫儲存失敗: {e}"))

        finally:
            driver.quit()
            self.stdout.write("關閉 WebDriver。")

        self.stdout.write(
            self.style.SUCCESS(
                f"任務完成！共成功爬取並儲存 {scraped_count} 篇目標新聞。"
            )
        )

    # ==========================
    # 爬蟲輔助函數
    # ==========================
    def get_news_urls(self, driver, index_url, min_comments):
        """從 Yahoo 政治分類首頁使用 Selenium 解析外層卡片，只提取有超過指定數量留言且時間相近的新聞"""
        driver.get(index_url)
        time.sleep(3)

        # 滾動幾次以便加載更多新聞，確保庫存充足
        number_of_scrolls = 15
        for _ in range(number_of_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        urls = []
        links = driver.find_elements(By.TAG_NAME, "a")

        for l in links:
            try:
                href = l.get_attribute("href")
                if not href or ".html" not in href or "tw.news.yahoo.com" not in href:
                    continue
                if "news.yahoo.com" not in href.replace("tw.news.yahoo.com", ""):
                    # 尋找留言數標籤 <span class="comment-btn-count">XXX</span>
                    try:
                        comment_spans = l.find_elements(
                            By.XPATH,
                            ".//span[contains(@class, 'comment-btn-count')] | ..//span[contains(@class, 'comment-btn-count')]",
                        )
                        if comment_spans:
                            cnt_text = comment_spans[0].text
                            comment_count = int(re.sub(r"\\D", "", cnt_text) or 0)

                            # 判斷是否大於等於指定留言數
                            if comment_count >= min_comments and href not in urls:
                                urls.append(href)
                    except:
                        pass
            except:
                pass

        if not urls:
            self.stdout.write(
                self.style.WARNING("無法從外層解析留言數字，採用全掃描。")
            )
            for l in links:
                try:
                    href = l.get_attribute("href")
                    if href and ".html" in href and "tw.news.yahoo.com" in href:
                        if "news.yahoo.com" not in href.replace(
                            "tw.news.yahoo.com", ""
                        ):
                            if href not in urls:
                                urls.append(href)
                except:
                    pass
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"在列表頁面就成功篩選出 {len(urls)} 篇留言大於 20 的預備新聞！"
                )
            )

        return urls

    def get_news_content(self, url):
        """使用 Requests 取得新聞標題、內文與發布日期"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"
        }
        try:
            time.sleep(1)  # 禮貌性延遲
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            # 抓取標題
            title_tag = soup.find("h1")
            title = title_tag.text if title_tag else "無標題"

            # 抓取內文，並濾除推薦閱讀、延伸閱讀等雜質
            article_body = soup.find("div", class_="caas-body") or soup.find("article")
            news_paragraphs = []

            if article_body:
                for p in article_body.find_all("p"):
                    text = p.text.strip()
                    if not text or len(text) < 5:
                        continue
                    if (
                        "加入為 Google 偏好來源" in text
                        or "將 Yahoo 設為首選來源" in text
                    ):
                        continue
                    # 碰到這些結尾關鍵字就停止往下抓，過濾掉底部的其它新聞連結
                    if (
                        "看更多相關新聞" in text
                        or "更多Newtalk" in text
                        or "延伸閱讀" in text
                        or "查看原文" in text
                        or "更多新聞報導" in text
                        or "更多 NOWnews" in text
                        or "看更多新聞" in text
                    ):
                        break
                    news_paragraphs.append(text)
            else:
                # 備用方案
                for p in soup.find_all("p"):
                    text = p.text.strip()
                    if len(text) > 10 and "加入為 Google 偏好來源" not in text:
                        news_paragraphs.append(text)

            content = "\n".join(news_paragraphs)

            if not content:
                return None

            # 抓取日期
            time_tag = soup.find("time")
            pub_date = None
            if time_tag and time_tag.has_attr("datetime"):
                dt_str = time_tag["datetime"]  # ISO 格式如 "2024-05-11T12:00:00.000Z"
                dt_obj = datetime.strptime(dt_str[:10], "%Y-%m-%d")
                pub_date = dt_obj.date()
            else:
                # 若找不到時間即設定為今天 (可依需求調整)
                pub_date = timezone.localtime().date()

            return {"title": title, "content": content, "published_date": pub_date}
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Requests 訪問內文失敗: {e}"))
            return None

    def scrape_comments(self, driver, url, MIN_COMMENTS=1, MAX_COMMENTS=30):
        """使用 Selenium/UC 展開並摘取留言，若無足夠留言則回傳 None"""
        try:
            driver.get(url)
            time.sleep(3)

            # 1. 點擊展開按鈕並驗證留言數量
            try:
                # 放寬搜尋條件：可以是 div、button、span，字眼包含 '則留言' 或 '檢視留言'
                open_comment_buttons = driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), '則留言') or contains(text(), '檢視留言') or contains(text(), '留言')]",
                )

                # 試著從含有數字的按鈕中捕捉留言數
                btn_with_number = None
                for btn in open_comment_buttons:
                    try:
                        if btn.is_displayed():
                            match = re.search(r"\d+", btn.text)
                            if match:
                                btn_with_number = btn
                                btn_text = btn.text
                                break
                    except:
                        continue

                if btn_with_number:
                    comment_count = int(re.search(r"\d+", btn_text).group())
                    if comment_count < MIN_COMMENTS:
                        self.stdout.write(
                            self.style.WARNING(
                                f"    --> 僅有 {comment_count} 則留言，不符合要求數量。"
                            )
                        )
                        return None

                    # 留言數符合標準，點擊展開
                    try:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'center'});",
                            btn_with_number,
                        )
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", btn_with_number)
                        time.sleep(4)
                    except:
                        pass
                else:
                    # 如果找不到帶有數字的留言按鈕，我們直接往下滾動，確認網頁中是不是已經把留言展開了
                    existing_comments = driver.find_elements(
                        By.XPATH,
                        "//div[contains(@class, 'comment-list-item')] | //li[contains(@class, 'comment')]",
                    )
                    if not existing_comments:
                        return None  # 沒有找到留言按鈕，也沒發現直接載入的留言

            except Exception as e:
                return None

            # 2. 滾動與點擊查看更多
            max_clicks = max(5, MAX_COMMENTS // 10)
            last_height = driver.execute_script("return document.body.scrollHeight")

            for _ in range(max_clicks):
                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight - 1000);"
                )
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                # 嘗試將頁面中最後一個可能的留言元素滾動到畫面上，強制觸發懶加載
                try:
                    comments_elements = driver.find_elements(
                        By.XPATH,
                        "//div[contains(@class, 'comment-list-item')] | //li[contains(@class, 'comment')]",
                    )
                    if comments_elements:
                        driver.execute_script(
                            "arguments[0].scrollIntoView(true);", comments_elements[-1]
                        )
                        time.sleep(1)
                except:
                    pass

                try:
                    # 擴大尋找可能代表「載入更多/查看更多」的按鈕文字
                    more_buttons = driver.find_elements(
                        By.XPATH,
                        "//button[contains(text(), '顯示較多') or contains(text(), '查看更') or contains(text(), '載入更') or contains(text(), '顯示更多')]",
                    )
                    clicked = False
                    for btn in more_buttons:
                        try:
                            # 確保按鈕是可見的才點擊
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                clicked = True
                                time.sleep(2)
                                break
                        except:
                            pass

                    if not clicked:
                        new_height = driver.execute_script(
                            "return document.body.scrollHeight"
                        )
                        # 如果高度沒變，且留言數量已達標，就中斷
                        if new_height == last_height:
                            if (
                                len(
                                    driver.find_elements(
                                        By.XPATH,
                                        "//div[contains(@class, 'comment-list-item')] | //li[contains(@class, 'comment')]",
                                    )
                                )
                                >= MAX_COMMENTS
                            ):
                                break
                        last_height = new_height
                except:
                    pass

            time.sleep(3)

            # 4. 解析留言
            soup = BeautifulSoup(driver.page_source, "html.parser")
            comments = []
            seen_texts = set()

            # 嘗試找新版留言區 div.comment-list-item，如果沒有再找舊版 li.comment
            li_elements = soup.find_all(
                "div", class_=lambda c: c and "comment-list-item" in c.split()
            )
            if not li_elements:
                li_elements = soup.find_all(
                    "li", class_=lambda x: x and "comment" in x.lower()
                )

            # 避免抓到外層導覽列，做更嚴謹的篩選
            for li in li_elements:
                text_div = li.find(
                    "div",
                    class_=lambda c: c
                    and ("C(varBtsTextPrimary)" in c or "text-text-primary" in c),
                )
                if not text_div:
                    raw_text = li.get_text(separator=" ", strip=True)
                    text = (
                        raw_text.split("回覆")[0].strip()
                        if "回覆" in raw_text
                        else raw_text
                    )
                else:
                    text = text_div.get_text(separator=" ", strip=True)

                if len(text) < 2 or text in seen_texts:
                    continue

                replies = "0"
                thumbsup = "0"
                thumbsdown = "0"

                # 處理新版 (有 aria-label="xx讚" / "xx倒讚" / class="replies-button")
                for btn in li.find_all("button"):
                    btn_text = btn.get_text(strip=True)
                    aria = btn.get("aria-label", "") or ""

                    if "回覆數" in btn_text or (
                        btn.get("class") and "replies-button" in btn.get("class")
                    ):
                        m = re.search(r"\d+", btn_text)
                        if m:
                            replies = m.group()

                    if aria.endswith("讚") and not aria.endswith("倒讚"):
                        m = re.search(r"\d+", aria)
                        if m:
                            thumbsup = m.group()
                    elif aria.endswith("倒讚"):
                        m = re.search(r"\d+", aria)
                        if m:
                            thumbsdown = m.group()

                # 處理舊版 (透過 svg data-icon)
                up_svg = li.find("svg", attrs={"data-icon": "thumbsup-outline"})
                if up_svg and up_svg.parent.find("span") and thumbsup == "0":
                    thumbsup = up_svg.parent.find("span").get_text(strip=True)

                down_svg = li.find("svg", attrs={"data-icon": "thumbsdown-outline"})
                if down_svg and down_svg.parent.find("span") and thumbsdown == "0":
                    thumbsdown = down_svg.parent.find("span").get_text(strip=True)

                comments.append(
                    {
                        "text": text,
                        "replies": replies,
                        "thumbsup": thumbsup,
                        "thumbsdown": thumbsdown,
                    }
                )
                seen_texts.add(text)

                if len(comments) >= MAX_COMMENTS:
                    break

            driver.switch_to.default_content()
            return comments

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"抓取留言時發生異常: {e}"))
            try:
                driver.switch_to.default_content()
            except:
                pass
            return []
