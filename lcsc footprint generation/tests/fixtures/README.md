# Test Fixtures

This directory contains sample files for testing the OpenPnP Footprint Manager.

## Files Needed

### BOM Files (Place real BOM files here)
- `sample_bom.csv` - Sample BOM in CSV format
- `sample_bom.xlsx` - Sample BOM in Excel format

**Expected BOM format:**
```csv
Reference,Value,FOOTPRINT-NAME,supplier part
R1,10K,C0402,C25804
R2,10K,C0402,C25804
C1,100nF,C0402,C1525
U1,STM32F103,LQFP48,C8734
```

### OpenPnP Configuration Files
- `sample_packages.xml` - Sample packages from your OpenPnP
- `sample_parts.xml` - Sample parts from your OpenPnP

### LCSC API Responses (Optional - will be mocked)
- `sample_easyeda_response.json` - Sample response from LCSC API

## How to Add Files

1. Copy your real BOM files here (anonymize if needed)
2. Copy packages.xml and parts.xml from your OpenPnP .openpnp2 folder
3. These files help ensure the application works with your actual data

## Privacy Note

If you want to anonymize your BOM:
- Change component values to generic ones
- Keep the structure and column names
- Keep the LCSC part numbers (they're public anyway)
