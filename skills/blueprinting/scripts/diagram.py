"""Bounded evidence-linked diagrams and native Office mappings. No executable layout input."""

from functools import lru_cache
import subprocess

from engagement import Invalid, identifier
from qualification import text


DIRECTIONS = {
    "sequence": "preceding step -> following step",
    "handoff": "sender -> receiver",
    "dependency": "prerequisite -> dependent activity/outcome",
    "authority": "deciding role -> decision subject; not an authority grant",
    "trace": "supporting source/claim -> derived requirement/outcome",
}
CONVENTION = "Repeated IDs depict the same entity; see register."


def validate(block, shared):
    model = block["diagram"]
    if (not isinstance(model, dict) or set(model) != {"schema", "layout", "purpose", "lanes", "nodes", "edges"}
            or type(model["schema"]) is not int or model["schema"] != 1 or model["layout"] != "lanes-v1"
            or model["purpose"] not in ("process", "responsibility", "handoff", "traceability", "options", "roadmap")):
        raise Invalid("Unsupported diagram model or layout")
    for key, low, high in (("lanes", 1, 3), ("nodes", 1, 6), ("edges", 0, 7)):
        if not isinstance(model[key], list) or not low <= len(model[key]) <= high:
            raise Invalid(f"Diagram {key} must contain {low}–{high} entries")
    local, cells, pairs = set(), set(), set()
    lanes, nodes = {}, {}
    citations = [c["record"] for c in block["citations"]]
    for group, fields in (("lanes", {"id", "label"}),
                          ("nodes", {"id", "lane", "column", "kind", "label", "evidence"}),
                          ("edges", {"id", "from", "to", "kind", "label", "evidence"})):
        for item in model[group]:
            if not isinstance(item, dict) or set(item) != fields:
                raise Invalid("Unknown or missing diagram fields")
            key = identifier(item["id"])
            if len(key) > 24 or key in local:
                raise Invalid("Diagram IDs must be distinct and at most 24 characters")
            local.add(key)
            label = item["label"]
            if not text(label) or "\n" in label or len(label) > (64 if group == "nodes" else 30):
                raise Invalid("Diagram label missing, multiline or over its character bound")
            if group != "lanes":
                if (not isinstance(item["evidence"], list) or not item["evidence"]
                        or any(ref not in citations for ref in item["evidence"])):
                    raise Invalid("Every diagram entity/relationship needs exact evidence from its block citations")
            if group == "lanes":
                lanes[key] = len(lanes)
            elif group == "nodes":
                if (not isinstance(item["lane"], str) or item["lane"] not in lanes
                        or type(item["column"]) is not int or item["column"] not in (0, 1)
                        or item["kind"] not in ("activity", "decision", "outcome", "evidence", "actor", "option", "milestone", "requirement")):
                    raise Invalid("Unsupported diagram node, lane or column")
                cell = (lanes[item["lane"]], item["column"])
                if cell in cells:
                    raise Invalid("Only one diagram node per cell is supported")
                cells.add(cell)
                nodes[key] = cell
            else:
                start, end = item["from"], item["to"]
                if (not isinstance(start, str) or not isinstance(end, str) or start not in nodes or end not in nodes
                        or start == end or item["kind"] not in DIRECTIONS):
                    raise Invalid("Dangling or unsupported diagram relationship")
                pair = frozenset((start, end))
                if pair in pairs or sum(abs(a - b) for a, b in zip(nodes[start], nodes[end])) != 1:
                    raise Invalid("Use separate reviewed views for nonadjacent, reciprocal or parallel relationships")
                pairs.add(pair)
            signature = (group, {k: v for k, v in item.items() if k != "column"})
            if key in shared and shared[key] != signature:
                raise Invalid(f"{key}: inconsistent diagram identity across views")
            shared[key] = signature


def registers(packet):
    """Derived render-only fields; authoritative packets never accept these extra fields."""
    occurrences = {}
    for block in packet["blocks"]:
        if block["kind"] == "diagram":
            for group in ("lanes", "nodes", "edges"):
                for item in block["diagram"][group]:
                    occurrences.setdefault(item["id"], []).append(block["id"])
    blocks = []
    for block in packet["blocks"]:
        if block["kind"] != "diagram":
            blocks.append(block)
            continue
        model, rows = block["diagram"], []
        lanes = {lane["id"]: lane["label"] for lane in model["lanes"]}
        for lane in model["lanes"]:
            rows.append([lane["id"], "lane", lane["label"],
                         "Block context: " + "; ".join(c["label"] for c in block["citations"]),
                         ", ".join(occurrences[lane["id"]])])
        for group in ("nodes", "edges"):
            for item in model[group]:
                evidence = "; ".join(c["label"] for c in block["citations"] if c["record"] in item["evidence"])
                role = lanes[item["lane"]] if group == "nodes" else item["from"] + " -> " + item["to"]
                rows.append([item["id"], item["kind"] + ": " + role, item["label"], evidence,
                             ", ".join(occurrences[item["id"]])])
        glossary = "; ".join(kind + ": " + DIRECTIONS[kind] for kind in sorted({e["kind"] for e in model["edges"]}))
        blocks.append(dict(block, columns=["ID", "Type / role", "Label / relationship", "Evidence", "Views"], rows=rows,
                           text=block["text"] + "\n" + CONVENTION,
                           notes="\n".join(filter(None, (block["notes"], glossary)))))
    return dict(packet, blocks=blocks)


@lru_cache(maxsize=32)
def face(family, size):
    from PIL import ImageFont
    path = subprocess.run(["fc-match", "-f", "%{file}", family + ":style=Regular"],
                          capture_output=True, text=True, check=True, timeout=10).stdout
    return ImageFont.truetype(path, size * 4)


def wrapped(value, family, size, width):
    font = face(family, size)
    lines, line = [], ""
    for word in value.split():
        if font.getlength(word) / 4 > width * 72:
            raise Invalid("Diagram word/ID exceeds its box; shorten and re-review, never shrink")
        candidate = line + (" " if line else "") + word
        if font.getlength(candidate) / 4 > width * 72:
            lines.append(line)
            line = word
        else:
            line = candidate
    return [*lines, line]


def geometry(block, family, slide=False):
    """Fixed boxes and ports with checked text, line and arrowhead clearance."""
    width, height, step = (12, 3.8, 1.45) if slide else (6.9, 4, 1.55)
    xs, node_width = ((1.5, 7.5), 3) if slide else ((1, 4.4), 1.5)
    size, small, lane_size, edge_size = (18, 10, 14, 12) if slide else (12, 9, 10, 10)
    model, boxes, lines, nodes = block["diagram"], [], [], {}

    def box(key, kind, rect, value, points, extra=None):
        x, y, w, h = rect
        inset = .04 if kind == "node" else 0
        chunks = [(s, points) for s in wrapped(value, family, points, w - inset * 2)]
        if extra is not None:
            chunks += [(s, small) for s in wrapped(extra, family, small, w - inset * 2)]
        if sum(p * 1.2 for _, p in chunks) > (h - inset * 2) * 72 + 1e-8:
            raise Invalid(f"{block['id']}/{key}: diagram text exceeds its box; split and re-review")
        boxes.append({"id": key, "kind": kind, "rect": rect, "text": chunks, "inset": inset})

    for row, lane in enumerate(model["lanes"]):
        box(lane["id"], "lane", (0, row * step, 1.3 if slide else .9, .9), lane["label"], lane_size)
        for node in model["nodes"]:
            if node["lane"] == lane["id"]:
                rect = (xs[node["column"]], row * step, node_width, .9)
                nodes[node["id"]] = rect
                box(node["id"], "node", rect, node["kind"] + ": " + node["label"], size, node["id"])
    for edge in model["edges"]:
        a, b = nodes[edge["from"]], nodes[edge["to"]]
        horizontal = a[1] == b[1]
        if horizontal:
            forward = a[0] < b[0]
            start = (a[0] + (a[2] if forward else 0), a[1] + .45)
            end = (b[0] + (0 if forward else b[2]), b[1] + .45)
            rect = (4.65, a[1], 2.7, .4) if slide else (2.6, a[1] + .02, 1.7, .36)
        else:
            forward = a[1] < b[1]
            start = (a[0] + a[2] / 2, a[1] + (.9 if forward else 0))
            end = (b[0] + b[2] / 2, b[1] + (0 if forward else .9))
            rect = ((start[0] + .1, min(a[1], b[1]) + .97, 2.4, .42) if slide else
                    (start[0] + .08, min(a[1], b[1]) + 1.02, 1.4, .5))
        lines.append(dict(edge, start=start, end=end))
        box(edge["id"], "label", rect, edge["kind"] + ": " + edge["label"], edge_size)

    def overlap(a, b, clearance=.02):
        return (a[0] < b[0] + b[2] + clearance and a[0] + a[2] + clearance > b[0]
                and a[1] < b[1] + b[3] + clearance and a[1] + a[3] + clearance > b[1])

    for i, current in enumerate(boxes):
        x, y, w, h = current["rect"]
        if x < 0 or y < 0 or x + w > width + 1e-8 or y + h > height + 1e-8:
            raise Invalid("Diagram object exceeds its canvas")
        for other in boxes[i + 1:]:
            if overlap(current["rect"], other["rect"]):
                raise Invalid(f"{block['id']}: overlapping diagram labels; split views and re-review")
        for line in lines:
            if current["id"] in (line["from"], line["to"]):
                continue
            (x1, y1), (x2, y2) = line["start"], line["end"]
            stroke = (min(x1, x2) - .014, min(y1, y2) - .014, abs(x2-x1) + .028, abs(y2-y1) + .028)
            # Medium arrowhead is three times the 2pt shaft: 6pt long and 6pt wide.
            # Its length extends back from the target, not past it in both directions.
            tip = ((x2 - (.084 if x2 > x1 else 0), y2 - .042, .084, .084) if y1 == y2 else
                   (x2 - .042, y2 - (.084 if y2 > y1 else 0), .084, .084))
            if overlap(current["rect"], stroke) or overlap(current["rect"], tip):
                raise Invalid(f"{block['id']}/{current['id']}: diagram line/label collision; split and re-review")
    return width, height, boxes, lines


def word(doc, block, palette):
    from lxml import etree as E
    family, ink, accent, muted = palette
    width, height, boxes, lines = geometry(block, family)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
          'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
          'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
          'wpg': 'http://schemas.microsoft.com/office/word/2010/wordprocessingGroup',
          'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape'}

    def add(parent, tag, **attrs):
        prefix, local = tag.split(':')
        item = E.SubElement(parent, '{'+ns[prefix]+'}'+local)
        for key, value in attrs.items():
            if ':' in key:
                p, k = key.split(':'); key = '{'+ns[p]+'}'+k
            item.set(key, str(value))
        return item

    def emu(value):
        return round(value * 914400)

    drawing = E.SubElement(doc.add_paragraph().add_run()._r, '{'+ns['w']+'}drawing', nsmap=ns)
    inline = add(drawing, 'wp:inline', distT=0, distB=0, distL=0, distR=0)
    add(inline, 'wp:extent', cx=emu(width), cy=emu(height))
    ident = doc.part.next_id
    add(inline, 'wp:docPr', id=ident, name=block['id'], descr=block['text'])
    add(inline, 'wp:cNvGraphicFramePr')
    canvas = add(add(add(inline, 'a:graphic'), 'a:graphicData', uri=ns['wpg']), 'wpg:wgp')
    add(canvas, 'wpg:cNvGrpSpPr')
    transform = add(add(canvas, 'wpg:grpSpPr'), 'a:xfrm')
    for tag, attrs in (('off', {'x': 0, 'y': 0}), ('ext', {'cx': emu(width), 'cy': emu(height)}),
                       ('chOff', {'x': 0, 'y': 0}), ('chExt', {'cx': emu(width), 'cy': emu(height)})):
        add(transform, 'a:'+tag, **attrs)
    # Writer normalizes occupied bounds: preserve the declared canvas with a blank native background.
    background = {"id": "canvas", "kind": "background", "rect": (0, 0, width, height), "text": [], "inset": 0}
    for current in [background, *boxes, *lines]:
        ident += 1
        item = add(canvas, 'wps:wsp')
        add(item, 'wps:cNvPr', id=ident, name=block['id'] + '/' + current['id'])
        add(item, 'wps:cNvSpPr')
        properties = add(item, 'wps:spPr')
        is_line = 'start' in current
        if is_line:
            (x1, y1), (x2, y2) = current['start'], current['end']
            x, y, w, h = min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1)
            transform = add(properties, 'a:xfrm', flipH=int(x2 < x1), flipV=int(y2 < y1))
        else:
            x, y, w, h = current['rect']
            transform = add(properties, 'a:xfrm')
        add(transform, 'a:off', x=emu(x), y=emu(y))
        add(transform, 'a:ext', cx=max(1, emu(w)), cy=max(1, emu(h)))
        add(add(properties, 'a:prstGeom', prst='line' if is_line else 'rect'), 'a:avLst')
        add(add(properties, 'a:solidFill'), 'a:srgbClr', val='FFFFFF')
        stroke = add(properties, 'a:ln', w=25400 if is_line else 12700)
        if is_line or current['kind'] == 'node':
            add(add(stroke, 'a:solidFill'), 'a:srgbClr', val=accent)
        else:
            add(stroke, 'a:noFill')
        if is_line:
            add(stroke, 'a:tailEnd', type='triangle', w='med', len='med')
        content = add(add(item, 'wps:txbx'), 'w:txbxContent')
        for value, size in current.get('text', [('', 10)]):
            paragraph = add(content, 'w:p')
            style = add(paragraph, 'w:pPr')
            add(style, 'w:spacing', **{'w:before': 0, 'w:after': 0, 'w:line': round(size * 24), 'w:lineRule': 'exact'})
            run = add(paragraph, 'w:r')
            font = add(run, 'w:rPr')
            add(font, 'w:rFonts', **{'w:ascii': family, 'w:hAnsi': family})
            add(font, 'w:sz', **{'w:val': size * 2})
            add(font, 'w:color', **{'w:val': ink})
            add(run, 'w:t').text = value
        if not len(content):
            add(content, 'w:p')
        inset = emu(current.get('inset', 0))
        add(add(item, 'wps:bodyPr', wrap='none', anchor='ctr', lIns=inset, rIns=inset, tIns=inset, bIns=inset), 'a:noAutofit')


def powerpoint(slide, block, palette):
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
    from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.util import Inches, Pt
    family, ink, accent, muted = palette
    _, _, boxes, lines = geometry(block, family, True)
    for current in boxes:
        x, y, w, h = current['rect']
        if current['kind'] == 'node':
            item = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(x+.6), Inches(y+2.25), Inches(w), Inches(h))
            item.fill.solid()
            item.fill.fore_color.rgb = RGBColor.from_string('FFFFFF')
            item.line.color.rgb, item.line.width = RGBColor.from_string(accent), Pt(1)
        else:
            item = slide.shapes.add_textbox(Inches(x+.6), Inches(y+2.25), Inches(w), Inches(h))
        item.name = block['id'] + '/' + current['id']
        frame = item.text_frame
        frame.auto_size, frame.word_wrap = MSO_AUTO_SIZE.NONE, False
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = Inches(current['inset'])
        for i, (value, size) in enumerate(current['text']):
            paragraph = frame.paragraphs[0] if not i else frame.add_paragraph()
            paragraph.text = value
            paragraph.font.name, paragraph.font.size = family, Pt(size)
            paragraph.font.color.rgb = RGBColor.from_string(ink)
            paragraph.space_before = paragraph.space_after = Pt(0)
            paragraph.line_spacing = Pt(size * 1.2)
    for line in lines:
        (x1, y1), (x2, y2) = line['start'], line['end']
        item = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1+.6), Inches(y1+2.25), Inches(x2+.6), Inches(y2+2.25))
        item.name = block['id'] + '/' + line['id']
        item.line.color.rgb, item.line.width = RGBColor.from_string(accent), Pt(2)
        tail = OxmlElement('a:tailEnd')
        for key, value in (('type', 'triangle'), ('w', 'med'), ('len', 'med')):
            tail.set(key, value)
        item._element.spPr.get_or_add_ln().append(tail)
