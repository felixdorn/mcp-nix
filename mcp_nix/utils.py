# SPDX-License-Identifier: GPL-3.0-or-later
from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    """Extract text from HTML using BeautifulSoup."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ").strip()
