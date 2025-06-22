# pip install -r requirements.txt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
import requests
import time
import random
import pandas as pd

from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = "..."  # Replace with your actual key
llm = ChatOpenAI(model="gpt-4", temperature=0.7)

def suggest_seo_improvements(title, meta_title, meta_desc):
    prompt = ChatPromptTemplate.from_template("""
You are an SEO expert. Improve the following page metadata for better SEO while keeping the meaning clear and attractive to users.

Original Title: {title}
Meta Title: {meta_title}
Meta Description: {meta_desc}

Return the improved version as:
Title: ...
Meta Title: ...
Meta Description: ...
    """)

    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "title": title or "Not Found",
        "meta_title": meta_title or "Not Found",
        "meta_desc": meta_desc or "Not Found"
    })
    return result

visited = set()
results = []

def setup_browser():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2
    }
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(options=options)

def fetch_html(url):
    driver = setup_browser()
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        return driver.page_source
    except Exception as e:
        print(f"\u274c Failed loading {url}: {e}")
        return None
    finally:
        driver.quit()

def check_status(url):
    try:
        r = requests.head(url, timeout=5, allow_redirects=True)
        return r.status_code
    except:
        return 'Error'

def extract_links(html, base_url, domain):
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    for a in soup.find_all('a', href=True):
        href = urljoin(base_url, a['href'])
        href, _ = urldefrag(href)  # Remove URL fragments
        parsed = urlparse(href)
        clean_href = parsed.scheme + "://" + parsed.netloc + parsed.path
        if domain in clean_href and clean_href.startswith("http") and not any(clean_href.endswith(ext) for ext in ['.jpg', '.png', '.pdf', '.css', '.js']):
            links.add(clean_href.rstrip('/'))
    return links

def extract_meta_content(soup, name=None, prop=None):
    if name:
        tag = soup.find("meta", attrs={"name": name})
    elif prop:
        tag = soup.find("meta", attrs={"property": prop})
    else:
        return None
    return tag.get("content", None) if tag else None

def extract_seo_data(url, html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title else 'Not Found'
    meta_title = extract_meta_content(soup, prop="og:title") or extract_meta_content(soup, name="title") or "Not Found"
    meta_description = extract_meta_content(soup, name="description") or extract_meta_content(soup, prop="og:description") or "Not Found"

    suggestions = suggest_seo_improvements(title, meta_title, meta_description)

    return {
        'url': url,
        'status': check_status(url),
        'title': title,
        'meta_title': meta_title,
        'meta_description': meta_description,
        'seo_suggestions': suggestions
    }

def crawl_website(start_url, max_pages=50):
    domain = urlparse(start_url).netloc
    to_visit = [start_url.rstrip('/')]

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue

        print(f"\n\U0001f50e Crawling: {url}")
        html = fetch_html(url)
        if not html:
            visited.add(url)
            continue

        seo_data = extract_seo_data(url, html)
        results.append(seo_data)

        internal_links = extract_links(html, url, domain)
        for link in internal_links:
            if link not in visited and link not in to_visit:
                to_visit.append(link)

        visited.add(url)

    return results

def export_to_excel(results, filename="seo_report_clean.xlsx"):
    df = pd.DataFrame(results)
    df.to_excel(filename, index=False)
    print(f"\n✅ SEO Report with Suggestions saved as '{filename}'")

if __name__ == "__main__":
    root_url = input("Enter root website URL (e.g., https://www.example.com): ").strip()
    if not root_url.startswith("http"):
        root_url = "https://" + root_url

    pages = crawl_website(root_url, max_pages=100)  # You can adjust this as needed
    export_to_excel(pages)