import time
import random
import os
from dotenv import load_dotenv

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


import openai
load_dotenv()

# 1) Configure your credentials and paths
LEETCODE_USERNAME = os.getenv("LEETCODE_USERNAME")
LEETCODE_PASSWORD = os.getenv("LEETCODE_PASSWORD")
API_KEY = os.getenv("OPENAI_API_KEY")  # Securely get key from env variable

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY is missing! Add it to your .env file.")


# 2) Define a ChatGPT helper to get complexities
def get_complexities_from_chatgpt(code_str, language="C++"):
    """
    Sends the code snippet to ChatGPT and asks for time and space complexity.
    Returns a dict with time_complexity and space_complexity.
    """
    # You can refine the system/instructions prompts to get more consistent results
    system_prompt = (
        "You are a senior software engineer who determines the time and space complexity for code snippets. "
        "Please be concise and accurate."
    )
    
    user_prompt = f"""
Given the following {language} code snippet, please:
1. State the time complexity in Big-O notation.
2. State the space complexity in Big-O notation.
3. Provide a short explanation.

Code snippet:

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
        content = response["choices"][0]["message"]["content"]
        # You could parse the content if needed; for now, just return the whole text
        return content
    except Exception as e:
        print(f"Error with ChatGPT API: {e}")
        return "Error or no response."

# 3) (Optional) Convert code to C++ with ChatGPT if original solution is not in C++
def convert_to_cpp_with_chatgpt(code_str, original_lang="Python"):
    """
    If the code is in Python (or any other language), ask ChatGPT to convert it to C++.
    """
    system_prompt = (
        "You are a senior software engineer who converts code to C++."
    )
    user_prompt = f"""
Convert the following {original_lang} code snippet to equivalent C++ code:

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
        cpp_code = response["choices"][0]["message"]["content"]
        return cpp_code
    except Exception as e:
        print(f"Error converting to C++: {e}")
        return None


def human_like_typing(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3)) 

# 4) Initialize Selenium (undetected ChromeDriver)
def init_browser():
    options = webdriver.ChromeOptions()

    # ✅ Use real browser profile
    options.add_argument("--user-data-dir=/Users/omnisceo/Library/Application Support/Google/Chrome")
    options.add_argument("--profile-directory=Default")  # Change if needed

    # ✅ Spoof User-Agent
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.89 Safari/537.36")

    # ✅ Disable bot detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    # ✅ Initialize Undetected ChromeDriver
    browser = uc.Chrome(
        options=options, 
        use_subprocess=True,
        browser_executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        driver_executable_path="/opt/homebrew/bin/chromedriver"  # Ensure correct path
    )

    # ✅ Patch ChromeDriver (Avoid Detection)
    browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return browser



# 5) Login to LeetCode
def login_to_leetcode(browser):
    print("[*] Navigating to LeetCode login page...")
    browser.get("https://leetcode.com/accounts/login/")
    
    # Wait for user to solve CAPTCHA manually
    input("\n[!] Solve any CAPTCHA in the browser and then press Enter here...\n")

    try:
        username_input = browser.find_element(By.ID, "id_login")
        human_like_typing(username_input, LEETCODE_USERNAME)
        print("[+] Entered username.")
    except NoSuchElementException:
        print("[-] Could not locate the username field.")
        return

    try:
        password_input = browser.find_element(By.ID, "id_password")
        human_like_typing(password_input, LEETCODE_PASSWORD)
        print("[+] Entered password.")
    except NoSuchElementException:
        print("[-] Could not locate the password field.")
        return

    # Click login
    try:
        login_button = browser.find_element(By.ID, "signin_btn")
        browser.execute_script("arguments[0].click();", login_button)
        print("[*] Clicked 'Sign In' button.")
    except NoSuchElementException:
        print("[-] Could not find the sign in button.")
        return

    # Check if login succeeded
    time.sleep(3)
    current_url = browser.current_url
    if "login" in current_url.lower():
        print("[-] Still on login page. CAPTCHA or credentials issue.")
    else:
        print("[+] Logged in successfully.")


def click_editorial_post(browser):
    """
    This function tries to find the 'LeetCode Editorial' post on the Solutions page
    and clicks it to open the official editorial (like 'two-sum-by-leetcode-kwuq').
    """   
    print("[*] Attempting to click on the LeetCode Editorial post...")

    time.sleep(3)  # let solutions list load

    try:
        # Step A: find the editorial post container
        editorial_post = browser.find_element(
            By.XPATH,
            "//div[contains(@class, 'group flex w-full cursor-pointer flex-col gap-1.5 px-4 pt-3')"
            + " and .//span[text()='Editorial']]"
        )
        # Step B: find the link inside that container
        editorial_link = editorial_post.find_element(
            By.XPATH,
            ".//a[contains(@href, '/problems/') and contains(@href, '/solutions/') and contains(@href, 'two-sum-by-leetcode-kwuq')]"
        )

        # Finally, click the editorial link
        editorial_link.click()
        time.sleep(2)
        print("[+] Clicked on the official LeetCode editorial post.")
    except NoSuchElementException:
        print("[!] Could not find the editorial post or link.")



def extract_solutions(browser):
    """
    Extracts all solutions by clicking on them and scraping the content.
    """
    try:
        print("[*] Waiting for solutions to load...")

        # ✅ FIX: Wait for solutions to appear
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'relative') and contains(@class, 'solution')]"))
        )
        
        print("[+] Solutions are visible.")
        solutions_list = browser.find_elements(By.XPATH, "//div[contains(@class, 'relative') and contains(@class, 'solution')]")

        if not solutions_list:
            print("[!] No solutions found.")
            return []

        print(f"[+] Found {len(solutions_list)} solutions. Clicking each one...")

        solution_data = []

        for index, solution in enumerate(solutions_list):
            try:
                # ✅ Scroll to the solution (in case of lazy loading)
                browser.execute_script("arguments[0].scrollIntoView();", solution)
                time.sleep(1)

                # ✅ Click the solution to expand
                ActionChains(browser).move_to_element(solution).click().perform()
                time.sleep(2)

                # ✅ Extract the solution code
                code_block = solution.find_element(By.XPATH, ".//pre")  # Adjust if necessary

                solution_text = code_block.text.strip() if code_block else "No solution text found."
                print(f"[+] Extracted solution {index + 1}:\n{solution_text[:200]}...")

                solution_data.append(solution_text)

            except Exception as e:
                print(f"[!] Failed to extract solution {index + 1}: {e}")

        return solution_data

    except Exception as e:
        print(f"[!] Error extracting solutions: {e}")
        return []


# 6) Scrape problems + solutions
def scrape_problems(browser, num_pages=1):
    print("[*] Navigating to Problems page...")
    browser.get("https://leetcode.com/problemset/all/")
    time.sleep(5)

    solutions_data = []  # Store extracted data

    for page in range(num_pages):
        problem_elements = browser.find_elements(By.XPATH, "//a[contains(@href, '/problems/')]")
        if not problem_elements:
            print("[-] No problems found on this page. Possibly the selector changed.")
            break

        problem_links = []
        for elem in problem_elements:
            url = elem.get_attribute("href")
            title = elem.text.strip()
            if url and title:
                problem_links.append((title, url))

        for (problem_title, problem_url) in problem_links:
            print(f"[+] Found problem: {problem_title} | URL: {problem_url}")

            # ✅ FIX: Use the correct solutions page URL
            solutions_url = problem_url + "/solutions/?tab=solutions"
            print(f"[*] Navigating directly to: {solutions_url}")
            browser.get(solutions_url)

            # ✅ Extract all solutions for this problem
            extracted_solutions = extract_solutions(browser)

            # ✅ Store extracted solutions
            solutions_data.append({
                "problem_title": problem_title,
                "problem_url": problem_url,
                "solutions": extracted_solutions
            })

        # ✅ Click "Next" to load more problems
        try:
            next_btn = browser.find_element(By.XPATH, "//button[contains(text(), 'Next')]")
            next_btn.click()
            time.sleep(5)
        except NoSuchElementException:
            print("[*] No more pages or 'Next' button not found.")
            break

    return solutions_data


# 7) Scroll the page to load more solutions (if applicable)
def scroll_page(browser):
    """
    Scrolls down the solutions page to load all solutions dynamically.
    """
    body = browser.find_element(By.TAG_NAME, "body")
    
    for _ in range(5):  # Scroll down 5 times
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(1)  # Give time for loading new elements

    print("[*] Scrolled through the solutions page.")



# 8) Main function to orchestrate the scraping
def main():
    data = []
    browser = init_browser()
    try:
        login_to_leetcode(browser)
        # For demonstration, let's only scrape 1 page to avoid heavy load
        data = scrape_problems(browser, num_pages=1)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        input("Press Enter to close browser...")
        browser.quit()

    # Print or store the results
    print("[*] Scraping done. Solutions data:")
    for item in data:
        print("========================================")
        print(f"Problem: {item['problem_title']}")
        print(f"Link: {item['problem_url']}")
        print(f"Regex time complexity: {item['time_complexity_regex']}")
        print(f"Regex space complexity: {item['space_complexity_regex']}")
        print(f"Original snippet (truncated): {item['original_snippet'][:100]} ...")
        print("Converted to C++ (truncated):")
        print(item['converted_cxx_snippet'][:200], "...")
        print("Complexities (raw ChatGPT response):")
        print(item['complexities_chatgpt'])
        print("========================================")

if __name__ == "__main__":
    main()
