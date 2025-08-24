from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
import time, os, re, json
import pandas as pd
import google.generativeai as genai

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyCYvmNfbSxbhh_mBDpxWPGIVdUsx-GruWo"  # Replace with your actual API key
genai.configure(api_key=GEMINI_API_KEY)

# Configure generation config for better compatibility
generation_config = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 40,
    "max_output_tokens": 2048,
}

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

# Base URL for Practo search
BASE_URL = "https://www.practo.com/search/doctors?results_type=doctor&q=%5B%7B%22word%22%3A%22{specialty}%22%2C%22autocompleted%22%3Atrue%2C%22category%22%3A%22subspeciality%22%7D%2C%7B%22word%22%3A%22Aundh%22%2C%22autocompleted%22%3Atrue%2C%22category%22%3A%22locality%22%7D%5D&city=Pune&page=1"

driver = webdriver.Chrome()

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
            print("⚠️ No profile link found for extracting patient stories")
            return []
        
        # Get the href attribute
        profile_url = name_link.get_attribute('href')
        if not profile_url:
            return []
        
        # Make sure it's a full URL
        if profile_url.startswith('/'):
            profile_url = "https://www.practo.com" + profile_url
        
        print(f"📖 Navigating to profile for patient stories: {profile_url}")
        
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
                print(f"📝 Found {len(review_elements)} review elements")
                for i, elem in enumerate(review_elements[:10]):  # Get first 10 reviews
                    try:
                        review_text = elem.text.strip()
                        if review_text and len(review_text) > 10:  # Only meaningful reviews
                            patient_stories.append(review_text)
                            print(f"  Review {i+1}: {review_text[:50]}...")
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
                            print(f"  Feedback {i+1}: {feedback_text[:50]}...")
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
                                print(f"  Story {len(patient_stories)}: {text[:50]}...")
                    except:
                        continue
            
        except Exception as e:
            print(f"❌ Error extracting patient stories: {e}")
        
        # Close the tab and switch back
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        
        print(f"✅ Extracted {len(patient_stories)} patient stories")
        return patient_stories
        
    except Exception as e:
        print(f"❌ Error in extract_patient_stories: {e}")
        # Make sure we're back on the main page
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        return []

def generate_summary_with_gemini(patient_stories):
    """Generate a 2-line summary using Gemini API"""
    try:
        if not patient_stories:
            return "No patient stories available for summary."
        
        # Prepare the prompt for Gemini
        stories_text = "\n\n".join([f"Story {i+1}: {story}" for i, story in enumerate(patient_stories[:10])])
        
        prompt = f"""
        Based on the following patient stories and reviews about a doctor, provide a concise 2-line paragraph summary highlighting the key pros and cons, and overall recommendation.

        Patient Stories:
        {stories_text}

        Please provide exactly 2 lines as a natural paragraph (no "Line 1:" or "Line 2:" labels):
        First line: Key strengths and positive aspects
        Second line: Areas of concern (if any) and overall recommendation

        Write as a natural flowing paragraph with just 2 lines.
        """
        
        # Try different model names - prioritize Gemini Flash
        model_names = ['gemini-2.5-flash']
        
        for model_name in model_names:
            try:
                print(f"🤖 Trying model: {model_name}")
                model = genai.GenerativeModel(model_name, generation_config=generation_config)
                response = model.generate_content(prompt)
                
                summary = response.text.strip()
                print(f"✅ Gemini Summary: {summary}")
                
                return summary
                
            except Exception as model_error:
                print(f"❌ Model {model_name} failed: {model_error}")
                continue
        
        # If all models fail, create a simple summary manually
        print("⚠️ All Gemini models failed, creating manual summary...")
        return create_manual_summary(patient_stories)
        
    except Exception as e:
        print(f"❌ Error generating summary with Gemini: {e}")
        return "Summary generation failed."

def create_manual_summary(patient_stories):
    """Create a simple manual summary when Gemini API fails"""
    try:
        if not patient_stories:
            return "No patient stories available for summary."
        
        # Count positive and negative keywords
        positive_keywords = ['good', 'excellent', 'great', 'amazing', 'satisfied', 'recommend', 'best', 'professional', 'caring', 'gentle', 'painless', 'comfortable']
        negative_keywords = ['bad', 'poor', 'terrible', 'painful', 'expensive', 'rude', 'unprofessional', 'disappointed', 'worst', 'avoid']
        
        positive_count = 0
        negative_count = 0
        
        for story in patient_stories:
            story_lower = story.lower()
            for keyword in positive_keywords:
                if keyword in story_lower:
                    positive_count += 1
            for keyword in negative_keywords:
                if keyword in story_lower:
                    negative_count += 1
        
        # Create summary based on sentiment
        if positive_count > negative_count:
            line1 = f"Positive feedback with {positive_count} positive mentions including professional care and patient satisfaction."
            line2 = f"Overall recommended based on {len(patient_stories)} patient reviews."
        elif negative_count > positive_count:
            line1 = f"Mixed feedback with {negative_count} concerns mentioned by patients."
            line2 = f"Consider with caution based on {len(patient_stories)} patient reviews."
        else:
            line1 = f"Balanced feedback with {positive_count} positive and {negative_count} negative mentions."
            line2 = f"Mixed recommendations from {len(patient_stories)} patient reviews."
        
        manual_summary = f"{line1}\n{line2}"
        print(f"📋 Manual Summary: {manual_summary}")
        
        return manual_summary
        
    except Exception as e:
        print(f"❌ Error creating manual summary: {e}")
        return f"Summary based on {len(patient_stories)} patient reviews."

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
    
    # Remove rows with missing data
    print(f"\n🔍 Checking for incomplete records...")
    print(f"Original records: {len(df)}")
    
    # Define required fields that must not be empty
    required_fields = ['doctors_name', 'contact_number', 'complete_address', 'specialty']
    
    # Create a mask for complete records
    complete_mask = True
    for field in required_fields:
        if field in df.columns:
            # Check if field is not empty and not just whitespace
            field_mask = (df[field].notna()) & (df[field].astype(str).str.strip() != '')
            complete_mask = complete_mask & field_mask
            missing_count = (~field_mask).sum()
            if missing_count > 0:
                print(f"  ❌ {missing_count} records missing '{field}'")
    
    # Filter to keep only complete records
    df_complete = df[complete_mask].copy()
    removed_count = len(df) - len(df_complete)
    
    print(f"✅ Complete records: {len(df_complete)}")
    print(f"🗑️ Removed {removed_count} incomplete records")
    
    # Save only complete records
    df_complete.to_excel(filename, index=False)
    print(f"✅ Data saved to {filename}")
    print(f"Final records: {len(df_complete)}")
    
    # Print summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY:")
    print("="*60)
    print(f"Total doctors processed: {len(df)}")
    print(f"Complete records saved: {len(df_complete)}")
    print(f"Incomplete records removed: {removed_count}")
    
    # Show specialty breakdown
    if 'specialty' in df_complete.columns:
        print(f"\n📊 SPECIALTY BREAKDOWN:")
        specialty_counts = df_complete['specialty'].value_counts()
        for specialty, count in specialty_counts.items():
            print(f"  {specialty}: {count} doctors")
    
    print(f"\n📋 FIELD COMPLETION:")
    print(f"Doctors with names: {len(df_complete[df_complete['doctors_name'] != ''])}")
    print(f"Doctors with contact numbers: {len(df_complete[df_complete['contact_number'] != ''])}")
    print(f"Doctors with specialties: {len(df_complete[df_complete['specialty'] != ''])}")
    print(f"Doctors with addresses: {len(df_complete[df_complete['complete_address'] != ''])}")
    print(f"Doctors with ratings: {len(df_complete[df_complete['ratings'] != ''])}")
    print(f"Doctors with reviews: {len(df_complete[df_complete['reviews'] != ''])}")
    
    return df_complete

try:
    all_doctors_data = []
    
    # Process each specialty
    for specialty_idx, specialty in enumerate(SPECIALTIES):
        print(f"\n{'='*80}")
        print(f"PROCESSING SPECIALTY {specialty_idx + 1}/{len(SPECIALTIES)}: {specialty}")
        print(f"{'='*80}")
        
        # Navigate to the specialty page
        specialty_url = BASE_URL.format(specialty=specialty.replace(" ", "%20"))
        print(f"🔗 Navigating to: {specialty_url}")
        driver.get(specialty_url)
        
        # Wait for doctor cards to load
        try:
            elems = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.u-border-general--bottom"))
            )
            print(f"✅ Found {len(elems)} doctors for {specialty}")
        except TimeoutException:
            print(f"❌ No doctors found for {specialty}")
            continue
        
        # Process only first 5 doctors for each specialty
        doctors_to_process = min(5, len(elems))
        print(f"📊 Processing {doctors_to_process} doctors for {specialty}")
        
        for idx, elem in enumerate(elems[:doctors_to_process]):
            print(f"\n{'='*50}")
            print(f"Processing {specialty} doctor {idx + 1}/{doctors_to_process}")
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
            
            # Extract patient stories and generate summary
            print("📖 Extracting patient stories for summary...")
            patient_stories = extract_patient_stories(elem)
            
            if patient_stories:
                print("🤖 Generating summary with Gemini...")
                summary = generate_summary_with_gemini(patient_stories)
                doctor_info['summary_pros_cons'] = summary
                print(f"📋 Summary: {summary}")
            else:
                doctor_info['summary_pros_cons'] = "No patient stories available for summary."
                print("⚠️ No patient stories found for summary")
            
            # Add to our data collection
            all_doctors_data.append(doctor_info)
            
            # Get the HTML content for backup
            d = elem.get_attribute("outerHTML")
            
            # Save to file with specialty prefix
            os.makedirs("data", exist_ok=True)
            specialty_clean = specialty.lower().replace(" ", "_")
            with open(f"data/{specialty_clean}_{idx}.html", "w", encoding="utf-8") as f:
                f.write(d)
            
            # Add a small delay between processing each doctor
            time.sleep(3)
        
        # Add delay between specialties
        print(f"⏳ Waiting 5 seconds before next specialty...")
        time.sleep(5)
    
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
