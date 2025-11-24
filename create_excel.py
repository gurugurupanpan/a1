#!/usr/bin/env python3
"""
Script to convert Krinsky-Robb diagram data to Excel format
"""
import pandas as pd

# Data extracted from Krinsky-Robb 95% Confidence Intervals diagram
data = {
    'Parameter': [
        'ASC',
        'MF (A\'-A)',
        'Label',
        'MF × Label',
        'Tasting label',
        'MF × Tasting label'
    ],
    'Mean/Point Estimate': [821.29, 127.28, -172.75, 437.02, 290.71, -398.61],
    'CI Lower Bound': [734.4, 32.3, -266.7, 329.9, 167.0, -555.7],
    'CI Upper Bound': [911.6, 220.8, -81.0, 545.8, 415.8, -244.5],
    'CI Width': [177.2, 188.5, 185.7, 215.9, 248.8, 311.2]
}

# Create DataFrame
df = pd.DataFrame(data)

# Save to Excel with formatting
with pd.ExcelWriter('krinsky_robb_data.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Krinsky-Robb CI', index=False)

    # Get the worksheet
    worksheet = writer.sheets['Krinsky-Robb CI']

    # Adjust column widths
    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        worksheet.column_dimensions[column_letter].width = adjusted_width

print("Excel file created successfully: krinsky_robb_data.xlsx")
print("\nData preview:")
print(df.to_string(index=False))
