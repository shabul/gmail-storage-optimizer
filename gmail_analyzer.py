#!/usr/bin/env python3
"""
Gmail Storage Optimizer - Email Analyzer
Author: Shabul

Scans Gmail inbox to identify high-volume senders and suggests
email addresses for bulk deletion.
"""

import time
import argparse
from collections import Counter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Configuration
PROFILE_PATH = "/Users/ey/Documents/code-trials/clean-gmail/chrome-profile"

def setup_driver():
    """Sets up the Chrome driver with the user's profile."""
    options = Options()
    options.add_argument(f"user-data-dir={PROFILE_PATH}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(options=options)
    return driver

def analyze_emails(max_pages=500):
    """Scans Gmail inbox to find top senders."""
    driver = setup_driver()
    sender_counter = Counter()
    
    try:
        print("Opening Gmail (All Mail)...")
        # Navigate to "All Mail" to get a better view
        driver.get("https://mail.google.com/mail/u/0/#all")
        
        # Wait for list to load
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
            )
        except TimeoutException:
            print("Error: content did not load.")
            return

        print(f"Scanning up to {max_pages} pages (Greedy Mode)...")
        
        for page in range(1, max_pages + 1):
            print(f"Processing page {page}/{max_pages}...")
            
            # Wait for rows to be visible
            time.sleep(2) 
            
            # Find all email rows
            # Class 'zA' is the standard class for email rows in the list
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.zA")
            
            page_senders = []
            for row in rows:
                try:
                    # The sender's email is often in a span with the 'email' attribute
                    # This is the most reliable way to get the actual address
                    email_element = row.find_element(By.CSS_SELECTOR, "span[email]")
                    email = email_element.get_attribute("email")
                    if email:
                        page_senders.append(email)
                    else:
                        # Fallback to text if email attr is missing (rare)
                        page_senders.append(email_element.text)
                except (NoSuchElementException, StaleElementReferenceException):
                    # Sometimes it's just a name span without email attr
                    # Or the element became stale (DOM updated)
                    try:
                        # 'yP' is often the class for the sender name
                        name_element = row.find_element(By.CSS_SELECTOR, ".yP")
                        page_senders.append(name_element.text)
                    except Exception:
                        continue
                except Exception:
                    # Catch-all to prevent crash on single row failure
                    continue
            
            sender_counter.update(page_senders)
            print(f"  Found {len(page_senders)} emails on this page. Total unique senders: {len(sender_counter)}")
            
            # Go to next page
            try:
                # "Older" button (Next page)
                # Gmail often has two: top and bottom. We need the visible one.
                older_btns = driver.find_elements(By.CSS_SELECTOR, "div[aria-label='Older']")
                
                clicked = False
                for btn in older_btns:
                    try:
                        if btn.is_displayed() and btn.get_attribute("aria-disabled") != "true":
                            # Scroll into view
                            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                            time.sleep(1)
                            
                            try:
                                btn.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", btn)
                            
                            clicked = True
                            break
                    except:
                        continue
                
                if not clicked:
                    # Check if we are at the end (all disabled)
                    all_disabled = all(btn.get_attribute("aria-disabled") == "true" for btn in older_btns)
                    if all_disabled and older_btns:
                        print("Reached the last page.")
                        break
                    elif not older_btns:
                        print("Could not find 'Older' button. Stopping.")
                        break
                    else:
                        print("Found 'Older' buttons but none were clickable. Trying JS on the last one...")
                        driver.execute_script("arguments[0].click();", older_btns[-1])
                
            except Exception as e:
                print(f"Error navigating: {e}")
                break

    finally:
        print("\nClosing browser...")
        try:
            driver.quit()
        except:
            pass
        
        print("\n" + "="*40)
        print("SENDERS WITH 10+ EMAILS")
        print("="*40)
        
        # Filter out protected emails from keywords.py
        try:
            import keywords
            if hasattr(keywords, 'protected_emails'):
                protected = set(keywords.protected_emails)
                for p_email in protected:
                    if p_email in sender_counter:
                        del sender_counter[p_email]
        except ImportError:
            pass
        
        # Filter out emails from deleted_history.json
        try:
            import json
            import os
            
            deleted_file = "deleted_history.json"
            if os.path.exists(deleted_file):
                with open(deleted_file, 'r') as f:
                    deleted_history = json.load(f)
                    deleted_set = set(deleted_history)
                    for email in deleted_set:
                        if email in sender_counter:
                            del sender_counter[email]
                    print(f"Filtered out {len(deleted_set)} emails from deleted_history.json")
        except Exception as e:
            print(f"Warning: Could not load deleted_history.json: {e}")
        
        # Filter out emails from safe_not_deleted.json
        try:
            safe_file = "safe_not_deleted.json"
            if os.path.exists(safe_file):
                with open(safe_file, 'r') as f:
                    safe_history = json.load(f)
                    safe_set = set(safe_history)
                    for email in safe_set:
                        if email in sender_counter:
                            del sender_counter[email]
                    print(f"Filtered out {len(safe_set)} emails from safe_not_deleted.json")
        except Exception as e:
            print(f"Warning: Could not load safe_not_deleted.json: {e}")
        
        # Filter out @gmail.com addresses (personal emails should never be suggested for deletion)
        gmail_count = 0
        for sender in list(sender_counter.keys()):
            if sender.lower().endswith('@gmail.com') or sender.lower().endswith('@outlook.com'):
                del sender_counter[sender]
                gmail_count += 1
        if gmail_count > 0:
            print(f"Filtered out {gmail_count} @gmail.com/@outlook.com addresses (personal emails are protected)")

        # Get all senders with >= 10 emails
        significant_senders = [(s, c) for s, c in sender_counter.most_common() if c >= 10]
        
        if not significant_senders:
            print("No senders found with 10+ emails (after filtering).")
        else:
            # Print as a Python list for easy copying
            print("\nCopy this list to your keywords.py:")
            print("-" * 20)
            print("emails = [")
            for sender, count in significant_senders:
                print(f'    "{sender}", # Count: {count}')
            print("]")
            print("-" * 20)
        print("="*40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Gmail top senders.")
    parser.add_argument("--pages", type=int, default=500, help="Number of pages to scan (default: 500)")
    args = parser.parse_args()
    
    analyze_emails(args.pages)
