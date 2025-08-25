# Selenium Doctor Scraping Project

This project scrapes doctor information from Practo and organizes the data into an Excel file. The code has been split into three main files for better organization and maintainability.

## File Structure

### 1. `main.py` - Core Scraping Logic
Contains the main scraping functionality:
- Selenium web driver setup
- Doctor card extraction functions
- Contact information extraction
- Patient stories extraction
- Main execution loop

### 2. `gemini_service.py` - AI Summary Generation
Handles all Gemini API related functionality:
- Gemini API configuration
- Summary generation from patient stories
- Fallback manual summary creation
- Error handling for API failures

### 3. `excel_export.py` - Data Export
Manages Excel file creation and data formatting:
- DataFrame creation and column ordering
- Data validation and filtering
- Excel file export with proper formatting
- Summary statistics generation

## Dependencies

Make sure you have the following packages installed:
```bash
pip install selenium pandas google-generativeai openpyxl
```

## Usage

1. **Set up your Gemini API key** in `gemini_service.py`:
   ```python
   GEMINI_API_KEY = "your_actual_api_key_here"
   ```

2. **Run the main script**:
   ```bash
   python main.py
   ```

3. **Output**: The script will generate:
   - HTML backup files in the `data/` directory
   - An Excel file with all doctor information

## Features

- **Multi-specialty scraping**: Cardiologist, Dermatologist, Neurologist, etc.
- **Multi-region support**: Aundh, Baner, Wakad in Pune
- **AI-powered summaries**: Uses Gemini API to generate patient story summaries
- **Comprehensive data extraction**: Name, specialty, contact info, ratings, reviews
- **Data validation**: Filters out incomplete records
- **Error handling**: Robust error handling for web scraping issues

## Configuration

You can modify the following constants in `main.py`:
- `SPECIALTIES`: List of medical specialties to scrape
- `REGIONS`: List of regions to search in
- `BASE_URL`: The base URL for Practo search

## Notes

- The script processes 5 doctors per specialty-region combination
- Includes delays between requests to be respectful to the website
- Saves HTML backups for each doctor card processed
- Uses multiple strategies for extracting contact information
- Falls back to manual summary generation if Gemini API fails

## Workflow Diagram

![Automation workflow diagram](images/workflow.png)
