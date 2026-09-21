from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Decide Websites that I would like my agent to visit
websites = [
    "https://www.cdc.gov/index.html"
]


#print(vault)
#print(vault.exists())

# Get Journal Entries
for site in websites:
    web_data = requests.get(site)
    page = BeautifulSoup(web_data.text, "html.parser")

    # Add links to page
    for link in page.find_all("a"):
        href = link.get("href")

        if href:
            full_url = urljoin(site, href)
            link_text = link.get_text(" ", strip=True)

            link.replace_with(f"{link_text} [{full_url}]")

non_html_page = page.get_text(separator="\n", strip=True)

#print(non_html_page)

'''
# Design the prompt for the model to use
prompt = f"""
Read the following webpage.

Suggest:
1. A short summary
2. 3-5 useful tags
3. Important topics mentioned


{non_html_page}
"""
'''

prompt = f"""
Read the following webpage.

Then:
Identify the articles abpout important news.
Return the title and URL of each relevant article.


{non_html_page}
"""


# Makes a request to the ollama localhost.
response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "gemma3:4b",
        "prompt": prompt,
        "stream": False # Ollama waits until the entire response is finished before sending back the JSON Object
    }
)

result = response.json()

print(result["response"])
