import requests
from bs4 import BeautifulSoup
import logging
import re
import time
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# SOURCES
# ---------------------------------------------------
SOURCES = {
    "Xinhua": "https://english.news.cn/world/index.htm",
    "Global Times": "https://www.globaltimes.cn/world/",
    "CGTN": "https://news.cgtn.com/news/world/index.html"
}

# ---------------------------------------------------
# KEYWORDS
# ---------------------------------------------------
WAR_KEYWORDS = {
    "war", "strike", "attack", "missile", "drone",
    "bomb", "retaliation", "military", "airstrike",
    "offensive", "defense", "fighter jet", "casualties",
    "naval", "rocket", "operation", "explosion",
    "ceasefire", "troops", "combat", "raid"
}

IRAN_TERMS = {
    "iran", "iranian", "irgc", "tehran", "khamenei"
}

ISRAEL_TERMS = {
    "israel", "israeli", "idf", "netanyahu"
}

US_TERMS = {
    "us", "u.s.", "united states", "america",
    "american", "washington", "pentagon", "centcom"
}

MIN_TEXT_LENGTH = 200
MAX_ARTICLES_PER_SITE = 25

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# ---------------------------------------------------
# TEXT UTILITIES
# ---------------------------------------------------
def normalize_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def relevance_score(text):

    lower = text.lower()

    score = 0

    for kw in WAR_KEYWORDS:
        if kw in lower:
            score += 2

    for kw in IRAN_TERMS:
        if kw in lower:
            score += 1

    for kw in ISRAEL_TERMS:
        if kw in lower:
            score += 1

    for kw in US_TERMS:
        if kw in lower:
            score += 1

    return score


def is_relevant(text):

    lower = text.lower()

    has_iran = any(t in lower for t in IRAN_TERMS)

    has_enemy = (
        any(t in lower for t in ISRAEL_TERMS) or
        any(t in lower for t in US_TERMS)
    )

    has_war = any(t in lower for t in WAR_KEYWORDS)

    if not (has_iran and has_enemy and has_war):
        return False

    return relevance_score(text) >= 8


# ---------------------------------------------------
# SENTENCE FILTERING
# ---------------------------------------------------
def extract_relevant_sentences(text):

    sentences = re.split(r'(?<=[.!?])\s+', text)

    filtered = []

    for sent in sentences:

        lower = sent.lower()

        has_iran = any(t in lower for t in IRAN_TERMS)

        has_enemy = (
            any(t in lower for t in ISRAEL_TERMS) or
            any(t in lower for t in US_TERMS)
        )

        has_war = any(t in lower for t in WAR_KEYWORDS)

        if has_iran and has_enemy and has_war:
            filtered.append(sent)

    return " ".join(filtered)


# ---------------------------------------------------
# FETCH ARTICLE
# ---------------------------------------------------
def fetch_full_article(url):

    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        if resp.status_code != 200:
            logger.warning(f"Bad response {resp.status_code}: {url}")
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # remove garbage
        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "aside",
            "header",
            "noscript"
        ]):
            tag.decompose()

        selectors = [
            "article",
            ".article",
            ".article-body",
            ".story-body",
            ".post-content",
            ".content",
            ".detail",
            ".news-detail",
            ".content-wrapper",
            ".text",
            "main"
        ]

        for selector in selectors:

            container = soup.select_one(selector)

            if container:

                text = container.get_text(
                    separator=' ',
                    strip=True
                )

                text = normalize_text(text)

                if len(text) >= MIN_TEXT_LENGTH:
                    return text

        # fallback
        paragraphs = soup.find_all("p")

        text = " ".join(
            p.get_text(strip=True)
            for p in paragraphs
        )

        return normalize_text(text)

    except Exception as e:
        logger.error(f"Article fetch error {url}: {e}")
        return ""


# ---------------------------------------------------
# LINK EXTRACTION
# ---------------------------------------------------
def extract_links(base_url):

    try:
        resp = requests.get(
            base_url,
            headers=HEADERS,
            timeout=15
        )

        if resp.status_code != 200:
            logger.warning(f"Cannot access {base_url}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        links = []

        for a in soup.find_all("a", href=True):

            href = a["href"]

            if href.startswith("#"):
                continue

            if "javascript:" in href:
                continue

            full_url = urljoin(base_url, href)

            patterns = [
                "/202",
                "/news/",
                "/world/",
                ".html"
            ]

            if any(p in full_url for p in patterns):

                if full_url not in links:
                    links.append(full_url)

        return links[:MAX_ARTICLES_PER_SITE]

    except Exception as e:
        logger.error(f"Link extraction error: {e}")
        return []


# ---------------------------------------------------
# CRAWLER
# ---------------------------------------------------
def crawl_and_feed():

    for source_name, source_url in SOURCES.items():

        logger.info(f" Crawling {source_name}")

        links = extract_links(source_url)

        logger.info(f" Found {len(links)} candidate links")

        for url in links:

            try:
                logger.info(f" Checking article: {url}")

                full_text = fetch_full_article(url)

                if not full_text:
                    continue

                # strict article-level filter
                if not is_relevant(full_text):
                    logger.info(" Article rejected")
                    continue

                # sentence-level filtering
                filtered_text = extract_relevant_sentences(full_text)

                if len(filtered_text) < 150:
                    logger.info(" Not enough relevant sentences")
                    continue

                logger.info(" Relevant war article accepted")

                yield filtered_text

                time.sleep(1)

            except Exception as e:
                logger.error(f"Crawl error: {e}")


# ---------------------------------------------------
# SEND TO FLASK KB
# ---------------------------------------------------
def update_knowledge_base():

    logger.info("Starting KB update cycle...")

    processed = 0
    added_total = 0

    for article_text in crawl_and_feed():

        try:
            resp = requests.post(
                "http://localhost:5000/add_text",
                json={"text": article_text},
                timeout=60
            )

            if resp.status_code != 200:
                logger.error(
                    f"API error {resp.status_code}"
                )
                continue

            result = resp.json()

            added_triplets = result.get(
                "new_triplets_added",
                []
            )

            added_count = len(added_triplets)

            if added_count > 0:

                logger.info(
                    f" Added {added_count} triplets"
                )

                added_total += added_count

            else:
                logger.info(
                    " No new triplets extracted"
                )

            processed += 1

        except Exception as e:
            logger.error(f"POST error: {e}")

    logger.info(
        f"KB update complete | "
        f"Articles processed: {processed} | "
        f"Triplets added: {added_total}"
    )