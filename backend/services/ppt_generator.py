from collections import defaultdict
from pathlib import Path
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls

# Corporate Identity Theme Colors
BLUE, DARK, WHITE = RGBColor(0, 153, 204), RGBColor(32, 32, 32), RGBColor(255, 255, 255)
HEADER_BLUE = RGBColor(31, 78, 121)

def safe_text(v): 
    return "" if v is None else str(v).strip()

def normalize_priority(v):
    val = safe_text(v).lower()
    return val.capitalize() if val in ["high", "low", "skip"] else "Medium"

def clear_slides(prs):
    for i in range(len(prs.slides) - 1, -1, -1):
        prs.part.drop_rel(prs.slides._sldIdLst[i].rId)
        del prs.slides._sldIdLst[i]

def add_clean_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    for shp in list(slide.shapes):
        if shp.is_placeholder: 
            slide.shapes._spTree.remove(shp.element)
    return slide

def set_cell_border(cell, color="D3D3D3", width="12700"):
    """Applies clean, executive gray cell borders using strictly compliant OOXML namespaces."""
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ["lnL", "lnR", "lnT", "lnB"]:
        # Completely eliminate the nested tag mismatch by enforcing absolute namespace tokens
        xml_string = (
            f'<a:{tag} {nsdecls("a")} w="{width}">'
            f'  <a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'  <a:prstDash val="solid"/>'
            f'</a:{tag}>'
        )
        tcPr.append(parse_xml(xml_string))

def add_branding(slide, prs, release, page_no):
    """Draws consistent company accents, page pagination anchors, and secure logs."""
    for y, h, c in [(0, 0.12, BLUE), (prs.slide_height - Inches(0.2), 0.2, BLUE)]:
        rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, y, prs.slide_width, Inches(h))
        rect.fill.solid()
        rect.fill.fore_color.rgb = c
        rect.line.fill.background()
    
    logo_configs = [
        ("assets/arcturus_logo.png", prs.slide_width - Inches(2.05), Inches(0.28), 1.65), 
        ("assets/tid_logo.png", (prs.slide_width // 2) - Inches(0.35), prs.slide_height - Inches(0.85), 0.7)
    ]
    for path, x, y, w in logo_configs:
        if os.path.exists(path): 
            try:
                slide.shapes.add_picture(path, x, y, width=Inches(w))
            except Exception as img_err:
                print(f"Skipping logo asset injection: {img_err}")
                pass
    
    for txt, x, w, align in [(f"Oracle Upgrade Assessment Profile {release} — Internal Consultancy Reference", 0, prs.slide_width, PP_ALIGN.CENTER), (str(page_no), prs.slide_width - Inches(0.5), 0.4, PP_ALIGN.RIGHT)]:
        tb = slide.shapes.add_textbox(x, prs.slide_height - Inches(0.2), w, Inches(0.2))
        p = tb.text_frame.paragraphs[0]
        p.text = txt
        p.font.name = "Calibri"
        p.font.size = Pt(6 if align == PP_ALIGN.CENTER else 7)
        p.font.color.rgb = WHITE
        p.alignment = align

def add_textbox(slide, l, t, w, h, txt, size=14, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = safe_text(txt)
    p.font.name, p.font.size, p.font.bold, p.font.color.rgb, p.alignment = "Calibri", Pt(size), bold, DARK, align

def set_cell_style(cell, txt, size=9, bold=False, color=DARK, align=PP_ALIGN.LEFT):
    tf = cell.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = safe_text(txt)
    p.font.name, p.font.size, p.font.bold, p.font.color.rgb = "Calibri", Pt(size), bold, color
    p.alignment = align

def add_title_slide(prs, release, rel_date, module, page):
    slide = add_clean_slide(prs)
    add_branding(slide, prs, release, page)
    y = prs.slide_height // 2 - Inches(1)
    
    add_textbox(slide, Inches(1), y, prs.slide_width - Inches(2), Inches(0.5), f"Oracle Cloud Readiness Advisory Review", 28, True, PP_ALIGN.CENTER)
    add_textbox(slide, Inches(1), y + Inches(0.6), prs.slide_width - Inches(2), Inches(0.4), f"Functional Track Analysis: {module}", 20, False, PP_ALIGN.CENTER)
    add_textbox(slide, Inches(1), y + Inches(1.1), prs.slide_width - Inches(2), Inches(0.3), f"Release Assessment Version: {release} ({rel_date})", 13, False, PP_ALIGN.CENTER)

def add_index_slide(prs, module_summaries, release, page):
    slide = add_clean_slide(prs)
    add_branding(slide, prs, release, page)
    add_textbox(slide, Inches(0.5), Inches(0.5), Inches(6), Inches(0.5), "Executive Overview: Functional Scope Matrix", 22, True)
    
    idx_table = slide.shapes.add_table(len(module_summaries) + 1, 2, Inches(0.8), Inches(1.4), Inches(8.4), Inches(0.38 * (len(module_summaries) + 1))).table
    idx_table.columns[0].width, idx_table.columns[1].width = Inches(6.4), Inches(2.0)
    
    for c, h in enumerate(["Target System Sub-Module Stream", "Identified Upgrade Feature Count"]):
        cell = idx_table.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = HEADER_BLUE
        set_cell_style(cell, h, bold=True, color=WHITE, align=PP_ALIGN.CENTER if c==1 else PP_ALIGN.LEFT)
        set_cell_border(cell)

    for i, summary in enumerate(module_summaries, 1):
        name, count = summary.split('|')
        set_cell_style(idx_table.cell(i, 0), name, size=10.5, bold=True)
        set_cell_style(idx_table.cell(i, 1), f"{count} Features", size=10.5, align=PP_ALIGN.CENTER)
        set_cell_border(idx_table.cell(i, 0))
        set_cell_border(idx_table.cell(i, 1))

def add_table_slide(prs, module, items, release, page_no, part_label=""):
    slide = add_clean_slide(prs)
    add_branding(slide, prs, release, page_no)
    
    title_text = f"{module} — Release Deployment Tracking {part_label}".strip()
    add_textbox(slide, Inches(0.42), Inches(0.42), Inches(8.5), Inches(0.35), title_text, size=16, bold=True)

    row_count = len(items)
    header_h = 0.35
    available_table_height = Inches(4.2)
    row_height = available_table_height / row_count

    table_shape = slide.shapes.add_table(row_count + 1, 6, Inches(0.42), Inches(0.95), Inches(9.16), Inches(header_h) + available_table_height)
    table = table_shape.table

    wds = [0.4, 2.1, 2.6, 2.2, 0.9, 0.96]
    for i, w in enumerate(wds):
        table.columns[i].width = Inches(w)
    
    table.rows[0].height = Inches(header_h)
    headers = ["Sr.", "Feature Strategy", "Description Summary", "Steps to Enable / Action Runbook", "Priority", "Impact Tiers"]
    for c, h in enumerate(headers):
        cell = table.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = HEADER_BLUE
        set_cell_style(cell, h, bold=True, color=WHITE, align=PP_ALIGN.CENTER if c in [0,4,5] else PP_ALIGN.LEFT)
        set_cell_border(cell)

    for r, feat in enumerate(items, start=1):
        table.rows[r].height = row_height
        
        # SAFE CASE-INSENSITIVE VALUE ACCESS MATRICES
        feature_title = feat.get("title") or feat.get("Title", "")
        description_summary = feat.get("description") or feat.get("Description", "")
        steps_runbook = feat.get("steps_to_enable") or feat.get("Steps to Enable", "")
        priority_value = feat.get("priority") or feat.get("Priority", "Medium")
        impact_value = feat.get("impact") or feat.get("Impact", "Small Scale")

        vals = [
            str(feat.get("_serial", r)), 
            feature_title, 
            description_summary, 
            steps_runbook, 
            normalize_priority(priority_value),
            impact_value
        ]
        
        for c, v in enumerate(vals):
            cell = table.cell(r, c)
            
            if c == 4 and v == "High":
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(254, 237, 222)
                set_cell_style(cell, v, bold=True, color=RGBColor(166, 77, 0), align=PP_ALIGN.CENTER)
            elif c in [0, 4, 5]:
                set_cell_style(cell, v, align=PP_ALIGN.CENTER)
            else:
                set_cell_style(cell, v)
                
            set_cell_border(cell)

    link_start_y = Inches(5.6)
    link_height = Inches(0.24)
    
    for i, feature in enumerate(items):
        link_y = link_start_y + (i * link_height)
        box = slide.shapes.add_textbox(Inches(0.42), link_y, Inches(9.16), Inches(0.25))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        
        # Safe lookup for internal key designations
        fid = feature.get("oracle_feature_id") or feature.get("Oracle Feature ID") or feature.get("Generated Feature ID", "ORCL")
        ftitle = feature.get("title") or feature.get("Title", "")
        furl = feature.get("url") or feature.get("URL", "https://docs.oracle.com/en/cloud/")

        p.text = f"Verification Anchor Reference [{fid}] — {ftitle}"
        p.font.name = "Calibri"
        p.font.size = Pt(7.5)
        p.font.color.rgb = RGBColor(0, 102, 204)
        p.font.underline = True
        
        try:
            p.runs[0].hyperlink.address = furl
        except Exception:
            pass

def generate_ppt(features, output_path):
    try:
        prs = Presentation()
    except Exception:
        prs = Presentation()

    clear_slides(prs)
    if not features: 
        prs.save(output_path)
        return str(output_path)
    
    # Unified mapping fallbacks tracking raw payload objects
    rel = safe_text(features[0].get("release_version") or features[0].get("Release Version", "26B"))
    date = safe_text(features[0].get("release_date") or features[0].get("Release Date", "May 2026"))
    base_module = safe_text(features[0].get("module") or features[0].get("Module", "Supply Chain Architecture"))
    
    page = 1
    add_title_slide(prs, rel, date, base_module, page)
    page += 1
    
    valid = [f for f in features if normalize_priority(f.get("priority") or f.get("Priority", "Medium")) != "Skip"]
    grouped = defaultdict(list)
    for f in valid: 
        mod_key = safe_text(f.get("module") or f.get("Module", base_module))
        grouped[mod_key].append(f)
    
    module_summaries = [f"{mod}|{len(feats)}" for mod, feats in grouped.items()]
    for i in range(0, len(module_summaries), 10):
        add_index_slide(prs, module_summaries[i:i+10], rel, page)
        page += 1

    for mod, mod_feats in grouped.items():
        for i, f in enumerate(mod_feats, 1): 
            f["_serial"] = i
        
        chunks = [mod_feats[x:x+2] for x in range(0, len(mod_feats), 2)]
        for i, chunk in enumerate(chunks, 1):
            add_table_slide(prs, mod, chunk, rel, page, f"({i}/{len(chunks)})" if len(chunks) > 1 else "")
            page += 1
    
    prs.save(output_path)
    return str(output_path)