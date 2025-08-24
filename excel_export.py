import pandas as pd

def save_to_excel(data, filename="pune_doctors_sheet.xlsx"):
    """Save extracted data to Excel file"""
    if not data:
        return
    
    df = pd.DataFrame(data)
    
    # Reorder columns to match the required format
    columns_order = [
        'complete_address',
        'doctors_name', 
        'specialty',
        'region',
        'clinic_hospital',
        'years_of_experience',
        'contact_number',
        'contact_email',
        'ratings',
        'reviews',
        'summary_pros_cons'
    ]
    
    # Add any additional columns that might have been extracted
    for col in df.columns:
        if col not in columns_order:
            columns_order.append(col)
    
    df = df[columns_order]
    
    # Remove rows with missing data
    
    # Define required fields that must not be empty
    required_fields = ['doctors_name', 'contact_number', 'complete_address', 'specialty']
    
    # Create a mask for complete records
    complete_mask = True
    for field in required_fields:
        if field in df.columns:
            # Check if field is not empty and not just whitespace
            field_mask = (df[field].notna()) & (df[field].astype(str).str.strip() != '')
            complete_mask = complete_mask & field_mask
    
    # Filter to keep only complete records
    df_complete = df[complete_mask].copy()
    
    # Save only complete records
    df_complete.to_excel(filename, index=False)
    
    return df_complete
