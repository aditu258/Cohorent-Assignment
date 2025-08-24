from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
import time, os, re, json

# Import from our modules
from gemini_service import generate_summary_with_gemini
from excel_export import save_to_excel

# Define specialties to scrape
SPECIALTIES = [
    "Cardiologist",
    "Dermatologist", 
    "Neurologist",
    "Oncologist",
    "General Surgeon",
    "Orthopedic Surgeon",
    "Neurosurgeon",
    "Pediatrician",
    "Gynecologist",
    "Psychiatrist"
]

# Define regions to search in Pune
REGIONS = ["Aundh", "Baner", "Wakad"]

# Base URL for Practo search
BASE_URL = "https://www.practo.com/search/doctors?results_type=doctor&q=%5B%7B%22word%22%3A%22{specialty}%22%2C%22autocompleted%22%3Atrue%2C%22category%22%3A%22subspeciality%22%7D%2C%7B%22word%22%3A%22{region}%22%2C%22autocompleted%22%3Atrue%2C%22category%22%3A%22locality%22%7D%5D&city=Pune&page=1"

driver = webdriver.Chrome()

def extract_contact_info(doctor_card):
    """Extract contact information by clicking the Contact Clinic button"""
    try:
        # First, check if the contact button exists
        contact_buttons = doctor_card.find_elements(By.CSS_SELECTOR, '[data-qa-id="call_button"]')
        
        if not contact_buttons:
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
                    break
        except:
            pass
        
        # Try multiple click strategies
        click_successful = False
        
        # Strategy 1: Regular click
        try:
            contact_button.click()
            click_successful = True
        except ElementClickInterceptedException:
            pass
        
        # Strategy 2: JavaScript click
        if not click_successful:
            try:
                driver.execute_script("arguments[0].click();", contact_button)
                click_successful = True
            except Exception as e:
                pass
        
        # Strategy 3: ActionChains click
        if not click_successful:
            try:
                actions = ActionChains(driver)
                actions.move_to_element(contact_button).click().perform()
                click_successful = True
            except Exception as e:
                pass
        
        if not click_successful:
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
            
            # Extract the phone number
            phone_number = phone_element.text.strip()
            
            # Additional verification - check if this is a valid phone number
            if phone_number and len(phone_number) >= 10:
                return phone_number
            else:
                return ""
            
        except TimeoutException:
            return ""
        
    except Exception as e:
        return ""

def extract_detailed_address(doctor_card):
    """Navigate to doctor's profile page and extract detailed address"""
    try:
        # Debug: Print all links in the doctor card
        all_links = doctor_card.find_elements(By.CSS_SELECTOR, 'a')
        
        # Try multiple selectors to find the doctor name link
        name_link = None
        
        # Strategy 1: Look for link inside h2 with data-qa-id
        try:
            name_link = doctor_card.find_element(By.CSS_SELECTOR, 'h2[data-qa-id="doctor_name"] a')
        except NoSuchElementException:
            pass
        
        # Strategy 2: Look for any link that contains doctor name
        if not name_link:
            try:
                name_link = doctor_card.find_element(By.CSS_SELECTOR, 'a[href*="/doctor/"]')
            except NoSuchElementException:
                pass
        
        # Strategy 3: Look for link inside info-section
        if not name_link:
            try:
                name_link = doctor_card.find_element(By.CSS_SELECTOR, '.info-section a')
            except NoSuchElementException:
                pass
        
        # Strategy 4: Look for any anchor tag with href containing doctor
        if not name_link:
            try:
                all_links = doctor_card.find_elements(By.CSS_SELECTOR, 'a[href*="doctor"]')
                if all_links:
                    name_link = all_links[0]
            except NoSuchElementException:
                pass
        
        # Strategy 5: Look for any link with href containing "practo.com"
        if not name_link:
            try:
                all_links = doctor_card.find_elements(By.CSS_SELECTOR, 'a[href*="practo.com"]')
                if all_links:
                    name_link = all_links[0]
            except NoSuchElementException:
                pass
        
        if not name_link:
            return ""
        
        # Get the href attribute
        profile_url = name_link.get_attribute('href')
        
        if not profile_url:
            return ""
        
        # Make sure it's a full URL
        if profile_url.startswith('/'):
            profile_url = "https://www.practo.com" + profile_url
        
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
            
            # Close the tab and switch back
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            
            return detailed_address
            
        except TimeoutException:
            # Close the tab and switch back
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            return ""
            
    except Exception as e:
        # Make sure we're back on the main page
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        return ""

def extract_patient_stories(doctor_card):
    """Extract patient stories/reviews from the doctor's profile page"""
    try:
        # Find the doctor name link to navigate to profile
        name_link = None
        
        # Try multiple selectors to find the doctor name link
        try:
            name_link = doctor_card.find_element(By.CSS_SELECTOR, 'h2[data-qa-id="doctor_name"] a')
        except NoSuchElementException:
            try:
                name_link = doctor_card.find_element(By.CSS_SELECTOR, 'a[href*="/doctor/"]')
            except NoSuchElementException:
                try:
                    name_link = doctor_card.find_element(By.CSS_SELECTOR, '.info-section a')
                except NoSuchElementException:
                    try:
                        all_links = doctor_card.find_elements(By.CSS_SELECTOR, 'a[href*="doctor"]')
                        if all_links:
                            name_link = all_links[0]
                    except:
                        pass
        
        if not name_link:
            return []
        
        # Get the href attribute
        profile_url = name_link.get_attribute('href')
        if not profile_url:
            return []
        
        # Make sure it's a full URL
        if profile_url.startswith('/'):
            profile_url = "https://www.practo.com" + profile_url
        
        # Open profile in new tab
        driver.execute_script(f"window.open('{profile_url}', '_blank');")
        
        # Switch to the new tab
        driver.switch_to.window(driver.window_handles[-1])
        
        # Wait for page to load
        wait = WebDriverWait(driver, 15)
        
        patient_stories = []
        
        try:
            # Look for patient stories/reviews section
            # Try to find reviews or feedback elements
            review_elements = driver.find_elements(By.CSS_SELECTOR, '[data-qa-id="review-text"]')
            
            if review_elements:
                for i, elem in enumerate(review_elements[:10]):  # Get first 10 reviews
                    try:
                        review_text = elem.text.strip()
                        if review_text and len(review_text) > 10:  # Only meaningful reviews
                            patient_stories.append(review_text)
                    except:
                        continue
            
            # If no review-text elements, try other selectors
            if not patient_stories:
                feedback_elements = driver.find_elements(By.CSS_SELECTOR, '.feedback_content')
                for i, elem in enumerate(feedback_elements[:10]):
                    try:
                        feedback_text = elem.text.strip()
                        if feedback_text and len(feedback_text) > 10:
                            patient_stories.append(feedback_text)
                    except:
                        continue
            
            # If still no stories, try looking for any text that might be reviews
            if not patient_stories:
                # Look for elements with "patient" or "review" in their text
                all_elements = driver.find_elements(By.CSS_SELECTOR, 'p, div, span')
                for elem in all_elements[:50]:  # Check first 50 elements
                    try:
                        text = elem.text.strip()
                        if text and len(text) > 20 and ('patient' in text.lower() or 'treatment' in text.lower() or 'doctor' in text.lower()):
                            if len(patient_stories) < 10:
                                patient_stories.append(text)
                    except:
                        continue
            
        except Exception as e:
            pass
        
        # Close the tab and switch back
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        
        return patient_stories
        
    except Exception as e:
        # Make sure we're back on the main page
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        return []



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
                # Check for all specialties
                if text.lower() in [
                    'cardiologist', 'cardiology', 'heart',
                    'dermatologist', 'dermatology', 'skin',
                    'neurologist', 'neurology', 'brain',
                    'oncologist', 'oncology', 'cancer',
                    'general surgeon', 'surgery',
                    'orthopedic surgeon', 'orthopedics', 'orthopaedic',
                    'neurosurgeon', 'neurosurgery',
                    'pediatrician', 'pediatrics', 'paediatrician', 'paediatrics',
                    'gynecologist', 'gynecology', 'gynaecologist', 'gynaecology', 'obstetrics',
                    'psychiatrist', 'psychiatry', 'mental health',
                    'dentist', 'dental', 'orthodontist', 'endodontist', 'periodontist'
                ]:
                    doctor_info['specialty'] = text
                    break
        except:
            doctor_info['specialty'] = "Unknown"  # Default
        
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
        
        # Generate fake email based on doctor's name
        try:
            if doctor_info['doctors_name'] and doctor_info['doctors_name'] != "Unknown":
                # Clean the name and create email
                name_parts = doctor_info['doctors_name'].lower().split()
                if len(name_parts) >= 2:
                    # Use first and last name
                    email = f"{name_parts[0]}.{name_parts[-1]}@gmail.com"
                else:
                    # Use single name
                    email = f"{name_parts[0]}@gmail.com"
                
                # Remove any special characters and spaces
                email = email.replace(" ", "").replace("-", "").replace("'", "")
                doctor_info['contact_email'] = email
            else:
                doctor_info['contact_email'] = "doctor@gmail.com"
        except:
            doctor_info['contact_email'] = "doctor@gmail.com"
        
    except Exception as e:
        pass
    
    return doctor_info



try:
    all_doctors_data = []
    
    # Process each region completely with all specialties
    for region_idx, region in enumerate(REGIONS):
        # Process all specialties for this region
        for specialty_idx, specialty in enumerate(SPECIALTIES):
            # Navigate to the specialty-region page
            search_url = BASE_URL.format(
                specialty=specialty.replace(" ", "%20"),
                region=region.replace(" ", "%20")
            )
            driver.get(search_url)
            
            # Wait for doctor cards to load
            try:
                elems = WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.u-border-general--bottom"))
                )
            except TimeoutException:
                continue
            
            # Process only first 5 doctors for each specialty-region combination
            doctors_to_process = min(5, len(elems))
            
            for idx, elem in enumerate(elems[:doctors_to_process]):
                
                # Extract all doctor details (including detailed address)
                doctor_info = extract_doctor_details(elem)
                
                # Extract contact information
                phone_number = extract_contact_info(elem)
                doctor_info['contact_number'] = phone_number
                
                # Extract patient stories and generate summary
                patient_stories = extract_patient_stories(elem)
                
                if patient_stories:
                    summary = generate_summary_with_gemini(patient_stories)
                    doctor_info['summary_pros_cons'] = summary
                else:
                    doctor_info['summary_pros_cons'] = "No patient stories available for summary."
                
                # Add region information to doctor data
                doctor_info['region'] = region
                
                # Add to our data collection
                all_doctors_data.append(doctor_info)
                
                # Get the HTML content for backup
                d = elem.get_attribute("outerHTML")
                
                # Save to file with specialty and region prefix
                os.makedirs("data", exist_ok=True)
                specialty_clean = specialty.lower().replace(" ", "_")
                region_clean = region.lower().replace(" ", "_")
                with open(f"data/{specialty_clean}_{region_clean}_{idx}.html", "w", encoding="utf-8") as f:
                    f.write(d)
                
                # Add a small delay between processing each doctor
                time.sleep(3)
            
            # Add delay between specialties within the same region
            time.sleep(3)
        
        # Add delay between regions
        time.sleep(5)
    
    # Save all data to Excel
    df = save_to_excel(all_doctors_data)      
except Exception as e:
    elems = []
time.sleep(5)
driver.quit()