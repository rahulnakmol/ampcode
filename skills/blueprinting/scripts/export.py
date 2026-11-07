"""Render only selected packet content. No engagement traversal, cloud calls or sharing."""

import hashlib
import html
import os
from functools import lru_cache
from pathlib import Path
import re
import subprocess
import tempfile

from engagement import Invalid, digest, sync_directory
from publication import validate_packet


INK, TEAL, MUTED = "12263A", "086C75", "465766"
FONT = "Liberation Sans"


def narrative_packet(packet):
    """Present the reviewed typed estimate through the same numbers in every narrative format."""
    from estimate import office_values
    blocks = []
    for block in packet["blocks"]:
        if block["kind"] != "estimate":
            blocks.append(block)
            continue
        model = block["model"]
        values = office_values(model)
        notes = [block["notes"], "Assumptions: " + "; ".join(model["assumptions"]),
                 "Basis: " + "; ".join(model["basis"])]
        for row in model["activities"]:
            notes.append(f"{row['id']} — {row['activity']}; role: {row['role']}; basis: {row['basis']}; "
                         f"quantity: {row['quantity']}; days/unit: {row['days_per_unit_low']}–{row['days_per_unit_high']}; "
                         f"{model['currency']}/day: {row['day_rate']}; after: {', '.join(row['after']) or 'none'}.")
        notes.append(values["limitations"])
        rendered = {key: value for key, value in block.items() if key != "model"}
        rendered.update(kind="table", columns=["Measure", "Low", "High"], rows=[
            [label, *values["display"][key]] for key, label in (
                ("person_days", "Person-days"), ("base_cost", "Base " + model["currency"]),
                ("contingency_cost", "Contingency " + model["currency"]), ("total_cost", "Total " + model["currency"]))],
            text=block["text"] + f"\nRates dated {model['rate_date']}; contingency {model['contingency_percent']}%. "
                 "Cost ≠ price; effort ≠ duration.", notes="\n".join(notes))
        blocks.append(rendered)
    return dict(packet, blocks=blocks)


def table_data(block):
    if block["kind"] == "table":
        return block["columns"], block["rows"]
    return (["Category", *[s["name"] if s["name"] == block["unit"] else s["name"] + " (" + block["unit"] + ")"
                           for s in block["series"]]],
            [[category, *[str(s["values"][i]) for s in block["series"]]]
             for i, category in enumerate(block["categories"])])


def footer(block):
    return "\n".join([*block["caveats"], "Source: " + "; ".join(c["label"] for c in block["citations"])])


def markdown(packet, path):
    def escape(value):
        return re.sub(r"([\\`*_{}\[\]()#!|>])", r"\\\1", html.escape(value, quote=False)).replace("\n", "<br>")
    lines = ["# " + escape(packet["title"]), ""]
    for block in packet["blocks"]:
        lines += ["## " + escape(block["title"]), "", escape(block["text"]), ""]
        if block["kind"] != "text":
            columns, rows = table_data(block)
            lines += [" | ".join(map(escape, columns)), " | ".join("---" for _ in columns)]
            lines += [" | ".join(map(escape, row)) for row in rows]
            lines.append("")
        lines += [escape(footer(block)), ""]
        if block["notes"]:
            lines += ["### Speaker notes", "", escape(block["notes"]), ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def document(packet, path):
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc = Document()
    doc.core_properties.title = packet["title"]
    doc.core_properties.author = ""
    doc.core_properties.language = "en"
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Inches(0.7)
        section.left_margin = section.right_margin = Inches(0.8)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = FONT, Pt(11)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(8)
    for style in ("Title", "Heading 1", "Heading 2"):
        doc.styles[style].font.name = FONT
        doc.styles[style].font.color.rgb = RGBColor.from_string(INK)
    doc.add_heading(packet["title"], 0)
    for block in packet["blocks"]:
        doc.add_heading(block["title"], 1)
        doc.add_paragraph(block["text"])
        if block["kind"] != "text":
            columns, rows = table_data(block)
            table = doc.add_table(rows=1, cols=len(columns))
            table.style = "Light Shading Accent 1"
            for cell, value in zip(table.rows[0].cells, columns):
                cell.text = value
            header = OxmlElement("w:tblHeader")
            table.rows[0]._tr.get_or_add_trPr().append(header)
            for values in rows:
                for cell, value in zip(table.add_row().cells, values):
                    cell.text = value
            for row in table.rows:
                row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        doc.add_paragraph(footer(block))
        if block["notes"]:
            doc.add_heading("Speaker notes", 2)
            doc.add_paragraph(block["notes"])
    # Explicit language for assistive readers, beyond document properties.
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "en-US")
    normal.element.get_or_add_rPr().append(lang)
    doc.save(path)


def presentation(packet, path):
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_CONNECTOR
    from pptx.util import Inches, Pt
    from PIL import ImageFont
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    deck.core_properties.title, deck.core_properties.author = packet["title"], ""

    @lru_cache(maxsize=16)
    def font(size, bold):
        match = subprocess.run(["fc-match", "-f", "%{family}\n%{file}", FONT + (":style=Bold" if bold else ":style=Regular")],
                               capture_output=True, text=True, check=True, timeout=10).stdout.splitlines()
        if len(match) != 2 or match[0] != FONT:
            raise Invalid("Install Liberation Sans fonts before exporting slides")
        return ImageFont.truetype(match[1], size * 2)

    def fits(value, width, height, size, bold=False):
        face = font(size, bold)
        available, lines = width * 72, 0
        for paragraph in value.split("\n"):
            used = 0
            lines += 1
            for word in paragraph.split():
                length = face.getlength(word + " ") / 2
                if length > available:
                    raise Invalid("Slide text has an unbreakable word wider than its box; revise and review the packet")
                if used and used + length > available:
                    lines += 1
                    used = 0
                used += length
        if lines * size * 1.2 > height * 72:
            raise Invalid("Slide text would overflow; split and review the packet rather than shrink or omit it")

    def style(frame, size, color=INK, bold=False):
        frame.word_wrap = True
        frame.vertical_anchor = MSO_ANCHOR.TOP
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        for p in frame.paragraphs:
            p.alignment = PP_ALIGN.LEFT
            p.font.name, p.font.size, p.font.bold = FONT, Pt(size), bold
            p.font.color.rgb = RGBColor.from_string(color)
            p.space_after = Pt(0)

    def box(slide, x, y, w, h, value, size=24, color=INK, bold=False):
        fits(value, w, h, size, bold)
        shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        shape.text_frame.text = value
        style(shape.text_frame, size, color, bold)
        return shape

    for i, block in enumerate(packet["blocks"], 1):
        # Refuse dense content rather than shrinking type or silently dropping text.
        if (len(block["title"]) > 105 or len(block["text"]) > 420
                or len(footer(block)) > 240 or len(block["notes"]) > 4000):
            raise Invalid(f"{block['id']}: too dense for the slide layout; split and review the packet")
        slide = deck.slides.add_slide(deck.slide_layouts[5])
        title = slide.shapes.title
        title.left, title.top, title.width, title.height = map(Inches, (0.65, 0.65, 12, 1.15))
        title.text = block["title"]
        fits(block["title"], 12, 1.15, 34, True)
        style(title.text_frame, 34, INK, True)
        box(slide, 0.65, 0.15, 11.4, 0.35, packet["title"], 12, MUTED)
        box(slide, 12, 0.15, 0.6, 0.35, f"{i:02d}", 12, MUTED)
        line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0.65), Inches(1.9), Inches(12.6), Inches(1.9))
        line.line.color.rgb, line.line.width = RGBColor.from_string(TEAL), Pt(1.5)
        if block["kind"] == "text":
            box(slide, 0.65, 2.35, 11.95, 3.6, block["text"], 26)
        elif block["kind"] == "table":
            columns, rows = table_data(block)
            if len(columns) > 4 or len(rows) > 6 or any(len(v) > 80 for row in [columns, *rows] for v in row):
                raise Invalid(f"{block['id']}: table too dense; split and review the packet")
            box(slide, 0.7, 2.1, 11.9, 0.9, block["text"], 24)
            height = min(2.8, 0.65 * (len(rows) + 1))
            shape = slide.shapes.add_table(len(rows) + 1, len(columns), Inches(0.7), Inches(3.1), Inches(11.9), Inches(height))
            shape._element.xpath(".//p:cNvPr")[0].set("descr", block["text"])
            for r, values in enumerate([columns, *rows]):
                for c, value in enumerate(values):
                    fits(value, 11.9 / len(columns) - 0.2, height / (len(rows) + 1) - 0.1, 20, r == 0)
                    cell = shape.table.cell(r, c)
                    cell.text = value
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor.from_string(INK if r == 0 else ("EDF4F4" if r % 2 else "FFFFFF"))
                    style(cell.text_frame, 20, "FFFFFF" if r == 0 else INK, r == 0)
            bottom = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0.7), Inches(3.1 + height), Inches(12.6), Inches(3.1 + height))
            bottom.line.color.rgb, bottom.line.width = RGBColor.from_string(MUTED), Pt(0.75)
        else:
            if len(block["categories"]) > 7 or len(block["series"]) > 3:
                raise Invalid(f"{block['id']}: chart too dense; split and review the packet")
            for label in block["categories"]:
                fits(label, 6.3 / len(block["categories"]), 0.8, 18)
            fits(block["unit"], 3, 0.4, 16)
            for series in block["series"]:
                fits(series["name"], 6.3 / len(block["series"]), 0.4, 16)
                for value in series["values"]:
                    fits(str(value), 0.7 * 6.3 / (len(block["categories"]) * len(block["series"])), 0.35, 18)
                    fits(str(value), 0.8, 0.35, 18)
            box(slide, 0.7, 2.35, 4.2, 3.6, block["text"], 26)
            data = CategoryChartData()
            data.categories = block["categories"]
            for series in block["series"]:
                data.add_series(series["name"], series["values"])
            shape = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(5.1), Inches(2.25), Inches(7.5), Inches(3.8), data)
            shape._element.xpath(".//p:cNvPr")[0].set("descr", block["text"] + " Values are in the speaker notes.")
            chart = shape.chart
            chart.has_title = False
            chart.has_legend = len(block["series"]) > 1
            if chart.has_legend:
                chart.legend.position = XL_LEGEND_POSITION.BOTTOM
                chart.legend.font.size = Pt(16)
            values = [v for series in block["series"] for v in series["values"]]
            chart.value_axis.minimum_scale = min(0, min(values))
            chart.value_axis.maximum_scale = max(0, max(values)) if max(values) > 0 else 1
            chart.value_axis.has_title = True
            chart.value_axis.axis_title.text_frame.text = block["unit"]
            style(chart.value_axis.axis_title.text_frame, 16, MUTED)
            for axis in (chart.category_axis, chart.value_axis):
                axis.tick_labels.font.name, axis.tick_labels.font.size = FONT, Pt(18)
            plot = chart.plots[0]
            plot.has_data_labels = True
            plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
            plot.data_labels.font.size = Pt(18)
            for series, color in zip(chart.series, (TEAL, INK, "6D7680")):
                series.format.fill.solid()
                series.format.fill.fore_color.rgb = RGBColor.from_string(color)
        box(slide, 0.7, 6.25, 11.9, 1.0, footer(block), 16, MUTED)
        notes = [block["notes"], footer(block)]
        if block["kind"] != "text":
            columns, rows = table_data(block)
            notes.extend(" | ".join(row) for row in [columns, *rows])
        slide.notes_slide.notes_text_frame.text = "\n\n".join(notes)
    deck.save(path)


def render(packet, format, output):
    validate_packet(packet)
    output = Path(output).absolute()
    suffix = ".pdf" if format.startswith("pdf-") else "." + format
    if output.suffix.lower() != suffix or output.exists() or output.is_symlink():
        raise Invalid("Use a new output path with the matching format extension")
    with tempfile.TemporaryDirectory(prefix=".blueprint-export-", dir=output.parent) as temporary:
        base = Path(temporary)
        source_format = {"pdf-document": "docx", "pdf-deck": "pptx"}.get(format, format)
        source = base / ("content." + source_format)
        try:
            {"md": markdown, "docx": document, "pptx": presentation}[source_format](narrative_packet(packet), source)
        except ImportError as error:
            raise Invalid("Install scripts/export-requirements.txt in an isolated Python environment") from error
        renderer = None
        if format.startswith("pdf-"):
            renderer = subprocess.run(["libreoffice", "--version"], capture_output=True, text=True, check=True).stdout.strip()
            if not renderer.startswith("LibreOffice 7.4.7.2 "):
                raise Invalid("PDF rendering needs pinned LibreOffice 7.4.7.2; qualify a new version before changing this pin")
            filter_name = "writer_pdf_Export" if source_format == "docx" else "impress_pdf_Export"
            pdf_filter = 'pdf:' + filter_name + ':{"UseTaggedPDF":{"type":"boolean","value":"true"}}'
            subprocess.run(["libreoffice", "-env:UserInstallation=" + (base / "profile").as_uri(), "--headless",
                            "--convert-to", pdf_filter, "--outdir", str(base), str(source)],
                           capture_output=True, text=True, check=True, timeout=90)
            source = base / "content.pdf"
            if not source.is_file() or not source.read_bytes().startswith(b"%PDF-"):
                raise Invalid("Renderer did not produce a PDF")
        with source.open("rb") as stream:
            os.fsync(stream.fileno())
        os.link(source, output)
        sync_directory(output.parent)
    return {"output": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "packet_hash": digest(packet), "renderer": renderer, "status": "exported-not-delivered",
            "limitations": "Local artifact only; inspect rendering, meaning and editability before sharing. Not a client decision or delivery receipt."}
