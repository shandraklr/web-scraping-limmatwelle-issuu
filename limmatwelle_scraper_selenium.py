import os
import time
import json
import re
from pypdf import PdfReader
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ============================================================================
# CONFIGURATION
# ============================================================================

EPAPER_URL = "https://www.limmatwelle.ch/e-paper"
TARGET_DATE = "22. Mai"
TARGET_PAGES = [12, 13]
DOWNLOAD_DIR = os.path.abspath("./downloads")
PDF_FILENAME = "limmatwelle_22_mai.pdf"


# ============================================================================
# SELENIUM SETUP
# ============================================================================

def setup_chrome_driver(download_dir: str):
    """
    Setup Chrome WebDriver with download preferences
    """
    print("==== Setting up Chrome WebDriver ====")
    
    # Create download directory if not exists
    os.makedirs(download_dir, exist_ok=True)
    
    # Chrome options
    chrome_options = Options()
    
    # Headless mode (comment out to see browser)
    chrome_options.add_argument('--headless=new')
    
    # Other useful options
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Set download preferences
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True  # Don't open PDF in browser
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Initialize driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    
    print("==== Chrome WebDriver ready ====")
    return driver


# ============================================================================
# STEP 1: WEB SCRAPING WITH SELENIUM
# ============================================================================

def scrape_epaper_page_selenium(driver: webdriver.Chrome, url: str, target_date: str):
    """
    Scrape e-paper page to find PDF URL
    Returns: Issuu PDF URL or None
    """
    try:
        print(f"Loading e-paper page: {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(3)
        
        print(f"Searching for edition: {target_date}")
        
        # Find all links
        links = driver.find_elements(By.TAG_NAME, "a")
        
        for link in links:
            link_text = link.text.strip()
            link_href = link.get_attribute("href")
            
            if target_date in link_text and link_href and 'issuu.com' in link_href:
                print(f"Found target edition: {link_text}")
                print(f"Issuu URL: {link_href}")
                return link_href
        
        print(f"Could not find edition with date: {target_date}")
        return None
        
    except Exception as e:
        print(f"Error scraping page: {e}")
        return None


# ============================================================================
# STEP 2: DOWNLOAD PDF FROM ISSUU USING SELENIUM
# ============================================================================

def download_pdf(driver: webdriver.Chrome, issuu_url: str, download_dir: str, timeout: int = 60):
    """
    Download PDF from issuu.com
    Returns: Path to downloaded PDF file or None
    """
    try:
        print(f"\nNavigating to issuu page...")
        print(f"URL: {issuu_url}")
        
        driver.get(issuu_url)
        
        # Wait for page to load
        print("  Waiting for page to load...")
        time.sleep(5)
        
        # IMPORTANT: Handle cookie consent banner first!
        print("  Checking for cookie consent banner...")
        try:
            # Try to find and click cookie accept button
            cookie_selectors = [
                "//button[contains(text(), 'Accept')]",
                "//button[contains(text(), 'Allow')]",
                "//button[@id='CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll']",
                "//button[@id='CybotCookiebotDialogBodyButtonAccept']",
                "//a[contains(@class, 'cookie-accept')]",
            ]
            
            cookie_handled = False
            for selector in cookie_selectors:
                try:
                    cookie_btn = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    cookie_btn.click()
                    print("Cookie banner accepted successfully")
                    time.sleep(2)  # Wait for banner to disappear
                    cookie_handled = True
                    break
                except:
                    continue
            
            if not cookie_handled:
                print(">> No cookie banner found (or already dismissed) <<")
        except Exception as e:
            print(f">> Cookie handling skipped: {e} <<")
        
        # Try to find download button
        print("Looking for download button...")
        
        # Possible download button selectors (issuu uses different patterns)
        download_selectors = [
            "//button[contains(@aria-label, 'Download')]",
            "//button[contains(text(), 'Download')]",
            "//a[contains(@aria-label, 'Download')]",
            "//a[contains(text(), 'Download')]",
            "//button[contains(@class, 'download')]",
            "//a[contains(@class, 'download')]",
            "//*[@data-test-id='download-button']",
            "//*[contains(@class, 'sc-') and contains(text(), 'Download')]"
        ]
        
        download_button = None
        for selector in download_selectors:
            try:
                download_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                print(f"Found download button with selector: {selector}")
                break
            except (NoSuchElementException, TimeoutException):
                continue
        
        if download_button:
            print("Attempting to click download button...")
            
            try:
                # Method 1: Scroll to element first
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
                time.sleep(1)
                
                # Method 2: Use JavaScript click (bypasses overlay issues)
                print("Using JavaScript click to bypass overlays...")
                driver.execute_script("arguments[0].click();", download_button)
                time.sleep(2)
                
                print("Download button clicked successfully!")
                
            except Exception as click_error:
                print(f"JavaScript click failed: {click_error}")
                print("Trying alternative: ActionChains click...")
                
                try:
                    # Method 3: ActionChains with move to element
                    actions = ActionChains(driver)
                    actions.move_to_element(download_button).click().perform()
                    time.sleep(2)
                    print("ActionChains click successful!")
                    
                except Exception as action_error:
                    print(f"ActionChains also failed: {action_error}")
                    print("Download button found but cannot click due to overlays")
            
            # Wait for download to complete
            print(f"... Waiting for download to complete (max {timeout}s) ...")
            downloaded_file = wait_for_download(download_dir, timeout)
            
            if downloaded_file:
                print(f"PDF downloaded successfully: {downloaded_file}")
                return downloaded_file
            else:
                print("Download timeout or failed")
                return None
        else:
            print("\n>> Download button not found on issuu page <<")
            print(">> Issuu might require: <<")
            print("  >> Login/authentication <<")
            print("  >> Premium account <<")
            print("  >> Or the document owner disabled downloads <<")
            print("\n>> Trying alternative: Extract PDF from viewer... <<")
            
            # Alternative: Try to get PDF URL from page source or network
            return try_extract_pdf_url_from_issuu(driver)
        
    except Exception as e:
        print(f"Error downloading from issuu: {e}")
        return None


def wait_for_download(download_dir: str, timeout: int = 60):
    """
    Wait for file download to complete        
    Returns: Path to downloaded file or None
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Get all files in download directory
        files = os.listdir(download_dir)
        
        # Filter PDF files (exclude .crdownload temporary files)
        pdf_files = [f for f in files if f.endswith('.pdf') and not f.endswith('.crdownload')]
        
        if pdf_files:
            # Return the most recent PDF file
            pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
            return os.path.join(download_dir, pdf_files[0])
        
        # Check if download is in progress
        temp_files = [f for f in files if f.endswith('.crdownload')]
        if temp_files:
            print("Download in progress...", end='\r')
        
        time.sleep(1)
    
    return None


def try_extract_pdf_url_from_issuu(driver: webdriver.Chrome):
    """
    Try to extract direct PDF URL from issuu page source or network calls
    Returns: Path to downloaded PDF or None
    """
    try:
        print("Reading page source for PDF URL")
        
        # Get page source
        page_source = driver.page_source
        
        # Look for PDF URL patterns in page source
        pdf_patterns = [
            r'https://[^"\']+\.pdf',
            r'"pdfUrl":"([^"]+)"',
            r'"downloadUrl":"([^"]+)"',
            r'data-pdf-url="([^"]+)"'
        ]
        
        for pattern in pdf_patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                print(f"Found potential PDF URL: {matches[0]}")
                # Try to download from this URL
                # This would require additional implementation
                break
        
        print("Could not extract PDF URL automatically")
        return None
        
    except Exception as e:
        print(f"Error extracting PDF URL: {e}")
        return None


# ============================================================================
# STEP 3: PDF TEXT EXTRACTION
# ============================================================================

def extract_text_from_pdf(pdf_path: str, page_numbers):
    """
    Extract text from specific page(s) of PDF using pypdf        
    Returns: Extracted text as string (combined if multiple pages)
    """
    try:        
        print(f"\nOpening PDF: {pdf_path}")
        reader = PdfReader(pdf_path)
        
        total_pages = len(reader.pages)
        print(f"Total pages: {total_pages}")
        
        # Handle both single page and multiple pages
        if isinstance(page_numbers, int):
            page_numbers = [page_numbers]
        
        all_text = []
        for page_num in page_numbers:
            if page_num > total_pages:
                print(f"Page {page_num} exceeds total pages, skipping")
                continue
            
            page = reader.pages[page_num - 1]
            text = page.extract_text()
            all_text.append(text)
            print(f"Extracted {len(text)} characters from page {page_num}")
        
        combined_text = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
        print(f"Total extracted: {len(combined_text)} characters from {len(all_text)} page(s)")
        
        return combined_text
        
    except ImportError:
        print("pypdf not installed: pip install pypdf --break-system-packages")
        return None
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None


# ============================================================================
# STEP 4: DATA PARSING
# ============================================================================

def find_baugesuch_sections(text: str):
    """Find all Baugesuch sections from Gemeinde Wurenlos"""
    print("\nSearching for Baugesuch from Gemeinde Wurenlos...")
    
    sections = []
    
    # Simple pattern: Find "Baugesuchspublikation" followed by section until next "Baugesuchspublikation" or "BAUVERWALTUNG"
    # Split by these markers
    parts = re.split(r'(Baugesuchspublikation)', text, flags=re.IGNORECASE)
    
    # Reconstruct sections
    for i in range(1, len(parts), 2):
        if i+1 < len(parts):
            section = parts[i] + parts[i+1]
            
            # Check if this section contains Würenlos (handle encoding variants)
            if re.search(r'W[üÜu]renlos', section, re.IGNORECASE):
                # Also check for BAUVERWALTUNGWÜRENLOS at the end
                if 'BAUVERWALTUNG' in section.upper():
                    # Split at BAUVERWALTUNG to get just this section
                    section = section.split('BAUVERWALTUNG')[0] + 'BAUVERWALTUNGWÜRENLOS'
                
                sections.append(section)
                
                # Extract Baugesuch Nr for logging
                nr_match = re.search(r'BaugesuchNr\.?:?\s*(\d+)', section)
                if nr_match:
                    print(f"    Found Baugesuch Nr. {nr_match.group(1)}")
    
    print(f">> Found {len(sections)} Baugesuch section(s) <<")
    return sections


def extract_field(text: str, field: str):
    """Extract value for a field from text"""
    pattern = rf'{field}\s*[:\-]\s*([^\n]+(?:\n(?!\w+\s*[:A-Z])[^\n]+)*)'
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    
    if match:
        value = match.group(1).strip()
        value = re.sub(r'\s+', ' ', value)
        return value
    return ""


def parse_baugesuch(section: str):
    """Parse one Baugesuch section"""
    data = {}
    
    # Fix encoding issues first
    section = section.replace('Ãœ', 'Ü').replace('Ã¤', 'ä').replace('Ã¶', 'ö').replace('Ã–', 'Ö').replace('Ã„', 'Ä')
    section = section.replace('Ã©', 'é').replace('Ã¨', 'è').replace('Ã ', 'à')
    
    # Baugesuch Nr
    nr_match = re.search(r'BaugesuchNr\.?:?\s*(\d+)', section, re.IGNORECASE)
    if nr_match:
        data['Baugesuch_Nr'] = nr_match.group(1)
    
    # Extract Bauherrschaft - may span multiple lines
    bauherr_match = re.search(r'Bauherrschaft:?\s*(.*?)(?=Bauvorhaben:|$)', section, re.IGNORECASE | re.DOTALL)
    if bauherr_match:
        text = bauherr_match.group(1).strip()
        # Take only up to next field or reasonable length
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not re.match(r'^(Bauvorhaben|Lage|Zone|Zusatzgesuch):', line, re.IGNORECASE):
                lines.append(line)
            else:
                break
        if lines:
            data['Bauherrschaft'] = ','.join(lines)
    
    # Extract Bauvorhaben - may span multiple lines
    bauvor_match = re.search(r'Bauvorhaben:?\s*(.*?)(?=Lage:|$)', section, re.IGNORECASE | re.DOTALL)
    if bauvor_match:
        text = bauvor_match.group(1).strip()
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not re.match(r'^(Lage|Zone|Bauherrschaft):', line, re.IGNORECASE):
                lines.append(line)
            else:
                break
        if lines:
            data['Bauvorhaben'] = ' '.join(lines)
    
    # Extract Lage
    lage_match = re.search(r'Lage:?\s*(.*?)(?=Zone:|$)', section, re.IGNORECASE | re.DOTALL)
    if lage_match:
        text = lage_match.group(1).strip()
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not re.match(r'^(Zone|Zusatzgesuch):', line, re.IGNORECASE):
                lines.append(line)
            else:
                break
        if lines:
            data['Lage'] = ','.join(lines)
    
    # Extract Zone
    zone_match = re.search(r'Zone:?\s*(.*?)(?=Zusatzgesuch:|$)', section, re.IGNORECASE | re.DOTALL)
    if zone_match:
        text = zone_match.group(1).strip()
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not re.match(r'^(Zusatzgesuch|Gesuchsauflage):', line, re.IGNORECASE):
                lines.append(line)
            else:
                break
        if lines:
            data['Zone'] = lines[0]  # Usually single line
    
    # Extract Zusatzgesuch
    zusatz_match = re.search(r'Zusatzgesuch:?\s*(.*?)(?=Gesuchsauflage|$)', section, re.IGNORECASE | re.DOTALL)
    if zusatz_match:
        text = zusatz_match.group(1).strip()
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not re.match(r'^Gesuchsauflage', line, re.IGNORECASE):
                lines.append(line)
            else:
                break
        if lines:
            data['Zusatzgesuch'] = ','.join(lines)
    
    # Extract "others" - Gesuchsauflage text
    others_match = re.search(r'(Gesuchsauflage.*?)(?=BAUVERWALTUNG|$)', section, re.IGNORECASE | re.DOTALL)
    if others_match:
        others = others_match.group(1).strip()
        # Clean up excessive whitespace but preserve some structure
        others = re.sub(r'\s+', ' ', others)
        # Limit length if too long
        if len(others) > 500:
            others = others[:500] + '...'
        data['others'] = others
    
    return data


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    
    driver = None
    
    try:
        # Setup Selenium
        driver = setup_chrome_driver(DOWNLOAD_DIR)
        
        # STEP 1: Scrape website for PDF URL
        print("\n" + "="*70)
        print("[STEP 1] Scraping website for PDF URL...")
        print("="*70)
        
        issuu_url = scrape_epaper_page_selenium(driver, EPAPER_URL, TARGET_DATE)
        
        if not issuu_url:
            print("\n   Could not find PDF URL via Selenium")
            print("  Using known issuu URL as fallback...")
            issuu_url = "https://issuu.com/az-anzeiger/docs/woche_21_limmatwelle_22._mai"
        
        # STEP 2: Download PDF from issuu
        print("\n" + "="*70)
        print("[STEP 2] Downloading PDF from issuu...")
        print("="*70)
        
        pdf_path = download_pdf(driver, issuu_url, DOWNLOAD_DIR)
        
        if not pdf_path:
            print("\n   Automatic download failed")
            print("  Please download manually:")
            print(f"   1. Visit: {issuu_url}")
            print(f"   2. Download the PDF")
            print(f"   3. Place it in: {DOWNLOAD_DIR}/{PDF_FILENAME}")
            
            # Check if PDF already exists
            manual_pdf_path = os.path.join(DOWNLOAD_DIR, PDF_FILENAME)
            if os.path.exists(manual_pdf_path):
                print(f"\n  Found existing PDF: {manual_pdf_path}")
                pdf_path = manual_pdf_path
            else:
                print("\n  PDF not found. Exiting.")
                return
        
        # Rename downloaded file to standard name
        if pdf_path and os.path.basename(pdf_path) != PDF_FILENAME:
            new_path = os.path.join(DOWNLOAD_DIR, PDF_FILENAME)
            os.rename(pdf_path, new_path)
            pdf_path = new_path
            print(f"  Renamed PDF to: {PDF_FILENAME}")
        
        # STEP 3: Extract text from PDF
        print("\n" + "="*70)
        print(f"[STEP 3] Extracting text from page(s) {TARGET_PAGES}...")
        print("="*70)
        
        page_text = extract_text_from_pdf(pdf_path, TARGET_PAGES)
        
        if not page_text:
            print("  Failed to extract text from PDF")
            return
        
        # Save raw text for debugging
        page_label = "_".join(map(str, TARGET_PAGES)) if isinstance(TARGET_PAGES, list) else str(TARGET_PAGES)
        raw_text_path = os.path.join(DOWNLOAD_DIR, f"page_{page_label}_raw.txt")
        with open(raw_text_path, "w", encoding="utf-8") as f:
            f.write(page_text)
        print(f"  Raw text saved: {raw_text_path}")
        
        # STEP 4: Parse Baugesuch data
        print("\n" + "="*70)
        print("[STEP 4] Parsing Baugesuch data...")
        print("="*70)
        
        sections = find_baugesuch_sections(page_text)
        
        results = []
        for i, section in enumerate(sections, 1):
            print(f"\n  Processing Baugesuch #{i}...")
            data = parse_baugesuch(section)
            if any(data.values()):
                results.append(data)
                print(f"  Extracted data from Baugesuch #{i}")
        
        # STEP 5: Output results
        if results:
            print("\n" + "="*70)
            print("  FINAL JSON OUTPUT")
            print("="*70)
            
            output = json.dumps(results, ensure_ascii=False, indent=2)
            print(output)
            
            # output_file = "baugesuch_output.json"
            output_file = os.path.join(DOWNLOAD_DIR, "baugesuch_output.json")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output)
            
            print(f"\n  Output saved to: {output_file}")
            
            print("\n" + "="*70)
            print("  SCRAPING COMPLETED SUCCESSFULLY!")
            print("="*70)
            print(f"  Total Baugesuch extracted: {len(results)}")
            print(f"  PDF location: {pdf_path}")
            print(f"  Raw text: {raw_text_path}")
            print(f"  JSON output: {output_file}")
        else:
            print("\n  No Baugesuch data extracted")
            print(f"  Check {raw_text_path} for debugging")
        
    except Exception as e:
        print(f"\n  Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Close browser
        if driver:
            print("\n  Closing browser...")
            driver.quit()
            print("  Browser closed")


if __name__ == "__main__":
    main()