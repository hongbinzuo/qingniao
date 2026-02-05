"""
Generate HTML report from markdown that can be printed to PDF
"""

import re
from pathlib import Path


def md_to_html_simple(md_content):
    """Simple markdown to HTML converter"""
    html = md_content

    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Bold
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

    # Horizontal rules
    html = re.sub(r"^---$", r"<hr>", html, flags=re.MULTILINE)

    # Lists
    lines = html.split("\n")
    in_list = False
    result = []

    for line in lines:
        if line.strip().startswith("- "):
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append(f"<li>{line.strip()[2:]}</li>")
        elif line.strip().startswith(("1. ", "2. ", "3. ", "4. ")):
            if not in_list:
                result.append("<ol>")
                in_list = True
            result.append(f"<li>{line.strip()[3:]}</li>")
        else:
            if in_list:
                result.append("</ul>" if result[-1].startswith("<li>") else "</ol>")
                in_list = False
            result.append(line)

    if in_list:
        result.append("</ul>")

    html = "\n".join(result)

    # Paragraphs
    html = re.sub(r"\n\n", "</p><p>", html)

    return html


def convert_table(table_text):
    """Convert markdown table to HTML"""
    lines = [l.strip() for l in table_text.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return table_text

    html = "<table>\n<thead>\n<tr>\n"

    # Header
    headers = [h.strip() for h in lines[0].split("|") if h.strip()]
    for h in headers:
        html += f"<th>{h}</th>\n"
    html += "</tr>\n</thead>\n<tbody>\n"

    # Rows (skip separator line)
    for line in lines[2:]:
        cells = [c.strip() for c in line.split("|") if c.strip()]
        html += "<tr>\n"
        for c in cells:
            html += f"<td>{c}</td>\n"
        html += "</tr>\n"

    html += "</tbody>\n</table>\n"
    return html


# Read markdown
md_file = Path("BTC_Trading_Signal_Report.md")
with open(md_file, "r", encoding="utf-8") as f:
    md_content = f.read()

# Extract and convert table
table_match = re.search(r"\| Metric \|.+?\n\|.+?\n(\|.+?\n)+", md_content, re.DOTALL)
if table_match:
    table_md = table_match.group(0)
    table_html = convert_table(table_md)
    md_content = md_content.replace(table_md, "{{TABLE}}")
else:
    table_html = ""

# Convert markdown to HTML
html_body = md_to_html_simple(md_content)
if table_html:
    html_body = html_body.replace("{{TABLE}}", table_html)

print("[INFO] HTML conversion completed")
print(f"[INFO] Output length: {len(html_body)} characters")
