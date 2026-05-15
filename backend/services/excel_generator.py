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

    # 1. Build the rows list correctly
    rows = []
    for idx, feature in enumerate(features, start=1):
        rows.append({
            "Release Version": feature.get("release_version", "26B"),
            "Release Date": feature.get("release_date", "May 2026"),
            "Module": feature.get("module", "Inventory Management"),
            "Generated Feature ID": f"INV-{idx:03d}",
            "Oracle Feature ID": feature.get("oracle_feature_id", "N/A"),
            "Title": feature.get("title", ""),
            "Delivery Status": feature.get("delivery_status", "Enabled"),
            "Action Required": feature.get("action_required", "No Action Required"),
            "Impact": feature.get("impact", "Small Scale"),
            "Bug IDs": feature.get("bug_ids", "None"),
            "Description": feature.get("description", "Refer to Oracle Docs"),
            "Steps to Enable": feature.get("steps_to_enable", "Automatically enabled."),
            "URL": feature.get("url", ""),
            "Priority": feature.get("priority", "Low"),
            "Notes": feature.get("notes", "")
        })

    # 2. Create DataFrames
    df = pd.DataFrame(rows, columns=COLUMNS)
    summary_df = build_summary(df)

    # 3. Write to Excel using Pandas Engine
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Release Notes", index=False)
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name="Summary by Module", index=False)

    # 4. Apply professional styling
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
    
    # Professional Blue Header Styling
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                    top=Side(style='thin'), bottom=Side(style='thin'))

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    # Set dynamic column widths
    widths = [15, 15, 25, 20, 18, 45, 15, 20, 15, 15, 50, 50, 30, 15, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Apply wrapping to description and steps
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border

    # Add Dropdowns for Priority (Column N)
    if ws.max_row > 1:
        priority_dv = DataValidation(type="list", formula1='"High,Medium,Low"', allow_blank=True)
        ws.add_data_validation(priority_dv)
        priority_dv.add(f"N2:N{ws.max_row}")

    wb.save(path)