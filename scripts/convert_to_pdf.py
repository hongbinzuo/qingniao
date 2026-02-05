"""
Convert BTC Trading Signal Report from Markdown to PDF
"""

from pathlib import Path

import markdown
from weasyprint import CSS, HTML


def convert_md_to_pdf():
    # Read markdown file
    md_file = Path("BTC_Trading_Signal_Report.md")
    pdf_file = Path("BTC_Trading_Signal_Report.pdf")

    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(md_content, extensions=["tables", "fenced_code"])

    # Add CSS styling
    css_style = """
    @page {
        size: A4;
        margin: 2cm;
    }
    body {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #333;
    }
    h1 {
        color: #1a1a1a;
        font-size: 24pt;
        border-bottom: 3px solid #0066cc;
        padding-bottom: 10px;
        margin-top: 20px;
    }
    h2 {
        color: #0066cc;
        font-size: 18pt;
        margin-top: 25px;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 5px;
    }
    h3 {
        color: #0066cc;
        font-size: 14pt;
        margin-top: 20px;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 10px;
        text-align: left;
    }
    th {
        background-color: #0066cc;
        color: white;
        font-weight: bold;
    }
    tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    strong {
        color: #0066cc;
    }
    hr {
        border: none;
        border-top: 2px solid #e0e0e0;
        margin: 20px 0;
    }
    ul, ol {
        margin: 10px 0;
        padding-left: 30px;
    }
    li {
        margin: 5px 0;
    }
    """

    # Wrap HTML with proper structure
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>BTC Trading Signal Report</title>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Convert to PDF
    HTML(string=full_html).write_pdf(pdf_file, stylesheets=[CSS(string=css_style)])

    print(f"[SUCCESS] PDF generated: {pdf_file}")
    print(f"[INFO] File size: {pdf_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    convert_md_to_pdf()
