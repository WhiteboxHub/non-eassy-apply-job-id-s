from selenium.webdriver.common.by import By

# Enhanced selector registry with fallback support
# Each selector can have a primary and optional fallback locator

LOCATORS = {
    "search": {
        "primary": (By.CLASS_NAME, "jobs-search-results-list"),
        "fallback": (By.XPATH, "//div[contains(@class, 'jobs-search-results-list')]")
    },
    
    "links": {
        "primary": (By.XPATH, "//div[contains(@class, 'job-card-container') or @data-job-id or contains(@class, 'base-card')]"),
        "fallback": (By.CSS_SELECTOR, ".job-card-list__entity-lockup, .base-search-card, .base-card")
    },
    
    "company": {
        "primary": (By.CSS_SELECTOR, ".job-card-container__primary-description, .job-card-list__entity-lockup_subtitle, .artdeco-entity-lockup__subtitle"),
        "fallback": (By.CSS_SELECTOR, ".job-card-container__company-name, .job-card-list__company-name, [class*='company-name']")
    },
    
    "location": {
        "primary": (By.CSS_SELECTOR, ".job-card-container__metadata-item, .job-card-container__metadata-wrapper, .artdeco-entity-lockup__caption"),
        "fallback": (By.CSS_SELECTOR, ".job-card-container__location, .job-card-list__metadata-item")
    },
    
    "external_apply_button": {
        "primary": (By.XPATH, "//a[contains(@href, 'redir/redirect')] | //a[contains(@aria-label, 'Apply on company website')] | //a[.//span[contains(text(), 'Apply')]]"),
        "fallback": (By.XPATH, "//button[contains(@aria-label, 'Apply') and not(contains(@aria-label, 'filter'))] | //a[contains(@aria-label, 'Apply') and not(contains(@aria-label, 'filter'))] | //button[.//span[text()='Apply']] | //a[.//span[text()='Apply']] | //button[@id='jobs-apply-button-id'] | //span[text()='Apply']/parent::a")
    },

    "all_filters_button": {
        "primary": (By.XPATH, "//button[contains(@class, 'search-reusables__all-filters-pill-button')]"),
        "fallback": (By.XPATH, "//button[contains(@aria-label, 'All filters') or contains(text(), 'All filters')]")
    },

    "title_filter_labels": {
        # Scoped to the Title section container only — tries fieldset, section, li containers with 'Title' or 'Job title' headings
        "primary": (By.XPATH,
            "//fieldset[.//legend[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'title')]]//label"
            " | //fieldset[.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'title')]]//label"
            " | //section[.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'title')]]//label"
            " | //li[.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'title')]]//label"
        ),
        "fallback": (By.XPATH, "//div[contains(@class, 'artdeco-modal')]//label")
    },

    "title_filter_show_more": {
        "primary": (By.XPATH, "//fieldset[.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'title')]]//button[contains(@aria-label, 'Show more')]"),
        "fallback": (By.XPATH, "//button[contains(., 'Show more') and contains(@aria-label, 'Title')]")
    },

    "job_type_filter_labels": {
        "primary": (By.XPATH,
            "//fieldset[.//legend[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'job type')]]//label"
            " | //fieldset[.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'job type')]]//label"
            " | //section[.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'job type')]]//label"
            " | //li[.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'job type')]]//label"
        ),
        "fallback": (By.XPATH, "//div[contains(@class, 'artdeco-modal')]//label")
    },

    "job_type_filter_show_more": {
        "primary": (By.XPATH, "//fieldset[.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'job type')]]//button[contains(@aria-label, 'Show more')]"),
        "fallback": (By.XPATH, "//button[contains(., 'Show more') and contains(@aria-label, 'Job type')]")
    },

    "all_filters_show_results": {
        "primary": (By.XPATH, "//button[contains(@aria-label, 'Apply current filters') or contains(@data-control-name, 'all_filters_apply')]"),
        "fallback": (By.XPATH, "//span[contains(text(), 'Show') and contains(text(), 'results')]/ancestor::button")
    },

    "reset_filters": {
        "primary": (By.XPATH, "//button[contains(@aria-label, 'Reset current filters')]"),
        "fallback": (By.XPATH, "//button[contains(., 'Reset') or contains(., 'Clear all')]")
    },

    "modal_dismiss": {
        "primary": (By.XPATH, "//button[contains(@class, 'artdeco-modal__dismiss')]"),
        "fallback": (By.XPATH, "//button[contains(@aria-label, 'Dismiss')]")
    },

    "pagination_next": {
        "primary": (By.XPATH, "//button[contains(@class, 'pagination__button--next')]"),
        "fallback": (By.XPATH, "//button[@aria-label='Next' or contains(@aria-label, 'next page')] | //button[.//span[text()='Next']]")
    },

    "login_username": {
        "primary": (By.ID, "username"),
        "fallback": (By.NAME, "session_key")
    },

    "login_password": {
        "primary": (By.ID, "password"),
        "fallback": (By.NAME, "session_password")
    },

    "login_submit": {
        "primary": (By.CSS_SELECTOR, "button[type='submit']"),
        "fallback": (By.XPATH, "//button[contains(text(), 'Sign in')]")
    },

    "login_error_password": {
        "primary": (By.ID, "error-for-password"),
        "fallback": (By.CSS_SELECTOR, "[id*='error-for-password']")
    },

    "login_error_username": {
        "primary": (By.ID, "error-for-username"),
        "fallback": (By.CSS_SELECTOR, "[id*='error-for-username']")
    },

    "login_alert": {
        "primary": (By.CLASS_NAME, "alert-content"),
        "fallback": (By.CSS_SELECTOR, ".alert-content")
    },

    "job_card_anchors": {
        "primary": (By.TAG_NAME, "a"),
        "fallback": (By.CSS_SELECTOR, "a")
    },

    "job_details_panes": [
        (By.CLASS_NAME, "jobs-search-results-details__container"),
        (By.CSS_SELECTOR, ".jobs-details"),
        (By.CSS_SELECTOR, "[role='main']"),
        (By.CLASS_NAME, "jobs-details__main-content")
    ],

    "job_search_list_container": {
        "primary": (By.CSS_SELECTOR, ".jobs-search-results-list"),
        "fallback": (By.CSS_SELECTOR, ".scaffold-layout__list-container, .jobs-search__results-list, .jobs-search__results-list")
    },
    
    "guest_job_type_pill": {
        "primary": (By.XPATH, "//button[contains(@aria-label, 'Job type filter')]"),
        "fallback": (By.CSS_SELECTOR, "button[aria-label*='Job type filter']")
    },
    
    "guest_experience_pill": {
        "primary": (By.XPATH, "//button[contains(@aria-label, 'Experience level filter')]"),
        "fallback": (By.CSS_SELECTOR, "button[aria-label*='Experience level filter']")
    },
    
    "guest_modal_dismiss": {
        "primary": (By.XPATH, "//button[contains(@class, 'modal__dismiss') or contains(@aria-label, 'Dismiss') or contains(@class, 'artdeco-modal__dismiss')]"),
        "fallback": (By.CSS_SELECTOR, "button.modal__dismiss, button[aria-label='Dismiss'], .artdeco-modal__dismiss")
    },
    
    "safety_reminder_continue": {
        "primary": (By.XPATH, "//button[.//span[contains(text(), 'Continue applying')]]"),
        "fallback": (By.XPATH, "//button[contains(@aria-label, 'Continue applying') or contains(., 'Continue applying')]")
    }
}
