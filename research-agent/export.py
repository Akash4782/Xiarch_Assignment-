"""
export.py — Report export utilities for the Research Agent.

Supports two output formats:
  - Markdown (.md) — always available, no system dependencies.
  - PDF (.pdf)     — converts HTML/CSS to PDF using xhtml2pdf (100% pure Python).
                     No GTK+ or external C/C++ libraries required.
"""

import markdown
from xhtml2pdf import pisa

_PDF_STYLE = """
@page {
    size: letter;
    margin: 1in;
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #222;
}
h1, h2, h3 {
    color: #1a1a2e;
}
h2 {
    border-bottom: 0.5px solid #ddd;
    padding-bottom: 2px;
}
a {
    color: #1a0dab;
    text-decoration: none;
}
code {
    font-family: Courier, monospace;
    background-color: #f4f4f4;
}
pre {
    font-family: Courier, monospace;
    background-color: #f4f4f4;
    padding: 8px;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12px;
}
th, td {
    padding: 6px;
    border: 0.5px solid #ddd;
    text-align: left;
}
th {
    background-color: #f8f9fa;
}
"""


def export_markdown(content: str, filename: str) -> None:
    """
    Write the report content to a Markdown file.

    Parameters
    ----------
    content  : The Markdown-formatted report string.
    filename : Destination file path (e.g. 'report_topic.md').
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[*] Markdown report saved: {filename}")


def export_pdf(content: str, filename: str) -> None:
    """
    Convert the Markdown report to a styled PDF file using xhtml2pdf.

    Parameters
    ----------
    content  : The Markdown-formatted report string.
    filename : Destination file path (e.g. 'report_topic.pdf').
    """
    # Convert Markdown to HTML with Tables support extension
    html_body = markdown.markdown(content, extensions=['tables'])
    
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        {_PDF_STYLE}
    </style>
</head>
<body>
    {html_body}
</body>
</html>"""

    try:
        with open(filename, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(full_html, dest=pdf_file)
            
        if pisa_status.err:
            print(f"[!] PDF export error count: {pisa_status.err}")
        else:
            print(f"[*] PDF report saved: {filename}")
    except Exception as exc:
        print(f"[!] Failed to export PDF: {exc}")
