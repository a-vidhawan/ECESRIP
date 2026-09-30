#!/usr/bin/env python3
"""Render REPORT.md to a typeset PDF via PyMuPDF's Story engine."""
import re, sys, markdown, pymupdf

src = open("REPORT.md").read()

# Story's HTML subset does not do fenced code well; convert fences to <pre>
html_body = markdown.markdown(
    src, extensions=["tables", "fenced_code", "sane_lists"])

CSS = """
body { font-family: serif; font-size: 10pt; line-height: 1.45; color: #111; }
h1 { font-family: sans-serif; font-size: 19pt; margin: 0 0 2pt 0; }
h2 { font-family: sans-serif; font-size: 12.5pt; margin: 16pt 0 5pt 0;
     border-bottom: 1px solid #bbb; padding-bottom: 2pt; }
h3 { font-family: sans-serif; font-size: 10.5pt; margin: 11pt 0 3pt 0; }
p  { margin: 0 0 6pt 0; text-align: justify; }
li { margin: 0 0 3pt 0; }
table { width: 100%; border-collapse: collapse; margin: 6pt 0 9pt 0;
        font-size: 8.6pt; }
th { font-family: sans-serif; text-align: left; border-bottom: 1.2px solid #333;
     padding: 3pt 4pt; }
td { border-bottom: 0.5px solid #ddd; padding: 3pt 4pt; }
code { font-family: monospace; font-size: 8.6pt; }
pre  { font-family: monospace; font-size: 7.6pt; line-height: 1.25;
       background: #f6f6f6; padding: 6pt; margin: 6pt 0; }
hr { border: none; border-top: 0.8px solid #ccc; margin: 10pt 0; }
strong { font-weight: bold; }
em { font-style: italic; }
"""

story = pymupdf.Story(html=f"<body>{html_body}</body>", user_css=CSS)
writer = pymupdf.DocumentWriter("REPORT.pdf")
PAGE = pymupdf.paper_rect("letter")
MARGIN = 58
frame = PAGE + (MARGIN, MARGIN, -MARGIN, -MARGIN)

n = 0
more = True
while more:
    dev = writer.begin_page(PAGE)
    more, _ = story.place(frame)
    story.draw(dev)
    writer.end_page()
    n += 1
    if n > 60:
        break
writer.close()

# stamp page numbers
doc = pymupdf.open("REPORT.pdf")
for i, page in enumerate(doc):
    page.insert_text((PAGE.width / 2 - 8, PAGE.height - 32),
                     str(i + 1), fontname="helv", fontsize=8.5)
doc.saveIncr()
print(f"wrote REPORT.pdf, {n} pages")
