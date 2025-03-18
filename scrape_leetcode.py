import time
import random
import os
from dotenv import load_dotenv

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import openai

########################################
# 1) LOAD ENVIRONMENT VARIABLES
########################################
load_dotenv()

LEETCODE_USERNAME = os.getenv("LEETCODE_USERNAME")
LEETCODE_PASSWORD = os.getenv("LEETCODE_PASSWORD")
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise ValueError("OPENAI_API_KEY is missing! Add it to your .env file.")

openai.api_key = API_KEY


########################################
# 2) CHATGPT HELPER FUNCTIONS
########################################
def get_complexities_from_chatgpt(code_str, language="C++"):
    """
    Sends the code snippet to ChatGPT and asks for time and space complexity.
    Returns a dict with "time_complexity", "space_complexity", and an "explanation".
    """
    system_prompt = (
        "You are a senior software engineer who determines the time and space "
        "complexities for code snippets. Provide concise and accurate answers."
    )
    user_prompt = f"""
Given the following {language} code snippet, please:
1. State the time complexity in Big-O notation (like O(n)).
2. State the space complexity in Big-O notation (like O(1) or O(n)).
3. Provide a brief explanation.

Code snippet:

{code_str}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
        answer = response["choices"][0]["message"]["content"]
        return answer.strip()
    except Exception as e:
        print(f"[!] Error calling ChatGPT for complexities: {e}")
        return "Error or no response."


########################################
# 3) UTILITIES FOR HUMAN-LIKE TYPING & BROWSER INIT
########################################
def human_like_typing(element, text):
    """
    Simulates human typing by sending keys one by one, with short random delays.
    """
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))


def init_browser():
    """
    Initialize an undetected Chrome browser on Windows.
    Update the user_data_dir, profile-directory, and driver paths
    to match your local setup.
    """
    options = webdriver.ChromeOptions()

    # Example: Windows user profile path for Chrome
    user_data_dir = r"C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data"
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--profile-directory=Default")

    # Spoof Windows Chrome user-agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.6998.89 Safari/537.36"
    )

    # Disable some detection features
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    # Update the path to your actual ChromeDriver location
    chromedriver_path = r"C:\\Program Files\\ChromeDriver\\chromedriver-win64\\chromedriver.exe"

    # If you need a specific Chrome browser executable path (often optional)
    browser_path = None  # e.g. r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    browser = uc.Chrome(
        options=options,
        use_subprocess=True,
        driver_executable_path=chromedriver_path,
        browser_executable_path=browser_path,
    )

    # Patch to avoid detection
    browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return browser


########################################
# 4) LOGIN TO LEETCODE
########################################
def login_to_leetcode(browser):
    """
    Logs into LeetCode with your credentials from .env.
    Handles any CAPTCHAs manually by prompting the user.
    """
    print("[*] Navigating to LeetCode login page...")
    browser.get("https://leetcode.com/accounts/login/")

    # Prompt user to resolve CAPTCHA if any.
    input("\n[!] Solve any CAPTCHA in the opened browser, then press Enter here to continue...\n")

    try:
        username_input = browser.find_element(By.ID, "id_login")
        human_like_typing(username_input, LEETCODE_USERNAME)
        print("[+] Entered username.")
    except NoSuchElementException:
        print("[-] Username field not found.")
        return

    try:
        password_input = browser.find_element(By.ID, "id_password")
        human_like_typing(password_input, LEETCODE_PASSWORD)
        print("[+] Entered password.")
    except NoSuchElementException:
        print("[-] Password field not found.")
        return

    # Click the sign-in button
    try:
        login_button = browser.find_element(By.ID, "signin_btn")
        browser.execute_script("arguments[0].click();", login_button)
        print("[*] Clicked 'Sign In' button.")
    except NoSuchElementException:
        print("[-] Sign In button not found.")
        return

    time.sleep(3)
    if "login" in browser.current_url.lower():
        print("[-] Still on login page. Possibly a CAPTCHA or credential issue.")
    else:
        print("[+] Logged in successfully.")


########################################
# 5) HELPER TO CLICK THE C++ FILTER BUTTON
########################################
def click_cpp_filter(browser):
    """
    Clicks on the "C++" button in the solutions tab to filter only C++ solutions.
    """
    try:
        print("[*] Looking for the C++ filter button...")
        # Wait until the element is clickable
        cpp_button = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'C++')]"))
        )
        # Scroll into view and click
        browser.execute_script("arguments[0].scrollIntoView();", cpp_button)
        time.sleep(1)
        cpp_button.click()
        time.sleep(2)
        print("[+] Clicked the C++ filter button successfully.")
    except (TimeoutException, NoSuchElementException) as e:
        print(f"[!] C++ filter button not found or not clickable: {e}")


########################################
# 6) OPTIONALLY EXPAND ALL SOLUTIONS
########################################
def expand_all_solutions(browser):
    """
    If there's a button or link to expand solutions (like "Show more"),
    click them before scraping.
    """
    try:
        show_more_buttons = browser.find_elements(By.XPATH, "//button[contains(text(),'Show more')]")
        for btn in show_more_buttons:
            try:
                browser.execute_script("arguments[0].scrollIntoView();", btn)
                time.sleep(0.5)
                btn.click()
                time.sleep(1)
            except (ElementClickInterceptedException, NoSuchElementException):
                pass
    except Exception as e:
        print(f"[!] expand_all_solutions encountered an error: {e}")


########################################
# 7) EXTRACT SOLUTIONS (AFTER FILTERING)
########################################
def extract_solutions(browser):
    """
    Scrapes the solution code blocks from the Solutions tab, after applying filters.
    Returns a list of solution dicts with 'index', 'code', and 'chatgpt_analysis'.
    """
    print("[*] Waiting for solutions to load...")
    solution_data = []

    try:
        # Wait for a container that indicates solutions are loaded
        WebDriverWait(browser, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'solution')]"))
        )
    except TimeoutException:
        print("[!] Timed out waiting for solutions container. Possibly no solutions or changed HTML.")
        return solution_data

    print("[+] Potential solutions visible. Selecting C++ filter (if available).")
    click_cpp_filter(browser)

    # Wait briefly for the page to refresh after clicking the C++ filter
    time.sleep(2)

    print("[*] Expanding all solutions if needed...")
    expand_all_solutions(browser)

    # Now find individual solution blocks
    solutions_list = browser.find_elements(By.XPATH, "//div[contains(@class, 'solution')]")
    print(f"[+] Found {len(solutions_list)} solutions (post-filter). Extracting content...")

    for idx, solution_item in enumerate(solutions_list):
        try:
            # Scroll each solution into view
            browser.execute_script("arguments[0].scrollIntoView();", solution_item)
            time.sleep(1)

            # Usually, there's a <pre> or <code> element containing the solution code
            code_block = solution_item.find_element(By.XPATH, ".//pre")
            code_text = code_block.text.strip() if code_block else "No code found"

            # Ask ChatGPT for complexities (optional, can comment out if not needed)
            complexities_analysis = get_complexities_from_chatgpt(code_text, language="C++")

            solution_data.append({
                "index": idx + 1,
                "code": code_text,
                "chatgpt_analysis": complexities_analysis
            })

            print(f"[+] C++ Solution #{idx+1}: {code_text[:80]}...")
        except Exception as e:
            print(f"[!] Could not extract solution #{idx+1}: {e}")

    return solution_data


########################################
# 8) SCRAPE A SINGLE PROBLEM'S SOLUTIONS
########################################
def scrape_problem_solutions(browser, title, url):
    """
    Given a single problem's title/URL, navigate to the solutions tab, scrape solutions, and return them.
    """
    solutions_url = url.rstrip("/") + "/solutions/?tab=solutions"
    print(f"[*] Navigating to solutions page: {solutions_url}")

    browser.get(solutions_url)
    time.sleep(2)

    extracted_solutions = extract_solutions(browser)
    return {
        "problem_title": title,
        "problem_url": url,
        "solutions": extracted_solutions
    }


########################################
# 9) SCRAPE MULTIPLE PROBLEMS
########################################
def scrape_problems(browser, num_pages=1):
    """
    Collects problem links from the main problemset, then scrapes each problem's solutions.
    :param num_pages: How many "Next" pages to iterate through.
    """
    print("[*] Navigating to the 'All Problems' page...")
    browser.get("https://leetcode.com/problemset/all/")
    time.sleep(5)

    all_solutions_data = []

    for page_index in range(num_pages):
        # Gather problem links on this page
        problem_links = []
        problem_elements = browser.find_elements(By.XPATH, "//a[contains(@href, '/problems/')]")

        for elem in problem_elements:
            href = elem.get_attribute("href")
            p_title = elem.text.strip()
            if href and "problems" in href and p_title:
                # Basic filtering to avoid duplicates
                problem_links.append((p_title, href))

        # Remove potential duplicates by converting to a dict or set
        unique_problem_links = list(dict.fromkeys(problem_links))

        print(f"[*] Found {len(unique_problem_links)} problems on page {page_index+1}.")

        # Scrape each problem
        for (p_title, p_url) in unique_problem_links:
            print(f"  > [Problem] {p_title}: {p_url}")
            problem_solutions = scrape_problem_solutions(browser, p_title, p_url)
            all_solutions_data.append(problem_solutions)

        # Go to the next page if available
        try:
            next_btn = browser.find_element(By.XPATH, "//button[contains(text(), 'Next')]")
            next_btn.click()
            time.sleep(3)
            print(f"[*] Moved to page {page_index+2} of problems...")
        except NoSuchElementException:
            print("[*] No more 'Next' button found. Stopping problemset scrape.")
            break

    return all_solutions_data


########################################
# 10) MAIN ENTRY POINT
########################################
def main():
    """
    Main function: logs in, scrapes solutions, prints or processes the final data.
    """
    browser = init_browser()
    solutions_data = []

    try:
        # 1) Log in
        login_to_leetcode(browser)

        # 2) Scrape solutions from the first page of "All Problems" only (num_pages=1).
        #    Increase num_pages if you want to go deeper.
        solutions_data = scrape_problems(browser, num_pages=1)

    except Exception as e:
        print(f"[!] A major error occurred: {e}")

    finally:
        input("[!] Press Enter to close the browser...")
        browser.quit()

    # Print a summary of the scraped data
    print("\n\n[=== SCRAPING COMPLETE ===]")
    for item in solutions_data:
        print("=====================================================")
        print(f"Problem: {item['problem_title']}")
        print(f"Link: {item['problem_url']}")
        print(f"Number of solutions: {len(item['solutions'])}")
        for sol in item["solutions"]:
            print(f"  - C++ Solution #{sol['index']}:")
            print(f"    Code (truncated): {sol['code'][:100]}...")
            print(f"    ChatGPT Analysis: {sol['chatgpt_analysis'][:100]}...")
        print("=====================================================")


if __name__ == "__main__":
    main()
