from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

COLUMNS = [
    "Release Version", "Release Date", "Module", "Generated Feature ID",
    "Oracle Feature ID", "Title", "Delivery Status", "Action Required",
    "Impact", "Bug IDs", "Description", "Steps to Enable", "URL",
    "Priority", "Notes"
]

def generate_excel(features, output_path: str):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for idx, feature in enumerate(features, start=1):
        rows.append({
            "Release Version": feature.get("release_version", ""),
            "Release Date": feature.get("release_date", ""),
            "Module": feature.get("module", ""),
            "Generated Feature ID": feature.get("feature_id", f"FEATURE-{idx:03d}"),
            "Oracle Feature ID": feature.get("oracle_feature_id", ""),
            "Title": feature.get("title", ""),
            "Delivery Status": feature.get("delivery_status", feature.get("status", "Unknown")),
            "Action Required": feature.get("action_required", ""),
            "Impact": feature.get("impact", ""),
            "Bug IDs": feature.get("bug_ids", ""),
            "Description": feature.get("description", ""),
            "Steps to Enable": feature.get("steps_to_enable", ""),
            "URL": feature.get("url", ""),
            "Priority": feature.get("priority", ""),
            "Notes": feature.get("notes", "")
        })

    df = pd.DataFrame(rows, columns=COLUMNS)
    summary = build_summary(df)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Release Notes", index=False)
        summary.to_excel(writer, sheet_name="Summary by Module", index=False)

    style_workbook(output)
    return str(output)

def build_summary(df):
    summary_rows = []
    if df.empty:
        return pd.DataFrame(columns=["Module", "Total", "Enabled", "Disabled", "Action Required"])

    for module, group in df.groupby("Module"):
        summary_rows.append({
            "Module": module,
            "Total": len(group),
            "Enabled": group["Delivery Status"].astype(str).str.lower().eq("enabled").sum(),
            "Disabled": group["Delivery Status"].astype(str).str.lower().eq("disabled").sum(),
            "Action Required": group["Action Required"].fillna("").astype(str).str.strip().ne("").sum()
        })

    summary_rows.append({
        "Module": "Total",
        "Total": sum(r["Total"] for r in summary_rows),
        "Enabled": sum(r["Enabled"] for r in summary_rows),
        "Disabled": sum(r["Disabled"] for r in summary_rows),
        "Action Required": sum(r["Action Required"] for r in summary_rows)
    })
    return pd.DataFrame(summary_rows)

def style_workbook(path):
    wb = load_workbook(path)
    ws = wb["Release Notes"]
    summary_ws = wb["Summary by Module"]

    header_fill = PatternFill("solid", fgColor="D9EAF7")
    title_fill = PatternFill("solid", fgColor="F3F6FA")
    border = Border(
        left=Side(style="thin", color="C9CED6"),
        right=Side(style="thin", color="C9CED6"),
        top=Side(style="thin", color="C9CED6"),
        bottom=Side(style="thin", color="C9CED6")
    )

    # Insert main title row
    ws.insert_rows(1)
    ws["A1"] = "Oracle Quarterly Release Notes"
    ws["A1"].font = Font(size=14, bold=True)
    ws["A1"].fill = title_fill
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(COLUMNS))

    # Style Header (Row 2)
    for cell in ws[2]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Style Content
    for row in ws.iter_rows(min_row=3):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    # Column Widths
    widths = [16, 16, 22, 20, 20, 40, 16, 30, 30, 18, 60, 50, 40, 16, 30]
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    ws.freeze_panes = "A3"
    
    # CRITICAL FIX: Data Validation check to prevent "ValueError: 2 must be greater than 3"
    if ws.max_row >= 3:
        ws.auto_filter.ref = f"A2:O{ws.max_row}"

        priority_dropdown = DataValidation(type="list", formula1='"Critical,High,Low,Skip"', allow_blank=True)
        ws.add_data_validation(priority_dropdown)
        priority_dropdown.add(f"N3:N{ws.max_row}")

        status_dropdown = DataValidation(type="list", formula1='"Enabled,Disabled,Opt-In,Unknown"', allow_blank=True)
        ws.add_data_validation(status_dropdown)
        status_dropdown.add(f"G3:G{ws.max_row}")

    # Summary Sheet Styling
    for cell in summary_ws[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center")

    for row in summary_ws.iter_rows(min_row=2):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")

    for col in range(1, summary_ws.max_column + 1):
        summary_ws.column_dimensions[get_column_letter(col)].width = 24

    # Final row styling for total
    if summary_ws.max_row > 1:
        for cell in summary_ws[summary_ws.max_row]:
            cell.font = Font(bold=True)
            cell.fill = title_fill

    wb.save(path)