"""Simple FastMCP server with various tools."""

import datetime
from urllib.parse import quote_plus

import pytz
import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Information Tools")


@mcp.tool()
def get_current_time_and_date() -> str:
    """Gibt die Zeit (Datum und Uhrzeit) in Deutschland/Berlin (UTC+1) zurück.

    Returns:
        str: Die aktuelle Uhrzeit mit Datum im Format 'YYYY-MM-DD HH:MM:SS'.

    """
    return datetime.datetime.now(tz=pytz.timezone("Europe/Berlin")).strftime("%Y-%m-%d %H:%M:%S")


@mcp.tool()
def search_web(search_term: str, num_results: int = 5) -> list:
    """Führt eine Websuche mit dem angegebenen Suchbegriff durch und gibt die Ergebnisse zurück.

    Args:
        search_term (str): Der Suchbegriff
        num_results (int, optional): Anzahl der zurückzugebenden Ergebnisse. Standardwert ist 5.

    Returns:
        list: Eine Liste von Dictionaries mit den Suchergebnissen, die jeweils 'title', 'link' und 'snippet' enthalten.

    """
    encoded_search_term = quote_plus(search_term)
    headers = {
        # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa: E501
    }

    search_url = f"https://html.duckduckgo.com/html/?q={encoded_search_term}"

    try:
        response = requests.get(search_url, headers=headers, timeout=60)
        response.raise_for_status()  # Fehler bei HTTP-Statuscode != 200 auslösen
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        result_elements = soup.select(".result")

        for element in result_elements[:num_results]:
            title_element = element.select_one(".result__title")
            link_element = element.select_one(".result__url")
            snippet_element = element.select_one(".result__snippet")

            if title_element and link_element:
                title = title_element.get_text(strip=True)
                link = link_element.get("href") if link_element.get("href") else link_element.get_text(strip=True)
                snippet = snippet_element.get_text(strip=True) if snippet_element else ""

                results.append({"title": title, "link": link, "snippet": snippet})

        return results  # noqa: TRY300

    except requests.RequestException as e:
        print(f"Fehler bei der Websuche: {e}")
        return []


@mcp.tool()
def get_wikipedia_article(title: str) -> str:
    """Gibt den Inhalt eines Wikipedia-Artikels zurück.

    Args:
        title (str): Der Titel des Wikipedia-Artikels.

    Returns:
        str: Der Inhalt des Wikipedia-Artikels.

    """
    try:
        url = f"https://de.wikipedia.org/wiki/{quote_plus(title)}"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.find("div", class_="mw-parser-output").get_text()
        return content[:2000]
    except requests.RequestException as e:
        print(f"Fehler beim Abrufen des Wikipedia-Artikels: {e}")
        return ""


@mcp.tool()
def check_available_wikipedia_articles(possible_title: str) -> list[str]:
    """Überprüft, ob es Wikipedia-Artikel zu einem bestimmten Suchbegriff gibt.

    Args:
        possible_title (str): Der zu suchende Begriff.

    Returns:
        list[str]: Eine Liste von vorhandenen Artikeltiteln, die mit dem Suchbegriff übereinstimmen.

    """
    try:
        search_url = f"https://de.wikipedia.org/w/index.php?search={possible_title.replace(' ', '_')}"
        response = requests.get(search_url, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # check if redirected to page
        if "Suchergebnisse" not in soup.title.string:
            page_title = soup.find("h1", id="firstHeading").text.strip()
            return [page_title]
        search_results = []

        # Hauptsuchergebnisse finden
        results = soup.find_all("div", class_="mw-search-result-heading")
        if results:
            for result in results:
                link = result.find("a")
                if link and link.get("title"):
                    search_results.append(link.get("title"))

        # Check for "Did you mean" suggestions
        did_you_mean = soup.find("div", class_="searchdidyoumean")
        if did_you_mean:
            link = did_you_mean.find("a")
            if link and link.get("title") and link.get("title") not in search_results:
                search_results.append(link.get("title"))

        # Check for exact matches
        exact_match = soup.find("p", class_="mw-search-exists")
        if exact_match:
            link = exact_match.find("a")
            if link and link.get("title") and link.get("title") not in search_results:
                search_results.insert(
                    0,
                    link.get("title"),
                )

        return search_results  # noqa: TRY300

    except requests.RequestException as e:
        print(f"Fehler bei der Wikipedia-Suche: {e}")
        return []


if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run(transport="sse")
