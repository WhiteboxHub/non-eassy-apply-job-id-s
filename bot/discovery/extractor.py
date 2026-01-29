import time
import random
import logging
from bs4 import BeautifulSoup

from bot.utils.delays import sleep_random
from bot.utils.selectors import LOCATORS
from bot.utils.logger import logger
from bot.utils.retry import retry
from bot.utils.stale_guard import safe_action
from bot.discovery.job_identity import JobIdentity
from bot.discovery.search import Search
from bot.discovery.scroll_tracker import ScrollTracker
from bot.persistence.store import Store
from bot.persistence.mysql_store import MySQLStore
from bot.utils.human_interaction import HumanInteraction

import csv
import os

class JobExtractor(Search):
    def __init__(self, browser, candidate_id="default", blacklist=None, experience_level=None, csv_path=None, distance_miles=50, mysql_store=None):
        # We don't need workflow for extraction as we are not applying here
        # Passing None for workflow
        super().__init__(browser, None, blacklist, experience_level)
        self.candidate_id = candidate_id
        self.csv_path = csv_path
        self.distance_miles = distance_miles  # Distance filter: 10, 25, 50, 100 miles
        self.store = Store()
        self.mysql_store = mysql_store if mysql_store else MySQLStore()
        self.seen_jobs = self._load_seen_jobs()
        
        # Initialize CSV if provided
        if self.csv_path and not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
                writer.writerow(['job_id', 'title', 'company', 'location', 'zipcode', 'url', 'date_extracted', 'is_easy_apply'])

    def _load_seen_jobs(self):
        """Load already extracted job IDs from database to prevent duplicates"""
        try:
            res = self.store.con.execute("SELECT job_id FROM extracted_jobs").fetchall()
            return {row[0] for row in res}
        except Exception as e:
            logger.warning(f"Could not load seen jobs: {e}")
            return set()

    def start_extract(self, positions, locations, zipcode=""):
        combos = []
        # Ensure lists
        positions = [positions] if isinstance(positions, str) else positions
        locations = [locations] if isinstance(locations, str) else locations

        # Randomize combinations
        combo_list = []
        for p in positions:
            for l in locations:
                combo_list.append((p, l))
        random.shuffle(combo_list)

        for position, location in combo_list:
            logger.info(f"Extracting jobs for {position}: {location} (Zipcode: {zipcode})", step="extract_init")
            self.extraction_loop(position, location, zipcode)

    def extraction_loop(self, position, location, zipcode=""):
        jobs_per_page = 0
        start_time = time.time()
        human = HumanInteraction(self.browser)
        
        # Initial Load
        self.next_jobs_page(position, location, jobs_per_page)
        time.sleep(5)

        while time.time() - start_time < self.MAX_SEARCH_TIME:
            try:
                # Timer log
                mins_left = (self.MAX_SEARCH_TIME - (time.time() - start_time)) // 60
                logger.info(f"Page {int(jobs_per_page/25) + 1} | {mins_left}m left", step="job_extract")
                
                # Check for "No jobs found"
                if "No matching jobs found" in self.browser.page_source:
                    logger.info("No more jobs found for this search.", step="job_extract", event="no_results")
                    break

                # --- STEP 1: Scroll to load all jobs on current page ---
                time.sleep(4) # Wait for page results to settle
                
                logger.info("Starting scroll routine...", step="job_extract")
                last_height = 0
                stuck_count = 0
                
                for i in range(15):
                    try:
                        # Check browser health
                        if not self.browser.service.process or not self.browser.session_id:
                             raise Exception("Browser died")

                        # Aggressive JS Scroll that tries multiple selectors or fallbacks to window
                        new_height = self.browser.execute_script("""
                            try {
                                var selectors = ['.jobs-search-results-list', '.jobs-search-results', '.scaffold-layout__list-container', 'section.jobs-search-results-list'];
                                var list = null;
                                for (var s of selectors) {
                                    list = document.querySelector(s);
                                    if (list) break;
                                }
                                
                                if (list) {
                                    list.scrollTop = list.scrollHeight;
                                    return list.scrollHeight;
                                } else {
                                    // Fallback to window scroll if list not identified
                                    window.scrollTo(0, document.body.scrollHeight);
                                    return document.body.scrollHeight;
                                }
                            } catch(e) { return -1; }
                        """)
                        
                        if new_height == -1:
                            logger.warning("Scroll script error (JS side).", step="job_extract")
                            break

                        time.sleep(2) # Longer wait for content to load
                        
                        if new_height == last_height:
                            stuck_count += 1
                        else:
                            last_height = new_height
                            stuck_count = 0
                            logger.debug(f"Height change: {new_height}", step="job_extract")
                        
                        if stuck_count >= 3: # Stop earlier if height doesn't change
                            break
                            
                    except Exception as e:
                        err_str = str(e).lower()
                        if 'invalid session' in err_str or 'no such window' in err_str:
                             logger.error("Browser session lost during scroll. Terminating loop for restart.", step="job_extract")
                             raise e # Propagate to trigger restart in daily_extractor
                        logger.warning(f"Scroll iteration failed: {e}")
                        break

                logger.info("Scrolling complete.", step="job_extract")

                # --- STEP 2: Extract all jobs on this page ---
                if self.is_present(self.locator["links"]):
                    links = self.get_elements("links")
                    logger.info(f"Detected {len(links)} job cards on Page {int(jobs_per_page/25) + 1}.", step="job_extract")
                    extracted_on_page = 0
                    
                    for link in links:
                        try:
                             job_id = JobIdentity.extract_job_id(link)
                             if not job_id:
                                 continue
                             
                             if job_id in self.seen_jobs:
                                 logger.debug(f"Job {job_id} already seen, skipping.", step="job_extract")
                                 continue
                             
                             # Click job card to load details/URL
                             logger.info(f"Fetching details for job: {job_id}...", step="job_extract")
                             self.browser.execute_script("arguments[0].click();", link)
                             time.sleep(1)

                             # Skip Easy Apply
                             if "Easy Apply" in link.text:
                                 logger.info(f"Skipping Easy Apply job: {job_id}", step="job_extract")
                                 self.seen_jobs.add(job_id)
                                 continue

                             self.save_job(job_id, link, position, location, zipcode)
                             self.seen_jobs.add(job_id)
                             extracted_on_page += 1
                             
                        except Exception as e:
                             logger.warning(f"Error processing card {job_id}: {e}")
                             continue
                    
                    logger.info(f"Finished Page {int(jobs_per_page/25) + 1}: {extracted_on_page} NEW links saved.", step="job_extract")

                # --- STEP 3: Move to Next Page ---
                # Attempt to find "Next" button first
                try:
                    next_button = self.browser.find_element(By.XPATH, "//button[@aria-label='Next' or contains(@class, 'pagination__button--next')]")
                    if next_button and next_button.is_enabled():
                        logger.info("Clicking NEXT button...", step="job_extract")
                        self.browser.execute_script("arguments[0].click();", next_button)
                        jobs_per_page += 25
                        time.sleep(5)
                        continue
                except:
                    pass

                # Fallback to URL-based pagination
                logger.info("Next button not found, using URL pagination...", step="job_extract")
                jobs_per_page += 25
                if jobs_per_page >= 1000: break
                self.next_jobs_page(position, location, jobs_per_page)
                time.sleep(5)

            except Exception as e:
                logger.error(f"Extraction loop error: {e}", step="extract_error")
                break

    @retry(max_attempts=3, delay=1)
    def next_jobs_page(self, position, location, jobs_per_page):
        experience_level_str = ",".join(map(str, self.experience_level)) if self.experience_level else ""
        experience_level_param = f"&f_E={experience_level_str}" if experience_level_str else ""
        
        # Distance filter mapping: 10, 25, 50, 100 miles
        # LinkedIn uses f_D parameter for distance
        distance_param = f"&f_D={self.distance_miles}" if self.distance_miles else ""
        
        # Sort by distance (DD = Distance, R = Relevance, DD is for Date)
        sort_param = "&sortBy=DD"  # Sort by distance
        
        # Add origin and refresh for better recognition
        extra_params = "&origin=JOB_SEARCH_PAGE_LOCATION_AUTOCOMPLETE&refresh=true"
        
        # Improve location recognition for raw zipcodes
        if location.isdigit() and len(location) == 6:
             formatted_location = f"{location}, India"
        else:
             formatted_location = location

        # f_TPR=r86400 is the filter for Past 24 Hours
        location_param = f"&location={formatted_location}"
        url = ("https://www.linkedin.com/jobs/search/?f_TPR=r86400&keywords=" +
               position + location_param + "&start=" + str(jobs_per_page) + 
               experience_level_param + distance_param + sort_param + extra_params)
        
        logger.info(f"Navigating to: {url}", step="job_extract", event="navigation")
        self.browser.get(url)
        self.browser.execute_script("window.scrollTo(0, 0);")

    def save_job(self, job_id, element, position, search_location, zipcode=""):
        try:
            # Get all text lines, filtered for empty space
            all_lines = [l.strip() for l in element.text.split('\n') if l.strip()]
            
            # Remove badges/labels from lines to find real data
            filter_labels = ["Easy Apply", "Promoted", "Actively recruiting", "Be an early applicant", "1 week ago", "2 weeks ago", "days ago", "hours ago"]
            clean_lines = []
            for line in all_lines:
                if not any(label in line for label in filter_labels):
                    clean_lines.append(line)
            
            # Heuristic for LinkedIn Job Card
            # Text usually looks like:
            # "Job Title"
            # "Company Name"
            # "Location"
            # "Active 3 days ago"
            
            title = clean_lines[0] if len(clean_lines) > 0 else "Unknown"
            
            # Remove Title from lines to find Company/Location
            remaining_lines = clean_lines[1:]
            
            company = "Unknown"
            location = search_location # Default to search location if specific one not found

            if len(remaining_lines) > 0:
                company = remaining_lines[0]
                # Cleanup company name (sometimes has "3.5 star rating" or "with verification")
                company = company.split(" with verification")[0].strip()
                company = company.replace("\n", " ").strip()
            
            if len(remaining_lines) > 1:
                # Next line is usually location
                raw_loc = remaining_lines[1]
                # Validate if it looks like a location (not "Active 2 days ago")
                if "ago" not in raw_loc and "Apply" not in raw_loc:
                    location = raw_loc

            # Fallback: if Location still looks like the search term (e.g. zipcode), keep it or try to find a better one
            # The user reported "Turing" as location for "Remote Data Scientist" -> "Remote Data Scientist", "Turing", "500032"
            # If the extracted location equals the zip code, it might be wrong if there was a real location text available.
            
            # Special fix for the user's issue:
            # "Remote Data Scientist with verification" was title?
            # "Turing" was company
            # "500032" was location? 
            # If the location in CSV came out as "500032", it means we defaulted to search_location.
            # We want to grab the actual text from the card like "Remote" or "Hyderabad, Telangana".


            url = f"https://www.linkedin.com/jobs/view/{job_id}"
            
            # Database Save
            self.store.con.execute(
                 "INSERT OR REPLACE INTO extracted_jobs (id, job_id, url, title, company, location, date_extracted, candidate_id, is_easy_apply) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)",
                 [job_id, job_id, url, title, company, location, self.candidate_id, False]
             )
            self.store.con.commit()
             
            # CSV Save
            if self.csv_path:
                with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
                    writer.writerow([job_id, title, company, location, zipcode, url, time.strftime('%Y-%m-%d %H:%M:%S'), False])
                
            # MySQL Save
            self.mysql_store.insert_position({
                'title': title,
                'company': company,
                'location': location,
                'zipcode': zipcode,
                'url': url,
                'job_id': job_id
            })
            
            logger.info(f"Saved job: {title} at {company} ({location}) - Zipcode: {zipcode}", step="extract_job")
                
        except Exception as e:
             logger.debug(f"Failed to save job {job_id}: {e}")


