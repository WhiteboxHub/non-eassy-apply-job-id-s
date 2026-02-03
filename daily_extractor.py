import yaml
import logging
import os
import time
import re
from bot.utils.logger import logger
from bot.core.browser import Browser
from bot.core.session import Session
from bot.discovery.extractor import JobExtractor
from bot.persistence.store import Store
from bot.persistence.api_store import APIStore
from bot.api.website_client import fetch_candidates_from_api
from dotenv import load_dotenv

load_dotenv()

def load_candidates_with_enrichment():
    """
    Primary Source: YAML.
    Secondary Source: Dynamic (API/DB) for enriching missing locations.
    """
    yaml_candidates = []
    global_settings = {}
    
    # 1. Load YAML data
    try:
        yaml_path = "candidate_marketing.yaml"
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as stream:
                data = yaml.safe_load(stream)
                yaml_candidates = data.get('candidates', [])
                global_settings = data.get('settings', {})
                logger.info(f"Loaded {len(yaml_candidates)} candidates from {yaml_path}")
        else:
            logger.warning(f"{yaml_path} not found. Will attempt to load all from dynamic source.")
    except Exception as e:
        logger.error(f"Error reading YAML: {e}")

    # 2. Fetch Dynamic Data for enrichment/fallback
    dynamic_candidates = []
    try:
        dynamic_candidates = fetch_candidates_from_api()
        logger.info(f"Loaded {len(dynamic_candidates)} dynamic candidates for enrichment.")
    except Exception as e:
        logger.warning(f"Could not load dynamic candidates: {e}")

    # 3. Merging Logic
    final_candidates = []
    processed_emails = set()
    processed_cids = set()
    
    # First, process candidates from YAML - these are our "Marketing" candidates
    for cand in yaml_candidates:
        target_username = (cand.get('linkedin_username') or '').lower().strip()
        target_name = (cand.get('name') or '').lower().strip()
        cand_id = cand.get('candidate_id')
        
        # Match with dynamic data for enrichment
        match = None
        for dc in dynamic_candidates:
            dc_email = (dc.get('linkedin_username') or dc.get('email') or '').lower().strip()
            dc_cid = str(dc.get('candidate_id', dc.get('id', '')))
            
            if (target_username and dc_email == target_username) or (cand_id and str(cand_id) == dc_cid):
                match = dc
                break
        
        if match:
            # 1. Enrich Credentials if missing or placeholder
            if (not cand.get('linkedin_username') or cand.get('linkedin_username') == "example@gmail.com") and match.get('linkedin_username'):
                cand['linkedin_username'] = match['linkedin_username']
            if (not cand.get('linkedin_password') or cand.get('linkedin_password') == "*****") and match.get('linkedin_password'):
                cand['linkedin_password'] = match['linkedin_password']
            
            # 2. Enrich Keywords if missing
            if not cand.get('keywords') and match.get('keywords'):
                cand['keywords'] = match['keywords']
            
            # 3. Enrich Locations/Zipcodes if missing
            # Check multiple possible field names: locations, zipcodes, zip_code
            db_locs = match.get('locations') or match.get('zipcodes') or match.get('zip_code') or []
            if not cand.get('locations') and db_locs:
                cand['locations'] = [db_locs] if isinstance(db_locs, (str, int)) else db_locs
                logger.info(f"✅ Enriched YAML candidate {cand_id} ('{cand.get('name')}') with zipcodes from DB: {cand['locations']}")
        
        # Fallback for keywords/locations if still missing
        if not cand.get('keywords'):
            cand['keywords'] = global_settings.get('positions', ["Software Engineer"])
        if not cand.get('locations'):
             cand['locations'] = []

        final_candidates.append(cand)
        if target_username: processed_emails.add(target_username)
        if cand_id: processed_cids.add(str(cand_id))

    # Second, check if there are candidates in the dynamic source that should also run
    # (Optional: User said "it has to run only for those candidate [in candidate_marketing]", 
    # but usually if the flag is True in DB we should also run them)
    for dc in dynamic_candidates:
        dc_email = (dc.get('linkedin_username') or dc.get('email') or '').lower().strip()
        dc_cid = str(dc.get('candidate_id', dc.get('id', '')))
        
        if dc_email not in processed_emails and dc_cid not in processed_cids:
            # Check the flag in DB
            if dc.get('run_extract_linkedin_jobs') is True or str(dc.get('run_extract_linkedin_jobs')).lower() == 'true':
                logger.info(f"➕ Adding candidate {dc_cid} from database (Flag is ON).")
                final_candidates.append(dc)
                if dc_email: processed_emails.add(dc_email)

    return final_candidates, global_settings

    return final_candidates, global_settings

def run_extraction():
    store = Store()
    api_store = APIStore()
    
    candidates, global_settings = load_candidates_with_enrichment()
    
    if not candidates:
        logger.error("No candidates found to process.")
        return

    for cand in candidates:
        try:
            candidate_id = cand.get('candidate_id', 'unknown')
            
            # Respect the flag (Checking YAML flag or Database flag)
            run_flag = cand.get('run_extract_linkedin_jobs')
            if run_flag is False or str(run_flag).lower() == 'false':
                logger.info(f"⏭️ Skipping {candidate_id} - 'run_extract_linkedin_jobs' flag is disabled.")
                continue

            username = cand.get('linkedin_username')
            password = cand.get('linkedin_password')
            keywords = cand.get('keywords', ["Software Engineer"])
            locations = cand.get('locations', [])
            
            # Check if login is possible
            can_login = username and password and password != "*****"
            
            logger.info(f"--- Processing Candidate: {candidate_id} ({username if username else 'No Login'}) ---")
            logger.info(f"Keywords: {keywords}")
            logger.info(f"Locations: {locations}")

            if not locations:
                logger.warning(f"Candidate {candidate_id} has no locations. Skipping.")
                continue

            # File setup
            exports_dir = os.path.abspath(os.path.join(os.getcwd(), "data", "exports"))
            os.makedirs(exports_dir, exist_ok=True)
            csv_filename = os.path.join(exports_dir, "extractor_job_links.csv")
            
            # Distance and Limit settings
            max_total_limit = cand.get('max_applications_per_run') or global_settings.get('max_applications_per_run', 50)
            # User requested no limit like 15 per zip, so we set a high enough "infinite" per-zip limit
            jobs_per_zip = 999 
            
            total_candidate_extracted = 0
            
            use_ladder = global_settings.get('distance_ladder', True)
            if use_ladder:
                dist_list = [5, 10, 25, 50, 100]
                max_dist = cand.get('distance_miles') or global_settings.get('distance_miles', 50)
                dist_list = [d for d in dist_list if d <= max_dist]
            else:
                dist_list = [cand.get('distance_miles') or global_settings.get('distance_miles', 50)]

            # Profile setup
            profile_path = os.path.join(os.getcwd(), "data", "profiles", str(candidate_id))
            
            browser = None
            remaining_locations = list(locations)
            
            while remaining_locations:
                current_loc = str(remaining_locations[0]).strip()
                
                try:
                    if browser is None:
                        logger.info(f"Initializing browser for {candidate_id}...")
                        browser = Browser(profile_path=profile_path)
                        if can_login:
                            session = Session(browser.driver)
                            session.login(username, password)
                        else:
                            logger.info("Running without login (using profile or public search)...")

                    location_extraction_total = 0
                    for current_dist in dist_list:
                        # Exit if we hit the TOTAL CANDIDATE limit
                        if total_candidate_extracted >= max_total_limit:
                            logger.info(f"✅ Reached TOTAL candidate limit of {max_total_limit}. Stopping all extractions.")
                            remaining_locations = [] # Clear locations to break outer loop
                            break
                        
                        # Exit if we hit the (now very high) per-zip limit
                        if location_extraction_total >= jobs_per_zip:
                            break
                        
                        # Remaining for this specific candidate
                        remaining_for_cand = max_total_limit - total_candidate_extracted
                            
                        logger.info(f"  --- Distance Bucket: {current_dist} miles (Candidate Total: {total_candidate_extracted}/{max_total_limit}) ---")
                        
                        extractor = JobExtractor(
                            browser, 
                            candidate_id=candidate_id, 
                            csv_path=csv_filename, 
                            distance_miles=current_dist,
                            api_store=api_store
                        )
                        
                        zip_match = re.search(r'\b\d{5,6}\b', current_loc)
                        zipcode = zip_match.group(0) if zip_match else current_loc

                        logger.info(f"Starting extraction for: {current_loc} at {current_dist}mi")
                        newly_found = extractor.start_extract(keywords, locations=[current_loc], zipcode=zipcode, limit=remaining_for_cand)
                        location_extraction_total += newly_found
                        total_candidate_extracted += newly_found
                    
                    remaining_locations.pop(0)
                    time.sleep(5)

                except Exception as e:
                    err_msg = str(e).lower()
                    logger.error(f"Error processing location {current_loc}: {e}")
                    
                    if any(x in err_msg for x in ['invalid session', 'disconnected', 'no such window', 'browser_crash', 'retry_failed']):
                        logger.warning("Session issues detected. Restarting browser...")
                        if browser:
                            try: browser.driver.quit()
                            except: pass
                        browser = None
                    else:
                        logger.warning(f"Skipping {current_loc} due to logical error.")
                        remaining_locations.pop(0)
                        if browser:
                            try: browser.driver.quit()
                            except: pass
                        browser = None

            if browser:
                try: browser.driver.quit()
                except: pass
        except Exception as cand_e:
            logger.error(f"❌ Critical error processing candidate {cand.get('candidate_id')}: {cand_e}")
            continue

    api_store.close()
    logger.info("Daily Extraction completed.")

if __name__ == '__main__':
    # When run directly, it executes once.
    run_extraction()

