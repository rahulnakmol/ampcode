"""Native workbook authoring; decimal arithmetic uses bounded integer pieces, never macros."""

from decimal import Decimal
from functools import lru_cache
import math
import subprocess


def six_places(ref):
    # Numeric equality and EXACT's text coercion can erase retained low bits.
    # Power-of-two scaling preserves them as integers; compare small high/low
    # pieces. The second remainder avoids MOD's near-zero cancellation. Subtract
    # its offset: adding it can round an odd integer across a power-of-two boundary.
    scale = f"2^(53-INT(LOG({ref},2)))"
    left, right = f"({ref}*{scale})", f"(ROUND({ref},6)*{scale})"
    return (f"IF({ref}=0,TRUE,AND(INT({left}/134217728)=INT({right}/134217728),"
            f"MOD({left},134217728)=MOD({right},134217728),"
            f"MOD({left}-67108864,134217728)=MOD({right}-67108864,134217728)))")


class DecimalFormulas:
    """Base-1e6 pieces retain the bounded model's decimal intermediates through native edits.

    Each multiplication sum is below 1e13 and each aggregate sum below 1e9. These
    integers are exactly representable. Only final display values become fractions.
    Formula strings come from this code; supplied text never becomes a formula.
    """

    BASE = 1000000

    def __init__(self, sheet):
        self.sheet, self.row, self.col = sheet, 0, 0

    def cell(self, expression, cached):
        from xlsxwriter.utility import xl_rowcol_to_cell
        ref = xl_rowcol_to_cell(self.row, self.col)
        self.sheet.write_formula(self.row, self.col, "=" + expression, None, cached)
        self.col += 1
        return ref, cached

    def input(self, ref, supplied, valid):
        integer = int(Decimal(str(supplied)) * self.BASE)
        return [self.cell(f"MOD(INT(ROUND(IF({valid},{ref},0)*{self.BASE},0)/{self.BASE ** i}),{self.BASE})",
                          integer // self.BASE ** i % self.BASE) for i in range(3)]

    def multiply(self, left, right):
        result, carry = [], ("0", 0)
        for k in range(len(left) + len(right)):
            terms = [(f"{a[0]}*{b[0]}", a[1] * b[1]) for i, a in enumerate(left)
                     for j, b in enumerate(right) if i + j == k]
            total = self.cell("+".join([carry[0], *[ref for ref, _ in terms]]),
                              carry[1] + sum(value for _, value in terms))
            result.append(self.cell(f"MOD({total[0]},{self.BASE})", total[1] % self.BASE))
            carry = self.cell(f"INT({total[0]}/{self.BASE})", total[1] // self.BASE)
        return result

    def aggregate(self, rows):
        result, carry = [], ("0", 0)
        for k in range(len(rows[0]) + 1):
            values = [row[k] for row in rows] if k < len(rows[0]) else []
            parts = []
            for start in range(0, len(values), 200):
                group = values[start:start + 200]
                parts.append(self.cell("SUM(" + ",".join(ref for ref, _ in group) + ")",
                                       sum(value for _, value in group)))
            total = self.cell("+".join([carry[0], *[ref for ref, _ in parts]]),
                              carry[1] + sum(value for _, value in parts))
            result.append(self.cell(f"MOD({total[0]},{self.BASE})", total[1] % self.BASE))
            carry = self.cell(f"INT({total[0]}/{self.BASE})", total[1] // self.BASE)
        return result

    def rounded(self, pieces, scale, places):
        discard = scale - places
        if discard % 6:
            shift = 10 ** (6 - discard % 6)
            pieces = self.multiply(pieces, [(str(shift), shift)])
            discard += 6 - discard % 6
        count = discard // 6
        terms = [(f"{ref}*{self.BASE ** i}", value * self.BASE ** i)
                 for i, (ref, value) in enumerate(pieces[count:])]
        rounded = sum(value for _, value in terms) + (pieces[count - 1][1] >= self.BASE // 2)
        return self.cell("(" + "+".join(ref for ref, _ in terms)
                         + f"+IF({pieces[count - 1][0]}>={self.BASE // 2},1,0))/{10 ** places}",
                         rounded / 10 ** places)

    def raw(self, pieces, scale):
        integer = sum(value * self.BASE ** i for i, (_, value) in enumerate(pieces))
        return self.cell("SUM(" + ",".join(f"{ref}*{self.BASE ** i}/{10 ** scale}"
                                          for i, (ref, _) in enumerate(pieces)) + ")", integer / 10 ** scale)

    def bounded(self, pieces, scale):
        # Compare integer pieces, not a floating sum that could erase a tiny excess.
        count, power = divmod(9 + scale, 6)
        boundary = 10 ** power
        high = [f"{ref}=0" for ref, _ in pieces[count + 1:]]
        lower = "SUM(" + ",".join(ref for ref, _ in pieces[:count]) + ")=0"
        ref = pieces[count][0]
        expression = f"AND({','.join([*high, f'OR({ref}<{boundary},AND({ref}={boundary},{lower}))'])})"
        integer = sum(value * self.BASE ** i for i, (_, value) in enumerate(pieces))
        return self.cell(expression, integer <= 10 ** (9 + scale))


def workbook(packet, path):
    import xlsxwriter
    from engagement import Invalid, digest
    from estimate import office_values
    from export import footer, table_data
    from branding import identity, palette
    from diagram import registers
    packet_hash = digest(packet)
    packet = registers(packet)
    FONT, INK, TEAL, MUTED = palette(packet)

    with xlsxwriter.Workbook(path, {"strings_to_formulas": False, "strings_to_urls": False}) as book:
        book.set_properties({"title": packet["title"], "author": "", "comments": "Exported, not delivered or client-approved."})
        book.set_calc_mode("auto")
        # Column units depend on the Normal face too, not only formatted cell text.
        # An unavailable default Calibri can widen imported columns and split print pages.
        book.formats[0].set_font_name(FONT)
        formats = {key: book.add_format({"font_name": FONT, "font_size": 11, "valign": "top", **values})
                   for key, values in {
                       "title": {"font_size": 22, "bold": True, "font_color": INK, "text_wrap": True},
                       "text": {"text_wrap": True, "font_color": INK},
                       "note": {"text_wrap": True, "font_size": 10, "font_color": MUTED},
                       "header": {"bold": True, "text_wrap": True, "bg_color": INK, "font_color": "FFFFFF"},
                       "input": {"bg_color": "FFF1D6", "font_color": INK, "num_format": "0.######", "locked": False},
                       "days": {"bg_color": "EDF4F4", "font_color": INK, "num_format": "0.000000"},
                       "money": {"bg_color": "EDF4F4", "font_color": INK, "num_format": "#,##0.00"},
                       "error": {"bg_color": "FBE4DF", "font_color": "852417", "text_wrap": True},
                   }.items()}

        @lru_cache(maxsize=6)
        def font(size, bold):
            from PIL import ImageFont
            match = subprocess.run(["fc-match", "-f", "%{family}\n%{file}", FONT + (":style=Bold" if bold else ":style=Regular")],
                                   capture_output=True, text=True, check=True, timeout=10).stdout.splitlines()
            if len(match) != 2 or match[0] != FONT:
                raise Invalid("Selected workbook font unavailable; resolve an authorized substitution and re-review")
            return ImageFont.truetype(match[1], size * 2)

        def height(value, width, size=11, bold=False):
            # Column units are approximately seven screen pixels; reserve padding and
            # measure with the actual face. Overlong rows refuse, never truncate/shrink.
            available = width * 5.25 - 10
            face, lines = font(size, bold), 0
            for paragraph in value.split("\n"):
                used = 0
                lines += 1
                for word in paragraph.split():
                    length = face.getlength(word + " ") / 2
                    if used and used + length > available:
                        lines += 1
                        used = 0
                    if length > available:
                        pieces = math.ceil(length / available)
                        lines += pieces - 1
                        length -= available * (pieces - 1)
                    used += length
            result = max(24, math.ceil(lines * size * 1.4 + 8))
            if result > 400:
                raise Invalid("Workbook text would exceed a readable row; split and review the packet")
            return result

        def text(sheet, row, col, value, style="text"):
            if len(value) > 32767:
                raise Invalid("Workbook cell exceeds 32767 characters; split and review the packet")
            sheet.write_string(row, col, value, formats[style])

        def sheet(name, title, columns):
            page = book.add_worksheet(name)
            page.hide_gridlines(2)
            page.set_paper(8 if sum(columns) > 125 else 9)
            page.set_landscape()
            page.set_margins(.35, .35, .5, .5)
            page.set_tab_color(TEAL)
            label = (identity(packet) + " | " if identity(packet) else "") + "Exported, not client-approved"
            footer_width = ((16.54 if sum(columns) > 125 else 11.69) - .7) * 72 - 80
            if "\n" in label or font(10, False).getlength(label) / 2 > footer_width:
                raise Invalid("Workbook issuer/classification exceeds the footer; shorten and re-review")
            label = label.replace("&", "&&")
            footer_text = f'&L&"{FONT},Regular"&10{label}&RPage &P'
            if len(footer_text) > 255:
                raise Invalid("Workbook issuer/classification too long for the footer; shorten and re-review")
            page.set_footer(footer_text)
            for col, width in enumerate(columns):
                page.set_column(col, col, width)
            page.merge_range(0, 0, 0, len(columns) - 1, "", formats["title"])
            text(page, 0, 0, title, "title")
            page.set_row(0, height(title, sum(columns), 22, True))
            page.set_print_scale(100)
            page._blueprint_widths = columns
            return page

        def prose(page, row, value, style="text"):
            page.merge_range(row, 0, row, len(page._blueprint_widths) - 1, "", formats[style])
            text(page, row, 0, value, style)
            page.set_row(row, height(value, sum(page._blueprint_widths)))

        readme = sheet("Read me", packet["title"], [25, 100])
        for row, (label, value) in enumerate([
            ("Purpose", "Reviewed supporting analysis for " + packet["audience"] + ". Intended destination: " + packet["destination"]),
            ("Decision and authority", "Use the supplied decision framing below. Missing approvers and agreed due dates remain unknown."),
            ("Review boundary", "File identity is not client approval. Editing creates an unreviewed scenario; it does not change retained evidence."),
            ("Editable inputs", "Amber labelled cells are inputs. Green-grey cells are calculated. Validation also checks pasted edits; invalid scenarios withhold totals."),
            ("Calculation audit", "Visible Calculation sheets preserve exact decimal arithmetic in integer pieces. Edit inputs, not formulas. No macros or external links."),
            ("Content fingerprint", packet_hash),
        ], 3):
            text(readme, row, 0, label, "header")
            text(readme, row, 1, value)
            readme.set_row(row, max(height(label, 25), height(value, 100)))
        overview_row = 11

        for index, block in enumerate(packet["blocks"], 1):
            text(readme, overview_row, 0, f"{index:02d} / {block['id']}", "header")
            text(readme, overview_row, 1, block["title"] + "\n" + block["text"])
            readme.set_row(overview_row, max(height(f"{index:02d} / {block['id']}", 25),
                                           height(block["title"] + "\n" + block["text"], 100)))
            overview_row += 1
            if block["kind"] != "estimate":
                count = max(5, len(table_data(block)[0])) if block["kind"] != "text" else 5
                widths = [17 if count > 6 else 24] * count
                page = sheet(f"Content {index}", block["title"], widths)
                prose(page, 3, block["text"])
                cursor = 6
                if block["kind"] != "text":
                    columns, rows = table_data(block)
                    if len(columns) > 10 or len(rows) > 10000:
                        raise Invalid("Workbook table exceeds 10 columns or 10000 rows; split and review the packet")
                    if len({name.casefold() for name in columns}) != len(columns) or any(len(name) > 255 for name in columns):
                        raise Invalid("Workbook table headers must be unique")
                    for row in [columns, *rows]:
                        if any(len(value) > 32767 for value in row):
                            raise Invalid("Workbook table cell too long; split and review the packet")
                    page.add_table(cursor, 0, cursor + len(rows), len(columns) - 1, {
                        "data": rows, "columns": [{"header": name, "header_format": formats["header"],
                                                  "format": formats["text"]} for name in columns],
                        "style": None})
                    page.freeze_panes(cursor + 1, 1)
                    page.repeat_rows(cursor)
                    page.repeat_columns(0)
                    for row, values in enumerate([columns, *rows], cursor):
                        page.set_row(row, max(height(value, widths[col]) for col, value in enumerate(values)))
                    cursor += len(rows) + 3
                    if block["kind"] == "chart":
                        if len(rows) > 20 or len(columns) > 4:
                            raise Invalid("Workbook chart too dense; split and review the packet")
                        for row, values in enumerate(block["series"], 1):
                            for offset, value in enumerate(values["values"], 7):
                                page.write_number(offset, row, value, formats["text"])
                        chart = book.add_chart({"type": "bar"})
                        # Prevent Calc from adding an unstyled automatic series-name title.
                        chart.set_title({"none": True})
                        for col in range(1, len(columns)):
                            chart.add_series({"name": [page.name, 6, col],
                                "categories": [page.name, 7, 0, 6 + len(rows), 0],
                                "values": [page.name, 7, col, 6 + len(rows), col],
                                "fill": {"color": (TEAL, INK, MUTED)[col - 1]}})
                        chart.set_x_axis({"name": block["unit"], "num_font": {"name": FONT, "size": 11},
                                          "name_font": {"name": FONT, "size": 11},
                                          "min": min(0, min(v for s in block["series"] for v in s["values"]))})
                        chart.set_y_axis({"num_font": {"name": FONT, "size": 11}})
                        chart.set_legend({"none": True} if len(columns) == 2 else {
                            "position": "bottom", "font": {"name": FONT, "size": 11}})
                        chart_height = max(288, len(rows) * 22)
                        # The repeated title consumes space on the chart's page too.
                        # Budget points at 100% scale, including two default 15pt rows.
                        printable_height = ((297 if sum(widths) > 125 else 210) / 25.4 - 1) * 72
                        if height(block["title"], sum(widths), 22, True) + chart_height * .75 + 30 > printable_height:
                            raise Invalid("Workbook chart and repeated title exceed one printed page; split and review the packet")
                        chart.set_size({"width": 600, "height": chart_height})
                        page.set_h_pagebreaks([cursor])
                        page.repeat_rows(0)
                        page.insert_chart(cursor + 1, 0, chart, {"description": block["title"] + ". Values in the table above."})
                        cursor += math.ceil(chart_height / 20) + 2
                for value in (footer(block), block["notes"]):
                    prose(page, cursor, value, "note")
                    cursor += 2
                page.print_area(0, 0, cursor, max(4, len(columns) - 1) if block["kind"] != "text" else 4)
                continue

            model = block["model"]
            expected = office_values(model)
            name, calc_name = f"Estimate {index}", f"Calculation {index}"
            page = sheet(name, block["title"], [24, 12, 14, 14, 15, 15, 15, 17, 17])
            calc = sheet(calc_name, "Derived decimal calculation audit", [24, 24, 24, 24])
            prose(calc, 3, "Derived formulas only. Edit the labelled Estimate inputs; formula edits require reconciliation. "
                  "The calculation grid is visible on screen, not included in the print area.", "note")
            calc.print_area(0, 0, 3, 3)
            page.merge_range(3, 0, 3, 8, "", formats["header"])
            page.merge_range(4, 0, 4, 8, "", formats["note"])
            page.set_row(3, 26)
            page.set_row(4, 32)
            headers = ["Activity ID", "Quantity (input)", "Low days/unit (input)", "High days/unit (input)",
                       model["currency"] + "/day (input)", "Low person-days", "High person-days",
                       "Low base " + model["currency"], "High base " + model["currency"]]
            for col, label in enumerate(headers):
                text(page, 5, col, label, "header")
            page.set_row(5, 36)
            page.freeze_panes(6, 1)
            page.repeat_rows(5)
            builder = DecimalFormulas(calc)
            effort_rows, cost_rows, input_checks, bounds = [[], []], [[], []], [], []
            count = len(model["activities"])
            for row, activity in enumerate(model["activities"], 6):
                excel = row + 1
                text(page, row, 0, activity["id"])
                page.set_row(row, height(activity["id"], 24))
                values = [activity[key] for key in ("quantity", "days_per_unit_low", "days_per_unit_high", "day_rate")]
                for col, value in enumerate(values, 1):
                    page.write_number(row, col, float(Decimal(str(value))), formats["input"])
                builder.row, builder.col = row, 0
                refs = [f"'{name}'!{col}{excel}" for col in "BCDE"]
                q, lo, hi, rate = refs
                valid = builder.cell("IFERROR(AND(" + ",".join([
                    *[f"ISNUMBER({ref})" for ref in refs], *[f"{ref}>=0" for ref in refs],
                    *[f"{ref}<=1000000" for ref in refs], *[six_places(ref) for ref in refs],
                    f"{q}>0", f"{hi}>0", f"{rate}>0", f"{lo}<={hi}"]) + "),FALSE)", True)
                input_checks.append(valid)
                quantity, low, high, day_rate = [builder.input(ref, value, valid[0]) for ref, value in zip(refs, values)]
                for side, days in enumerate((low, high)):
                    effort = builder.multiply(quantity, days)
                    cost = builder.multiply(effort, day_rate)
                    effort_rows[side].append(effort)
                    cost_rows[side].append(cost)
                    bounds += [builder.bounded(effort, 12), builder.bounded(cost, 18)]
                    for col, pieces, scale, places, style in ((5 + side, effort, 12, 6, "days"),
                                                            (7 + side, cost, 18, 2, "money")):
                        value = builder.rounded(pieces, scale, places)
                        page.write_formula(row, col, f'=IF($A$4="VALID INPUTS / UNREVIEWED SCENARIO",\'{calc_name}\'!{value[0]},"")',
                                           formats[style], value[1])
            page.autofilter(5, 0, 5 + count, 8)
            reserve_row = count + 8
            text(page, reserve_row, 0, "Contingency % (input)")
            page.write_number(reserve_row, 1, float(Decimal(str(model["contingency_percent"]))), formats["input"])
            pct = f"'{name}'!B{reserve_row + 1}"
            builder.row, builder.col = count + 8, 0
            pct_valid = builder.cell(f"IFERROR(AND(ISNUMBER({pct}),{pct}>=0,{pct}<=100,{six_places(pct)}),FALSE)", True)
            input_checks.append(pct_valid)
            multiplier = builder.cell(f"ROUND(IF({pct_valid[0]},{pct},0)*1000000,0)",
                                      int(Decimal(str(model["contingency_percent"])) * 1000000))
            factor = builder.cell(f"100000000+{multiplier[0]}", 100000000 + multiplier[1])
            def pieces(value):
                return [builder.cell(f"MOD({value[0]},1000000)", value[1] % 1000000),
                        builder.cell(f"INT({value[0]}/1000000)", value[1] // 1000000)]
            pct_parts, factor_parts = pieces(multiplier), pieces(factor)
            displayed = {key: [] for key in ("person_days", "base_cost", "contingency_cost", "total_cost")}
            for side in range(2):
                effort, cost = builder.aggregate(effort_rows[side]), builder.aggregate(cost_rows[side])
                contingency, total = builder.multiply(cost, pct_parts), builder.multiply(cost, factor_parts)
                for key, digits, scale, places in (("person_days", effort, 12, 6), ("base_cost", cost, 18, 2),
                                                  ("contingency_cost", contingency, 26, 2), ("total_cost", total, 26, 2)):
                    bounds.append(builder.bounded(digits, scale))
                    displayed[key].append(builder.rounded(digits, scale, places))
                    builder.raw(digits, scale)
            checks = input_checks + bounds
            partials = [builder.cell("AND(" + ",".join(ref for ref, _ in checks[start:start + 200]) + ")", True)
                        for start in range(0, len(checks), 200)]
            valid = builder.cell("AND(" + ",".join(ref for ref, _ in partials) + ")", True)
            page.write_formula('A4', f'=IFERROR(IF(\'{calc_name}\'!{valid[0]},"VALID INPUTS / UNREVIEWED SCENARIO",'
                               '"INVALID SCENARIO / TOTALS WITHHELD"),"INVALID SCENARIO / TOTALS WITHHELD")',
                               formats["header"], "VALID INPUTS / UNREVIEWED SCENARIO")
            page.write_formula('A5', f'=IF(LEFT(A4,5)="VALID","Inputs meet numeric bounds; scope and rates still require review.",'
                               f'IFERROR("Check "&INDEX(A7:A{count + 6},MATCH(FALSE,\'{calc_name}\'!A7:A{count + 6},0))&'
                               f'" (row "&(MATCH(FALSE,\'{calc_name}\'!A7:A{count + 6},0)+6)&")"&'
                               '": quantity/rate/high > 0; low <= high; all <= 1000000, six decimals.",'
                               f'IF(NOT(\'{calc_name}\'!{pct_valid[0]}),"Check contingency: 0–100%, six decimals.",'
                               '"Calculated result exceeds 1000000000; reduce inputs or split and review the model.")))', formats["note"],
                               "Inputs meet numeric bounds; scope and rates still require review.")
            page.conditional_format(6, 1, 5 + count, 4, {"type": "formula", "criteria": '=LEFT($A$4,7)="INVALID"', "format": formats["error"]})
            page.data_validation(6, 1, 5 + count, 4, {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 1000000})
            page.data_validation(reserve_row, 1, reserve_row, 1, {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 100})
            total_row = reserve_row + 3
            text(page, total_row - 1, 7, "Low", "header")
            text(page, total_row - 1, 8, "High", "header")
            for offset, (key, label) in enumerate((("person_days", "Person-days"), ("base_cost", "Base " + model["currency"]),
                                                  ("contingency_cost", "Contingency " + model["currency"]), ("total_cost", "Total " + model["currency"]))):
                page.merge_range(total_row + offset, 0, total_row + offset, 6, "", formats["header"])
                text(page, total_row + offset, 0, label, "header")
                for side, (ref, cached) in enumerate(displayed[key]):
                    page.write_formula(total_row + offset, 7 + side, f'=IF(LEFT($A$4,5)="VALID",\'{calc_name}\'!{ref},"")',
                                       formats["days" if key == "person_days" else "money"], cached)
            readme.write_formula(overview_row, 1, f'=\'{name}\'!A4', formats["note"], "VALID INPUTS / UNREVIEWED SCENARIO")
            overview_row += 2
            # Retain all selected prose and activity provenance visibly, separate from numeric inputs.
            basis = sheet(f"Basis {index}", "Estimate assumptions and activity basis", [16, 28, 22, 42, 24])
            cursor = 3
            details = [block["text"], footer(block), block["notes"], "Rate date: " + model["rate_date"],
                       "Assumptions: " + "; ".join(model["assumptions"]), "Basis: " + "; ".join(model["basis"]), expected["limitations"]]
            for value in details:
                prose(basis, cursor, value)
                cursor += 2
            rows = [[r["id"], r["activity"], r["role"], r["basis"], ", ".join(r["after"]) or "none"] for r in model["activities"]]
            if any(len(value) > 32767 for row in rows for value in row):
                raise Invalid("Workbook activity text too long; split and review the packet")
            basis.add_table(cursor, 0, cursor + len(rows), 4, {"data": rows, "columns": [
                {"header": label, "header_format": formats["header"], "format": formats["text"]}
                for label in ("ID", "Activity", "Role", "Basis", "Predecessors")]})
            basis.freeze_panes(cursor + 1, 1)
            basis.repeat_rows(cursor)
            for r, values in enumerate([["ID", "Activity", "Role", "Basis", "Predecessors"], *rows], cursor):
                basis.set_row(r, max(height(value, basis._blueprint_widths[c]) for c, value in enumerate(values)))
            page.print_area(0, 0, total_row + 4, 8)
            basis.print_area(0, 0, cursor + len(rows), 4)
        readme.print_area(0, 0, overview_row, 1)
