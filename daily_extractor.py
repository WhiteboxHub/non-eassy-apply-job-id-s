import yaml
import logging
import os
import time
from bot.utils.logger import logger
from bot.core.browser import Browser
from bot.core.session import Session
from bot.discovery.extractor import JobExtractor
from bot.persistence.store import Store
from bot.persistence.mysql_store import MySQLStore
from dotenv import load_dotenv

load_dotenv()

def run_extraction():
    store = Store()
    mysql_store = MySQLStore()
    
    # --- AUTO-IMPORT from candidate_marketing.yaml ---
    # This ensures we always use the latest config without a separate import step
    try:
        with open("candidate_marketing.yaml", 'r') as stream:
            data = yaml.safe_load(stream)
            
        yaml_candidates = data.get('candidates', [])
        logger.info(f"Loaded {len(yaml_candidates)} candidates from YAML.")
    except Exception as e:
        logger.error(f"Failed to load candidate_marketing.yaml: {e}")
        return

    # Process each candidate directly from YAML
    for cand in yaml_candidates:
        candidate_id = cand['candidate_id']
        username = cand['linkedin_username']
        password = cand['linkedin_password']
        
        # Get keywords/locations directly from YAML
        custom_keywords = cand.get('keywords', [])
        locations = cand.get('locations', [])
        
        # Backwards compatibility check
        if not locations:
             # Try old 'zipcodes' or 'zipcode' fields
             locations = cand.get('zipcodes', [])
             if not locations:
                 single = cand.get('zipcode')
                 if single: locations = [single]

        if not username or not password:
             logger.warning(f"Candidate {candidate_id} missing credentials. Attempting to use saved session (profile).")
             # continue # Don't skip, try with profile

        logger.info(f"Starting extraction for candidate: {candidate_id} ({username})")
        logger.info(f"  Custom Keywords: {len(custom_keywords)} ({', '.join(custom_keywords[:3])}...)")
        logger.info(f"  Locations: {len(locations)} ({', '.join(locations[:3])}...)")

        # Enable persistent profile to allow working without credentials (cookie-based)
        profile_path = os.path.join(os.getcwd(), "data", "profiles", candidate_id)
        
        # Get configuration from YAML settings block
        global_settings = data.get('settings', {})
        positions = custom_keywords if custom_keywords else global_settings.get('positions', ["Software Engineer"])
        distance_miles = global_settings.get('distance_miles', 50)
        
        if not positions:
            positions = ["Software Engineer"] 

        safe_name = username.split('@')[0]
        csv_filename = f"{safe_name}_extracted_jobs.csv"

        # Browser management wrapper
        browser = None
        
        # Track which locations we have finished to avoid repeating on restart
        # But for simplicity, we iterate and if error, we restart from the *current* failed one? 
        # Or just restart session for the remaining items.
        
        # Flat list of tasks (Location)
        todo_locations = list(locations)
        
        while len(todo_locations) > 0:
            current_location = todo_locations[0]
            
            try:
                # Initialize Browser if needed
                if browser is None:
                    logger.info("Initializing browser session...")
                    browser = Browser(profile_path=profile_path)
                    session = Session(browser.driver)
                    session.login(username, password)
                
                # Helper to check browser life
                if not browser.driver.session_id:
                    raise Exception("Browser died, need restart")

                extractor = JobExtractor(
                    browser, 
                    candidate_id=candidate_id, 
                    csv_path=csv_filename, 
                    distance_miles=distance_miles,
                    mysql_store=mysql_store
                )
                
                # Process current location
                try:
                    # Input is now "Bangalore 560100"
                    search_location = current_location.strip()
                    
                    # Try to extract just numbers for the "zipcode" field in CSV
                    import re
                    zip_match = re.search(r'\b\d{6}\b', search_location)
                    zipcode = zip_match.group(0) if zip_match else search_location
                    
                    logger.info(f"Extracting jobs for location: {search_location} (Zipcode: {zipcode})")
                    extractor.start_extract(positions, locations=[search_location], zipcode=zipcode)
                    
                    # If successful, remove from todo list
                    todo_locations.pop(0)
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error processing location {current_location}: {e}")
                    err_str = str(e).lower()
                    # Check for crash keywords OR the retry failure message which often wraps a crash
                    if any(k in err_str for k in ['disconnected', 'closed', 'invalid session', 'no such window', 'retry_failed', 'next_jobs_page']):
                        logger.warning("Browser crash detected. Restarting session for current location...")
                        if browser:
                            try: browser.driver.quit()
                            except: pass
                        browser = None # Trigger re-init
                    else:
                        # Non-critical error, skip this location
                        logger.warning(f"Skipping location {current_location} due to logic error (not crash or retry failure).")
                        todo_locations.pop(0)

            except Exception as e:
                logger.error(f"Major session error: {e}")
                if browser:
                    try: browser.driver.quit()
                    except: pass
                browser = None
                # Prevent infinite loop if something is permanently broken
                # But we want to try at least once for the next location?
                # For now, just retry the loop which will re-init browser.
                time.sleep(5)

        # Cleanup
        if browser:
            try: browser.driver.quit()
            except: pass
            
    # Final DB cleanup
    mysql_store.close()

if __name__ == '__main__':
    run_extraction()
