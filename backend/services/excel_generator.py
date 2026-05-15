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
    # Inside generate_excel
for idx, feature in enumerate(features, start=1):
    ws.append([
        "26B", # Hardcoded or passed from release
        "May 2026",
        feature.get("module", "Inventory Management"),
        f"INV-{idx:03d}",
        feature.get("oracle_feature_id", "N/A"),
        feature.get("title", ""),
        feature.get("delivery_status", "Enabled"),
        feature.get("action_required", "No Action Required"),
        feature.get("impact", "Small Scale"),
        feature.get("bug_ids", "None"),
        feature.get("description", "Refer to Oracle Docs"),
        feature.get("steps_to_enable", "Automatically enabled."),
        feature.get("url", ""),
        feature.get("priority", "Low"),
        feature.get("notes", "")
    ])

    df = pd.DataFrame(rows, columns=COLUMNS)
    summary_df = build_summary(df)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Release Notes", index=False)
        summary_df.to_excel(writer, sheet_name="Summary by Module", index=False)

    style_workbook(output)
    return str(output)

def build_summary(df):
    if df.empty: return pd.DataFrame()
    
    summary = df.groupby("Module").agg(
        Total=('Title', 'count'),
        Action_Required=('Action Required', lambda x: x.ne("No Action Required").sum())
    ).reset_index()
    return summary

def style_workbook(path):
    wb = load_workbook(path)
    ws = wb["Release Notes"]
    
    # Header Styling
    header_fill = PatternFill("solid", fgColor="CFE2F3")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = border

    # Column Widths
    widths = [15, 15, 25, 20, 18, 45, 15, 20, 15, 15, 50, 50, 30, 15, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Add Dropdowns if rows exist
    if ws.max_row > 1:
        priority_dv = DataValidation(type="list", formula1='"High,Medium,Low"', allow_blank=True)
        ws.add_data_validation(priority_dv)
        priority_dv.add(f"N2:N{ws.max_row}")

    wb.save(path)