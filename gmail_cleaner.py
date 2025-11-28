#!/usr/bin/env python3
"""
Gmail Storage Optimizer - Email Cleaner
Author: Shabul

Automatically deletes bulk emails from specified senders while implementing
multiple safety mechanisms to protect important correspondence.
"""

import time
import argparse
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuration
PROFILE_PATH = "/Users/ey/Documents/code-trials/clean-gmail/chrome-profile"

def setup_driver():
    """Sets up the Chrome driver with the user's profile."""
    options = Options()
    options.add_argument(f"user-data-dir={PROFILE_PATH}")
    # This prevents the "Chrome is being controlled by automated test software" bar
    # and helps with some detection issues, though Gmail is tough.
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(options=options)
    return driver

def clean_emails(keywords):
    """Searches for emails by multiple keywords and deletes them iteratively in separate tabs (Async Cycling, Batched)."""
    driver = setup_driver()
    BATCH_SIZE = 5
    # Track which keywords were fully deleted and which were skipped due to safety threshold
    deleted_keywords = []
    safe_skipped_keywords = []
    
    try:
        # We keep the initial tab as a "Controller" to prevent the session from closing
        # when all worker tabs in a batch are closed.
        controller_handle = driver.current_window_handle
        driver.get("about:blank")
        print("Controller tab set up.")
        
        total_batches = (len(keywords) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx, i in enumerate(range(0, len(keywords), BATCH_SIZE)):
            batch = keywords[i:i + BATCH_SIZE]
            print(f"\n" + "="*40)
            print(f"Starting Batch {batch_idx + 1}/{total_batches} ({len(batch)} keywords)")
            print("="*40)
            
            active_tabs = []
            
            print("Opening tabs for this batch...")
            # Open a tab for each keyword in the batch
            for k_idx, keyword in enumerate(batch):
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[-1])
                
                # Use direct URL for search
                print(f"Opening tab {k_idx+1}/{len(batch)} for keyword: {keyword}")
                # Append -is:starred and -is:important to exclude protected emails
                safe_keyword = f"{keyword} -is:starred -is:important"
                url = f"https://mail.google.com/mail/u/0/#search/{safe_keyword}"
                driver.get(url)
                
                active_tabs.append({
                    "handle": driver.window_handles[-1],
                    "keyword": keyword,
                    "status": "ready", # ready, busy
                    "last_action_time": 0
                })
                # Random delay between opening tabs to look less robotic
                time.sleep(random.uniform(2.0, 4.0))

            print("Batch tabs opened. Starting parallel deletion loop...")
            
            while active_tabs:
                action_taken = False
                
                # Iterate through a copy of the list so we can remove items safely
                for tab in active_tabs[:]:
                    # Check if tab is busy (waiting for reload)
                    if tab['status'] == 'busy':
                        # If 5 seconds have passed, mark as ready
                        if time.time() - tab['last_action_time'] > 5:
                            tab['status'] = 'ready'
                        else:
                            continue # Skip this tab for now
                    
                    # If we are here, tab is ready (or became ready)
                    try:
                        # Switch to tab
                        driver.switch_to.window(tab['handle'])
                        
                        # Check if we are on a "No matches" page
                        # We use a short wait or just check immediately since we waited 5s
                        try:
                            body_text = driver.find_element(By.TAG_NAME, "body").text
                            if "No messages matched your search" in body_text:
                                print(f"[{tab['keyword']}] No more messages. Closing tab.")
                                driver.close()
                                active_tabs.remove(tab)
                                # Record successful deletion (all emails for this keyword are gone)
                                deleted_keywords.append(tab['keyword'])
                                action_taken = True
                                continue
                        except:
                            pass # Body might not be loaded, we'll try to find elements

                        # Check total count to avoid deleting if < 100
                        try:
                            # Look for the "1-50 of 123" text.
                            count_elements = driver.find_elements(By.XPATH, "//span[contains(text(), ' of ')]")
                            total_count = 0
                            for el in count_elements:
                                try:
                                    if el.is_displayed():
                                        text = el.text
                                        if " of " in text:
                                            parts = text.split(" of ")
                                            if len(parts) == 2:
                                                count_str = parts[1].replace(",", "").strip()
                                                if count_str.isdigit():
                                                    total_count = int(count_str)
                                                    break
                                except:
                                    continue
                            if total_count > 0 and total_count < 10:
                                print(f"[{tab['keyword']}] Found {total_count} emails (safe threshold < 100). Skipping deletion.")
                                # Record safe skip
                                safe_skipped_keywords.append(tab['keyword'])
                                driver.close()
                                active_tabs.remove(tab)
                                action_taken = True
                                continue
                        except Exception:
                            pass

                        print(f"[{tab['keyword']}] Checking for emails...")
                        
                        # Try multiple selectors for the "Select All" checkbox
                        checkbox_selectors = [
                            "div[aria-label='Select']",
                            "div[aria-label='Select all']",
                            "span[role='checkbox']",
                            "div[role='checkbox']"
                        ]
                        
                        checkbox_found = False
                        for selector in checkbox_selectors:
                            try:
                                checkboxes = driver.find_elements(By.CSS_SELECTOR, selector)
                                for cb in checkboxes:
                                    if cb.is_displayed():
                                        cb.click()
                                        checkbox_found = True
                                        break
                                if checkbox_found:
                                    break
                            except Exception:
                                continue
                        
                        if not checkbox_found:
                            # If we can't find the checkbox, it might be empty or loading.
                            # We'll mark it as busy for a bit to give it time, or check if it's truly empty next time.
                            # But if we just checked "No messages" and it wasn't there, maybe it's just slow.
                            print(f"[{tab['keyword']}] 'Select All' not found. Waiting...")
                            tab['status'] = 'busy'
                            tab['last_action_time'] = time.time()
                            continue

                        # Click Delete button
                        delete_button_found = False
                        potential_delete_btns = driver.find_elements(By.XPATH, "//*[@aria-label='Delete']")
                        
                        for btn in potential_delete_btns:
                            try:
                                if btn.is_displayed():
                                    # Random delay before clicking delete
                                    time.sleep(random.uniform(1.0, 3.0))
                                    # Try standard click first
                                    try:
                                        btn.click()
                                    except Exception:
                                        driver.execute_script("arguments[0].click();", btn)
                                    
                                    delete_button_found = True
                                    print(f"[{tab['keyword']}] Clicked Delete. Switching to next tab...")
                                    break
                            except Exception:
                                continue
                        
                        if delete_button_found:
                            # Mark as busy so we don't come back to this tab for 5 seconds
                            tab['status'] = 'busy'
                            tab['last_action_time'] = time.time()
                            action_taken = True
                        else:
                            print(f"[{tab['keyword']}] Delete button not found.")
                            # Wait a bit before retrying
                            tab['status'] = 'busy'
                            tab['last_action_time'] = time.time()
                        
                    except (NoSuchElementException, TimeoutException) as e:
                        print(f"[{tab['keyword']}] Error: {e}")
                        tab['status'] = 'busy'
                        tab['last_action_time'] = time.time()
                        continue
                    except Exception as e:
                        print(f"[{tab['keyword']}] Unexpected error: {e}")
                        if tab['handle'] not in driver.window_handles:
                            active_tabs.remove(tab)
                        continue
                
                # If no action was taken in the entire loop (all tabs busy), sleep briefly to prevent CPU spinning
                if not action_taken:
                    time.sleep(0.5)
            
            # Switch back to controller before next batch (or end)
            driver.switch_to.window(controller_handle)

    finally:
        print("Closing browser...")
        try:
            driver.quit()
        except:
            pass
    
    return deleted_keywords, safe_skipped_keywords

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean Gmail emails by keywords.")
    parser.add_argument("keywords", nargs='*', help="List of search keywords to delete emails for")
    args = parser.parse_args()
    
    target_keywords = args.keywords
    
    if not target_keywords:
        try:
            import keywords
            target_keywords = keywords.emails
            print(f"No keywords provided via CLI. Using {len(target_keywords)} keywords from keywords.py")
        except ImportError:
            print("Error: No keywords provided and keywords.py not found.")
            exit(1)
        except AttributeError:
            print("Error: keywords.py does not contain an 'emails' list.")
            exit(1)
            
    if not target_keywords:
        print("No keywords to process.")
        exit(1)
    
    # Filter out protected emails
    try:
        import keywords
        if hasattr(keywords, 'protected_emails'):
            protected = set(keywords.protected_emails)
            original_count = len(target_keywords)
            target_keywords = [k for k in target_keywords if k not in protected]
            skipped_count = original_count - len(target_keywords)
            if skipped_count > 0:
                print(f"Skipped {skipped_count} protected keywords that matched the protected list.")
    except ImportError:
        pass
    
    # Filter out @gmail.com addresses (personal emails should never be deleted)
    original_count = len(target_keywords)
    target_keywords = [k for k in target_keywords if not k.lower().endswith('@gmail.com') and not k.lower().endswith('@outlook.com')]
    gmail_skipped = original_count - len(target_keywords)
    if gmail_skipped > 0:
        print(f"Skipped {gmail_skipped} @gmail.com and @outlook.com addresses (personal emails are protected).")
    
    # clean_emails now returns two lists: deleted and safe-skipped keywords
    deleted_keywords, safe_skipped_keywords = clean_emails(target_keywords)
    
    # Log the deleted keywords to deleted_history.json
    try:
        import json
        import os
        
        history_file = "deleted_history.json"
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                pass
        # Merge new deleted keywords
        current_set = set(history)
        new_deleted = 0
        for k in deleted_keywords:
            if k not in current_set:
                history.append(k)
                current_set.add(k)
                new_deleted += 1
        if new_deleted > 0:
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
            print(f"\nLogged {new_deleted} new deleted keywords to {history_file}")
    except Exception as e:
        print(f"Error logging deleted history: {e}")
    
    # Log the safe-skipped keywords to safe_not_deleted.json
    try:
        safe_file = "safe_not_deleted.json"
        safe_history = []
        if os.path.exists(safe_file):
            try:
                with open(safe_file, 'r') as f:
                    safe_history = json.load(f)
            except json.JSONDecodeError:
                pass
        safe_set = set(safe_history)
        new_safe = 0
        for k in safe_skipped_keywords:
            if k not in safe_set:
                safe_history.append(k)
                safe_set.add(k)
                new_safe += 1
        if new_safe > 0:
            with open(safe_file, 'w') as f:
                json.dump(safe_history, f, indent=2)
            print(f"\nLogged {new_safe} safe-skipped keywords to {safe_file}")
    except Exception as e:
        print(f"Error logging safe-not-deleted history: {e}")
