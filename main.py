from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import configparser
import os
from datetime import datetime, timedelta
import pytz
import argparse


class CourtBooker:
    def __init__(self, user_prefix, headless=False, suppress_console=False, take_screenshots=False, use_config_date=False):
        """
        Initialize court booking system for a specific user.

        Args:
            user_prefix (str): User identifier prefix from config (e.g., 'USER1')
            headless (bool): Run browser without GUI
            suppress_console (bool): Minimize console output
            take_screenshots (bool): Enable screenshot capture
            use_config_date (bool): Use config date instead of calculated date
        """
        self.user_prefix = user_prefix
        self.headless = headless
        self.suppress_console = suppress_console
        self.take_screenshots = take_screenshots
        self.use_config_date = use_config_date
        self.logger = self._setup_logging(suppress_console)
        self.config = self._load_config()
        self.logged_in = False
        self.screenshots_dir = f"screenshots/{self.user_prefix}"
        self.driver = self._init_browser(headless, suppress_console)
        self.wait = WebDriverWait(self.driver, 10)

    def _setup_logging(self, suppress_console):
        """Set up logging configuration."""
        logger = logging.getLogger(self.user_prefix)
        logger.setLevel(logging.DEBUG)

        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')

        # Create a file handler
        file_handler = logging.FileHandler(f'logs/{self.user_prefix}.log')
        file_handler.setLevel(logging.DEBUG)

        # Create a console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if not suppress_console else logging.ERROR)

        # Create a formatter and set it for both handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add the handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def _load_config(self):
        """Load configuration for a specific user from the config file."""
        config = configparser.ConfigParser()
        if not config.read('config.ini'):
            self.logger.error("config.ini file not found")
            raise FileNotFoundError("config.ini file not found")

        # Verify user sections exist
        login_section = f"{self.user_prefix}_LOGIN"
        booking_section = f"{self.user_prefix}_BOOKING"

        if not config.has_section(login_section):
            self.logger.error(f"Missing login section for user {self.user_prefix}")
            raise ValueError(f"Missing login section for user {self.user_prefix}")
        if not config.has_section(booking_section):
            self.logger.error(f"Missing booking section for user {self.user_prefix}")
            raise ValueError(f"Missing booking section for user {self.user_prefix}")

        return {
            'login': dict(config[login_section]),
            'booking': self._process_booking_config(config[booking_section])
        }

    def _process_booking_config(self, booking_section):
        """Process booking configuration with date validation."""
        booking_config = dict(booking_section)

        if not self.use_config_date:
            tz = pytz.timezone('America/St_Johns')
            booking_date = datetime.now(tz) + timedelta(days=6)
            booking_config['date'] = booking_date.strftime("%Y-%m-%d")

        return booking_config

    def _init_browser(self, headless, suppress_console):
        """Initialize Chrome browser instance."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")

        if suppress_console:
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
            os.environ['WDM_LOG_LEVEL'] = '0'

        # Let Selenium automatically find ChromeDriver in PATH
        return webdriver.Chrome(options=chrome_options)

    def _take_screenshot(self, name):
        """Take a screenshot and save it to the screenshots directory."""
        if not self.take_screenshots:
            return
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(self.screenshots_dir, f"{name}_{timestamp}.png")
        self.driver.save_screenshot(screenshot_path)
        self.logger.info(f"Screenshot saved: {screenshot_path}")

    def execute_booking(self):
        """Main execution flow for the booking process."""
        try:
            if not self._login():
                return False
            if not self._navigate_to_booking():
                return False
            if not self._select_date():
                return False
            if not self._select_court():
                return False
            if not self._finalize_booking():
                return False
            return True
        except Exception as e:
            self.logger.error(f"Booking failed for {self.user_prefix}: {str(e)}")
            return False
        finally:
            if self.logged_in:
                self._logout()
            self.driver.quit()

    def _login(self):
        """User-specific login implementation."""
        try:
            login_info = self.config['login']
            self.driver.get(login_info['url'])

            # Login form interaction
            self.wait.until(EC.presence_of_element_located((By.ID, 'weblogin_username'))).send_keys(login_info['username'])
            self.driver.find_element(By.ID, 'weblogin_password').send_keys(login_info['password'])
            self.driver.find_element(By.ID, 'weblogin_buttonlogin').click()

            # Handle session warnings
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, 'loginresumesession_buttoncontinue'))).click()
            except TimeoutException:
                pass

            self.logged_in = True
            self.logger.info("Login successful")
            return True
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False

    def _navigate_to_booking(self):
        """Navigate to the booking page and clear any existing selections."""
        try:
            self.logger.info("Navigating to booking page")
            field_house_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'tile')]//h2[contains(text(), 'Field House Courts')]/ancestor::a"))
            )
            field_house_link.click()
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Facility Search')]")))
            self.logger.info("Booking page loaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to navigate to booking page: {str(e)}")
            return False
    def _select_date(self):
        """Select the desired booking date using the dropdown selectors."""
        try:
            desired_date = self.config['booking']['date']
            self.logger.info(f"Selecting date: {desired_date}")

            # Open datepicker
            date_picker_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'datepicker-button')]"))
            )
            date_picker_button.click()

            # Parse the desired date
            year, month, day = desired_date.split('-')
            month_int = int(month)
            day_int = int(day)
            year_int = int(year)

            # Get month name from month number
            month_names = ["January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"]
            target_month = month_names[month_int - 1]

            # Select month, day, and year
            self._select_dropdown_option("month_selection_button", target_month)  # Use month name
            self._select_dropdown_option("day_selection_button", day_int)
            self._select_dropdown_option("year_selection_button", year_int)

            # Confirm selection
            done_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'datepicker-button-primary') and contains(text(), 'Done')]"))
            )
            done_button.click()

            # Click search button
            search_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@id, 'frwebsearch_buttonsearch')]"))
            )
            search_button.click()

            self.logger.info(f"Date {desired_date} selected successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to select date: {str(e)}")
            return False

    def _select_dropdown_option(self, dropdown_id, value):
        """Select an option from a dropdown by its ID and value."""
        try:
            # Click the dropdown to open it
            dropdown = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(@id, '{dropdown_id}')]"))
            )
            dropdown.click()

            # Select the option based on the value
            option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//li[@role='option']//span[contains(@class, 'listitem__text') and text()='{value}']"))
            )
            option.click()

            self.logger.info(f"Selected option: {value}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to select dropdown option: {str(e)}")
            return False

    def _select_court(self):
        """Select a court and time slot based on the sport type in the config file."""
        try:
            desired_time = self.config['booking']['time']
            facility_type = self.config['booking']['facility'].lower()
            court_number = self.config['booking'].get('court_number', '')

            self.logger.info(f"Looking for {facility_type} court (preferred court #{court_number if court_number else 'any'})")

            # Parse time
            hour, minute = self._parse_time(desired_time)
            am_pm = "am" if hour < 12 else "pm"
            next_hour = (hour + 1) % 24
            next_am_pm = "am" if next_hour < 12 else "pm"

            # Format time strings for matching
            time_formats = [
                f"{hour % 12 or 12}:00 {am_pm} - {next_hour % 12 or 12}:00 {next_am_pm}",
                f"{hour % 12 or 12}:{minute:02d} {am_pm} - {next_hour % 12 or 12}:{minute:02d} {next_am_pm}",
                f"{hour % 12 or 12}:00 {am_pm}",
                f"{hour % 12 or 12} {am_pm}",
            ]

            # Wait for search results
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dateblock")))
            time.sleep(1)

            # Find all result content divs
            result_contents = self.driver.find_elements(By.CLASS_NAME, "result-content")
            self.logger.info(f"Found {len(result_contents)} court options")

            # Find matching courts
            court_matches = self._find_matching_courts(result_contents, facility_type, court_number, time_formats)
            if not court_matches:
                self.logger.error(f"No {facility_type} courts found with available slots matching {hour % 12 or 12}:{minute:02d} {am_pm}")
                return False

            # Select the best court
            best_court_name, best_court = sorted(court_matches.items(), key=lambda x: x[1]['score'], reverse=True)[0]
            self.logger.info(f"Selected best matching court: {best_court_name} (Score: {best_court['score']})")

            # Click on the first available slot
            selected_slot, slot_time = best_court['slots'][0]
            self.logger.info(f"Clicking on time slot: {slot_time}")
            selected_slot.click()

            # Handle additional confirmation
            try:
                if "instant-overlay" in selected_slot.get_attribute("class"):
                    self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "instant-overlay-content")))
                    continue_buttons = self.driver.find_elements(
                        By.XPATH,
                        "//button[contains(text(), 'Continue') or contains(text(), 'Book') or contains(text(), 'Add to Cart')]"
                    )
                    if continue_buttons:
                        self.logger.info(f"Clicking '{continue_buttons[0].text}' button")
                        continue_buttons[0].click()

                self.logger.info("Checking if time slot was added to cart")
                cart_indicators = self.driver.find_elements(By.XPATH, "//a[contains(@class, 'wt-cart-button')]")
                if cart_indicators:
                    self.logger.info("Item appears to be added to cart")

            except (TimeoutException, NoSuchElementException) as e:
                self.logger.info(f"No additional confirmation needed or error occurred: {str(e)}")

            self.logger.info(f"{best_court_name} at {slot_time} selected and added to cart successfully")
            return True

        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"Failed to select court and time: {str(e)}")
            return False

    def _parse_time(self, desired_time):
        """Parse the desired time into 24-hour format."""
        clean_time = desired_time.strip().lower()
        am_indicator = any(x in clean_time for x in ['am', 'a.m.', 'a.m'])
        pm_indicator = any(x in clean_time for x in ['pm', 'p.m.', 'p.m'])
        numeric_part = ''.join([c for c in clean_time if c.isdigit() or c == ':'])

        if ':' in numeric_part:
            hour_str, minute_str = numeric_part.split(':')
            hour = int(hour_str)
            minute = int(minute_str) if minute_str else 0
        else:
            hour = int(numeric_part) if numeric_part else 0
            minute = 0

        if pm_indicator and hour < 12:
            hour += 12
        elif am_indicator and hour == 12:
            hour = 0

        return hour, minute

    def _find_matching_courts(self, result_contents, facility_type, court_number, time_formats):
        """Find courts matching the facility type and available time slots."""
        court_matches = {}
        for court_div in result_contents:
            try:
                court_title = court_div.find_element(By.XPATH, ".//h2/span").text
                court_description = court_div.find_element(By.XPATH, ".//div[contains(@class, 'result-header__description')]").text
                court_text = (court_title + " " + court_description).lower()
                score = 0

                if facility_type in court_text:
                    score += 100
                    if court_number and f"{facility_type} {court_number}" in court_text:
                        score += 50
                    if "badminton" in facility_type and "badminton" in court_text:
                        score += 30
                    if "pickle" in facility_type and "pickle" in court_text:
                        score += 30

                if score > 0:
                    time_slots = court_div.find_elements(
                        By.XPATH,
                        ".//a[contains(@class, 'button') and contains(@class, 'cart-button')]"
                    )
                    available_slots = []
                    for slot in time_slots:
                        if "success" in slot.get_attribute("class"):
                            slot_text = slot.text.strip()
                            for time_format in time_formats:
                                if time_format.lower() in slot_text.lower():
                                    available_slots.append((slot, slot_text))
                                    break

                    if available_slots:
                        score += 50
                        court_matches[court_title] = {
                            'div': court_div,
                            'score': score,
                            'slots': available_slots
                        }
                        self.logger.info(f"Found candidate court: {court_title} (Score: {score}) with {len(available_slots)} matching slots")

            except NoSuchElementException as e:
                self.logger.info(f"Error examining court: {str(e)}")
                continue

        return court_matches

    def _finalize_booking(self):
        """Complete the booking process by confirming the reservation."""
        try:
            self.logger.info("Confirming booking")
            add_to_cart_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'multiselectlist__addbutton') and .//span[contains(text(), 'Add To Cart')]]")))
            add_to_cart_button.click()

            # Verify booking details
            booking_header = self.wait.until(EC.presence_of_element_located((By.XPATH, "//h1[@id='processingprompts_header']")))
            header_text = booking_header.text
            self.logger.info(f"Found booking header: {header_text}")

            # Fill in required form fields
            cell_number = self.config['booking'].get('cell_number', '')
            booking_reason = self.config['booking'].get('booking_reason', '')

            cell_field = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@id='question150906610']")))
            cell_field.clear()
            cell_field.send_keys(cell_number)

            reason_field = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@id='question150906642']")))
            reason_field.clear()
            reason_field.send_keys(booking_reason)

            # Proceed to checkout
            continue_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(text(), 'Continue') or contains(text(), 'Next')] | " +
                "//input[@value='Continue' or @value='Next']"
            )
            if continue_buttons:
                self.logger.info(f"Clicking continue button: '{continue_buttons[0].get_attribute('value') or continue_buttons[0].text}'")
                #continue_buttons[0].click()

            self.logger.info("Booking finalized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to finalize booking: {str(e)}")
            return False

    def _logout(self):
        """Logout from the booking website."""
        try:
            if not self.logged_in:
                self.logger.info("No active session to log out from")
                return True

            self.logger.info("Attempting to log out")

            # First, try the primary logout method (user menu dropdown)
            try:
                # Click on the user menu that contains the SVG icon and username
                user_menu = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'menuitem__title') and contains(., '#')]"))
                )
                self.logger.info("Found user menu by class and ID")
                user_menu.click()

                # Click on the Logout option in the dropdown
                logout_option = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'menuitem__text') and text()='Logout']"))
                )
                self.logger.info("Found logout option")
                logout_option.click()

                # Wait for "Sign In / Register" to appear, confirming successful logout
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//span[@class='menuitem__text' and text()='Sign In / Register']"))
                )

                self.logger.info("Logout successful - 'Sign In / Register' text found")
                self.logged_in = False
                return True

            except (TimeoutException, NoSuchElementException) as e:
                self.logger.error(f"Could not find user menu: {str(e)}")

                # Fallback to alternative approach - look for any logout link
                self.logger.info("Trying alternative logout approach")
                try:
                    # Direct approach - try to find any logout link on the page
                    logout_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Log Out') or contains(text(), 'Logout')]")
                    logout_link.click()

                    # Wait for "Sign In / Register" to appear
                    self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//span[@class='menuitem__text' and text()='Sign In / Register']"))
                    )

                    self.logger.info("Direct logout successful - 'Sign In / Register' text found")
                    self.logged_in = False
                    return True

                except Exception as direct_e:
                    self.logger.error(f"Direct logout approach failed: {str(direct_e)}")

                    # Last resort - try to navigate to the login page directly
                    try:
                        self.logger.info("Attempting to navigate to login page directly")
                        self.driver.get(self.config['login']['url'])

                        # Check for "Sign In / Register" presence
                        sign_in_element = self.driver.find_elements(By.XPATH, "//span[@class='menuitem__text' and text()='Sign In / Register']")

                        if sign_in_element or "login" in self.driver.current_url.lower():
                            self.logger.info("Forced logout by navigation successful")
                            self.logged_in = False
                            return True
                        else:
                            self.logger.error("Failed to force logout by navigation")
                            return False

                    except Exception as nav_e:
                        self.logger.error(f"Navigation approach failed: {str(nav_e)}")
                        return False

        except Exception as e:
            self.logger.error(f"Logout failed: {str(e)}")
            return False


def get_valid_users():
    """Extract all valid user prefixes from the config file."""
    config = configparser.ConfigParser()
    config.read('config.ini')

    users = []
    for section in config.sections():
        if section.endswith('_LOGIN'):
            user_prefix = section[:-6]
            if f"{user_prefix}_BOOKING" in config.sections():
                users.append(user_prefix)
    return users


def main():
    parser = argparse.ArgumentParser(description="Multi-user Court Booking System")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output")
    parser.add_argument("--screenshots", action="store_true", help="Enable screenshots")
    parser.add_argument("--use-config-date", action="store_true", help="Use config dates")
    args = parser.parse_args()

    # Get all valid users from the config file
    users = get_valid_users()
    if not users:
        print("No valid user configurations found")
        return

    results = {}
    for user in users:
        print(f"\nProcessing booking for {user}")
        booker = CourtBooker(
            user_prefix=user,
            headless=args.headless,
            suppress_console=args.quiet,
            take_screenshots=args.screenshots,
            use_config_date=args.use_config_date
        )
        results[user] = booker.execute_booking()

    # Print booking results
    print("\nBooking Results:")
    for user, success in results.items():
        print(f"{user}: {'Success' if success else 'Failed'}")


if __name__ == "__main__":
    main()