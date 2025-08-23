from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
import time, os, re, json
import pandas as pd

driver = webdriver.Chrome()
driver.get("https://www.practo.com/search/doctors?results_type=doctor&q=%5B%7B%22word%22%3A%22dentist%22%2C%22autocompleted%22%3Atrue%2C%22category%22%3A%22subspeciality%22%7D%2C%7B%22word%22%3A%22Aundh%22%2C%22autocompleted%22%3Atrue%2C%22category%22%3A%22locality%22%7D%5D&city=Pune&page=1")

def extract_contact_info(doctor_card):
    """Extract contact information by clicking the Contact Clinic button"""
    try:
        # First, check if the contact button exists
        contact_buttons = doctor_card.find_elements(By.CSS_SELECTOR, '[data-qa-id="call_button"]')
        
        if not contact_buttons:
            print("⚠️ No contact button found for this doctor")
            return ""
        
        contact_button = contact_buttons[0]
        
        # Scroll to the button to ensure it's visible
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", contact_button)
        time.sleep(2)
        
        # Clear any existing phone number elements first
        try:
            existing_phone_elements = driver.find_elements(By.CSS_SELECTOR, '[data-qa-id="phone_number"]')
            for elem in existing_phone_elements:
                if elem.is_displayed():
                    print("🗑️ Clearing existing phone number element")
                    break
        except:
            pass
        
        # Try multiple click strategies
        click_successful = False
        
        # Strategy 1: Regular click
        try:
            contact_button.click()
            click_successful = True
            print("✅ Regular click successful")
        except ElementClickInterceptedException:
            print("⚠️ Regular click intercepted, trying alternatives...")
        
        # Strategy 2: JavaScript click
        if not click_successful:
            try:
                driver.execute_script("arguments[0].click();", contact_button)
                click_successful = True
                print("✅ JavaScript click successful")
            except Exception as e:
                print(f"❌ JavaScript click failed: {e}")
        
        # Strategy 3: ActionChains click
        if not click_successful:
            try:
                actions = ActionChains(driver)
                actions.move_to_element(contact_button).click().perform()
                click_successful = True
                print("✅ ActionChains click successful")
            except Exception as e:
                print(f"❌ ActionChains click failed: {e}")
        
        if not click_successful:
            print("❌ All click strategies failed")
            return ""
        
        # Wait for the contact info to appear
        wait = WebDriverWait(driver, 10)
        try:
            # Wait for a new phone number element to appear
            phone_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa-id="phone_number"]'))
            )
            
            # Make sure we get the most recent phone number element
            all_phone_elements = driver.find_elements(By.CSS_SELECTOR, '[data-qa-id="phone_number"]')
            if len(all_phone_elements) > 1:
                # Get the last (most recent) phone number element
                phone_element = all_phone_elements[-1]
                print(f"📞 Found {len(all_phone_elements)} phone elements, using the most recent one")
            
            # Extract the phone number
            phone_number = phone_element.text.strip()
            print(f"✅ Found phone number: {phone_number}")
            
            # Additional verification - check if this is a valid phone number
            if phone_number and len(phone_number) >= 10:
                return phone_number
            else:
                print("⚠️ Invalid phone number format")
                return ""
            
        except TimeoutException:
            print("❌ Phone number element did not appear after clicking")
            return ""
        
    except Exception as e:
        print(f"❌ Could not extract contact info: {e}")
        return ""

def extract_detailed_address(doctor_card):
    """Navigate to doctor's profile page and extract detailed address"""
    try:
        # Debug: Print all links in the doctor card
        print("🔍 Debugging: Looking for profile links...")
        all_links = doctor_card.find_elements(By.CSS_SELECTOR, 'a')
        print(f"Found {len(all_links)} links in doctor card")
        
        for i, link in enumerate(all_links):
            href = link.get_attribute('href')
            text = link.text.strip()
            print(f"  Link {i+1}: href='{href}', text='{text}'")
        
        # Try multiple selectors to find the doctor name link
        name_link = None
        
        # Strategy 1: Look for link inside h2 with data-qa-id
        try:
            name_link = doctor_card.find_element(By.CSS_SELECTOR, 'h2[data-qa-id="doctor_name"] a')
            print("✅ Found link using Strategy 1")
        except NoSuchElementException:
            print("❌ Strategy 1 failed")
        
        # Strategy 2: Look for any link that contains doctor name
        if not name_link:
            try:
                name_link = doctor_card.find_element(By.CSS_SELECTOR, 'a[href*="/doctor/"]')
                print("✅ Found link using Strategy 2")
            except NoSuchElementException:
                print("❌ Strategy 2 failed")
        
        # Strategy 3: Look for link inside info-section
        if not name_link:
            try:
                name_link = doctor_card.find_element(By.CSS_SELECTOR, '.info-section a')
                print("✅ Found link using Strategy 3")
            except NoSuchElementException:
                print("❌ Strategy 3 failed")
        
        # Strategy 4: Look for any anchor tag with href containing doctor
        if not name_link:
            try:
                all_links = doctor_card.find_elements(By.CSS_SELECTOR, 'a[href*="doctor"]')
                if all_links:
                    name_link = all_links[0]
                    print("✅ Found link using Strategy 4")
            except NoSuchElementException:
                print("❌ Strategy 4 failed")
        
        # Strategy 5: Look for any link with href containing "practo.com"
        if not name_link:
            try:
                all_links = doctor_card.find_elements(By.CSS_SELECTOR, 'a[href*="practo.com"]')
                if all_links:
                    name_link = all_links[0]
                    print("✅ Found link using Strategy 5")
            except NoSuchElementException:
                print("❌ Strategy 5 failed")
        
        if not name_link:
            print("⚠️ No profile link found for this doctor")
            return ""
        
        # Get the href attribute
        profile_url = name_link.get_attribute('href')
        
        if not profile_url:
            print("⚠️ No profile URL found")
            return ""
        
        # Make sure it's a full URL
        if profile_url.startswith('/'):
            profile_url = "https://www.practo.com" + profile_url
        
        print(f"🔗 Navigating to profile: {profile_url}")
        
        # Open profile in new tab
        driver.execute_script(f"window.open('{profile_url}', '_blank');")
        
        # Switch to the new tab
        driver.switch_to.window(driver.window_handles[-1])
        
        # Wait for page to load
        wait = WebDriverWait(driver, 15)
        
        try:
            # Wait for the address element to appear
            address_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa-id="clinic-address"]'))
            )
            
            detailed_address = address_element.text.strip()
            print(f"✅ Found detailed address: {detailed_address}")
            
            # Close the tab and switch back
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            
            return detailed_address
            
        except TimeoutException:
            print("❌ Address element not found on profile page")
            # Close the tab and switch back
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            return ""
            
    except Exception as e:
        print(f"❌ Error extracting detailed address: {e}")
        # Make sure we're back on the main page
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        return ""

def extract_doctor_details(doctor_card):
    """Extract all doctor details from the card"""
    doctor_info = {
        'complete_address': '',
        'doctors_name': '',
        'specialty': '',
        'clinic_hospital': '',
        'years_of_experience': '',
        'contact_number': '',
        'contact_email': '',
        'ratings': '',
        'reviews': '',
        'summary_pros_cons': ''
    }
    
    try:
        # Extract doctor name
        try:
            name_element = doctor_card.find_element(By.CSS_SELECTOR, '[data-qa-id="doctor_name"]')
            doctor_info['doctors_name'] = name_element.text.strip()
        except NoSuchElementException:
            # Fallback for different name formats
            try:
                name_element = doctor_card.find_element(By.CSS_SELECTOR, "h2.u-jumbo-font")
                doctor_info['doctors_name'] = name_element.text.strip()
            except NoSuchElementException:
                doctor_info['doctors_name'] = "Unknown"
        
        # Extract specialty
        try:
            specialty_elements = doctor_card.find_elements(By.CSS_SELECTOR, "span")
            for elem in specialty_elements:
                text = elem.text.strip()
                if text.lower() in ['dentist', 'dental', 'orthodontist', 'endodontist', 'periodontist']:
                    doctor_info['specialty'] = text
                    break
        except:
            doctor_info['specialty'] = "Dentist"  # Default
        
        # Extract years of experience
        try:
            exp_elements = doctor_card.find_elements(By.CSS_SELECTOR, "div")
            for elem in exp_elements:
                text = elem.text.strip()
                if 'years experience' in text.lower():
                    # Extract just the number
                    match = re.search(r'(\d+)\s*years experience', text.lower())
                    if match:
                        doctor_info['years_of_experience'] = f"{match.group(1)} years"
                    else:
                        doctor_info['years_of_experience'] = text
                    break
        except:
            pass
        
        # Extract clinic/hospital name
        try:
            clinic_element = doctor_card.find_element(By.CSS_SELECTOR, '[data-qa-id="doctor_clinic_name"]')
            doctor_info['clinic_hospital'] = clinic_element.text.strip()
        except NoSuchElementException:
            # Look for clinic name in other elements
            try:
                clinic_elements = doctor_card.find_elements(By.CSS_SELECTOR, "span.u-c-pointer")
                for elem in clinic_elements:
                    text = elem.text.strip()
                    if text and not text.isdigit() and len(text) > 3:
                        doctor_info['clinic_hospital'] = text
                        break
            except:
                pass
        
        # Extract detailed address from profile page
        detailed_address = extract_detailed_address(doctor_card)
        if detailed_address:
            doctor_info['complete_address'] = detailed_address
        else:
            # Fallback to JSON-LD structured data
            try:
                # Get the parent element that contains the script
                parent_element = doctor_card.find_element(By.XPATH, "./..")
                script_elements = parent_element.find_elements(By.CSS_SELECTOR, "script[type='application/ld+json']")
                
                for script in script_elements:
                    try:
                        json_data = json.loads(script.get_attribute('innerHTML'))
                        if '@type' in json_data and json_data['@type'] == 'Dentist':
                            if 'address' in json_data:
                                address = json_data['address']
                                if isinstance(address, dict):
                                    street = address.get('streetAddress', '')
                                    locality = address.get('addressLocality', '')
                                    region = address.get('addressRegion', '')
                                    postal_code = address.get('postalCode', '')
                                    
                                    address_parts = [street, locality, region, postal_code]
                                    address_parts = [part for part in address_parts if part]
                                    doctor_info['complete_address'] = ', '.join(address_parts)
                                    break
                    except:
                        continue
            except:
                pass
        
        # Extract ratings
        try:
            rating_element = doctor_card.find_element(By.CSS_SELECTOR, '[data-qa-id="doctor_recommendation"]')
            doctor_info['ratings'] = rating_element.text.strip()
        except NoSuchElementException:
            # Look for rating in other elements
            try:
                rating_elements = doctor_card.find_elements(By.CSS_SELECTOR, "span.o-label--success")
                for elem in rating_elements:
                    text = elem.text.strip()
                    if '%' in text:
                        doctor_info['ratings'] = text
                        break
            except:
                pass
        
        # Extract reviews/patient stories
        try:
            reviews_element = doctor_card.find_element(By.CSS_SELECTOR, '[data-qa-id="total_feedback"]')
            doctor_info['reviews'] = reviews_element.text.strip()
        except NoSuchElementException:
            # Look for patient stories
            try:
                review_elements = doctor_card.find_elements(By.CSS_SELECTOR, "span.u-t-underline")
                for elem in review_elements:
                    text = elem.text.strip()
                    if 'patient' in text.lower() or 'stories' in text.lower():
                        doctor_info['reviews'] = text
                        break
            except:
                pass
        
        # Extract location
        try:
            location_element = doctor_card.find_element(By.CSS_SELECTOR, '[data-qa-id="practice_locality"]')
            location = location_element.text.strip()
            if location and not doctor_info['complete_address']:
                doctor_info['complete_address'] = location
        except:
            pass
        
    except Exception as e:
        print(f"❌ Error extracting doctor details: {e}")
    
    return doctor_info

def save_to_excel(data, filename="doctors_pune_comprehensive.xlsx"):
    """Save extracted data to Excel file"""
    if not data:
        print("No data to save!")
        return
    
    df = pd.DataFrame(data)
    
    # Reorder columns to match the required format
    columns_order = [
        'complete_address',
        'doctors_name', 
        'specialty',
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
    
    df.to_excel(filename, index=False)
    print(f"✅ Data saved to {filename}")
    print(f"Total records: {len(df)}")
    
    # Print summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY:")
    print("="*60)
    print(f"Total doctors processed: {len(df)}")
    print(f"Doctors with names: {len(df[df['doctors_name'] != ''])}")
    print(f"Doctors with contact numbers: {len(df[df['contact_number'] != ''])}")
    print(f"Doctors with ratings: {len(df[df['ratings'] != ''])}")
    print(f"Doctors with reviews: {len(df[df['reviews'] != ''])}")
    print(f"Doctors with addresses: {len(df[df['complete_address'] != ''])}")
    
    return df

try:
    # wait until at least 1 doctor card is present
    elems = WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.u-border-general--bottom"))
    )
    print("Found:", len(elems))
    
    all_doctors_data = []
    
    # Process each doctor card
    for idx, elem in enumerate(elems):
        print(f"\n{'='*50}")
        print(f"Processing doctor {idx + 1}/{len(elems)}")
        print(f"{'='*50}")
        
        # Extract all doctor details (including detailed address)
        doctor_info = extract_doctor_details(elem)
        print(f"Doctor: {doctor_info['doctors_name']}")
        print(f"Specialty: {doctor_info['specialty']}")
        print(f"Experience: {doctor_info['years_of_experience']}")
        print(f"Clinic: {doctor_info['clinic_hospital']}")
        print(f"Address: {doctor_info['complete_address']}")
        print(f"Ratings: {doctor_info['ratings']}")
        print(f"Reviews: {doctor_info['reviews']}")
        
        # Extract contact information
        phone_number = extract_contact_info(elem)
        doctor_info['contact_number'] = phone_number
        print(f"Contact: {phone_number}")
        
        # Add to our data collection
        all_doctors_data.append(doctor_info)
        
        # Get the HTML content for backup
        d = elem.get_attribute("outerHTML")
        
        # Save to file
        os.makedirs("data", exist_ok=True)
        with open(f"data/dentist_{idx}.html", "w", encoding="utf-8") as f:
            f.write(d)
        
        # Add a small delay between processing each doctor
        time.sleep(3)
    
    # Save all data to Excel
    print("\n" + "="*60)
    print("SAVING DATA TO EXCEL...")
    print("="*60)
    
    df = save_to_excel(all_doctors_data)
    
    # Display sample data
    if df is not None and not df.empty:
        print("\n" + "="*60)
        print("SAMPLE DATA:")
        print("="*60)
        print(df.head().to_string(index=False))
        
except Exception as e:
    print(f"❌ Error: {e}")
    elems = []

time.sleep(5)
driver.quit()
