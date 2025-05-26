import os
import time
import csv
import logging
import random
from datetime import datetime
import sys
import keyboard
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print("Current working directory:", os.getcwd())
print("Logs directory:", os.path.abspath('logs'))
print("Data directory:", os.path.abspath('data'))
print("Can write to current directory?", os.access(os.getcwd(), os.W_OK))

# Configuration
KEYWORDS = ['vaksin', 'vaksin covid', 'enggak vaksin', 'takut vaksin',"no mandate","my body my choice","natural immunity",
            "komunitas anti vaksin","lawan vaksin","komunitas prokes","komunitas tolak total","rumah sehat","vaksin sehat atau hoax","tanpa vaksin","hidup sehat natural","vaksin versus herbal","pengobatan alami",
            "efek samping vaksin","vaksin bikin sakit","reaksi vaksin","kematian vaksin","vaksin alergi","vaksin tidak efektif","gagal vaksin","kesehatan vaksin","sakit setelah vaksin","penyakit setelah vaksin",
            "diskusi vaksin","tanya vaksin","pro dan contra vaksin","vaksin debat","vaksin versus virus","cerita vaksin","pengalaman setelah vaksin","vaksin baik buruk","vaksin dilema","cerita keluarga vaksin",
            "indonesia lawan covid","vaksinasi nasional","vaksin untuk negeri","ayo vaksin","lindungi diri","lindungi keluarga","kita bisa lewat ","jangan mudik vaksin dulu","serbu vaksin","vaksin di kampung" ]

"""['vaksin', 'vaksin covid', 'enggak vaksin', 'takut vaksin', 
            'efek vaksin', 'vaksinasi', 'anti vaksin', 'ragu vaksin','vaccine hesitancy', 'vaccine indonesia',"vaksinasi COVID19","vaksin COVID19","program vaksin","vaksin gratis",
            "vaksin aman","vaksin halal","vaksin untuk semua","vaksin indonesia","tolak vaksin","saya tidak vaksin","vaksin haram","vaksin bikin mati","vaksin berbahaya","vaksin merusak","vaksin tidak aman",
            "vaksin membunuh","vaksin tidak halal","vaksin konspirasi","haram vaksin","vaksin haram","vaksin babi","vaksin tak halal","vaksin tak syar’i","vaksin haram pemerintah","vaksin bukan jihad",
            "takdirAllah lebih baik","vaksin tidak sesuai syariat","vaksin melawan iman","vaksin chip","chip vaksin","vaksin agenda","vaksin depopulasi","elit global","vaksin 5g","plandemik","plandemic",
            "anti vaksin","vaksin agenda iblis","info vaksin","berita vaksin","update covid","hoax vaksin","berita vaksinasi","covid indo","covid19 indonesia","pandemi indonesia","info covid19","infopenting",
            "no vaccine for me","anti vaccine","vaccine hoax","vaccine injury","vaccine freedom","vaxxed","vaxxed nation","no mandate","my body my choice","natural immunity",
            "komunitas anti vaksin","lawan vaksin","komunitas prokes","komunitas tolak total","rumah sehat","vaksin sehat atau hoax","tanpa vaksin","hidup sehat natural","vaksin versus herbal","pengobatan alami",
            "efek samping vaksin","vaksin bikin sakit","reaksi vaksin","kematian vaksin","vaksin alergi","vaksin tidak efektif","gagal vaksin","kesehatan vaksin","sakit setelah vaksin","penyakit setelah vaksin",
            "diskusi vaksin","tanya vaksin","pro dan contra vaksin","vaksin debat","vaksin versus virus","cerita vaksin","pengalaman setelah vaksin","vaksin baik buruk","vaksin dilema","cerita keluarga vaksin",
            "indonesia lawan covid","vaksinasi nasional","vaksin untuk negeri","ayo vaksin","lindungi diri","lindungi keluarga","kita bisa lewat ","jangan mudik vaksin dulu","serbu vaksin","vaksin di kampung" ]"""

LANG = 'id'
LOG_INTERVAL = 120  # 2 minutes
BREAK_INTERVAL = 30  # 30 seconds
BREAK_AFTER = 100  # Take break after 50 requests
SHUTDOWN_COMBO = {'ctrl', 'alt', 'shift', 's'}
MAX_TWEETS_PER_KEYWORD = 200

# Twitter Credentials (Fill these in)
TWITTER_USERNAME = "Barry11017454"
TWITTER_PASSWORD = "meatloaf88"

class TwitterVaccineScraper:
    def __init__(self):
        # Set the base directory to the script's location
        self.base_dir = os.path.dirname(os.path.abspath(__file__))  # D:\ProjectDatMin\scraper
        print(f"Files will be saved in: {self.base_dir}")

        # Define log/data paths relative to the script
        self.logs_dir = os.path.join(self.base_dir, "logs")
        self.data_dir = os.path.join(self.base_dir, "data")
        
        # Create directories
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize components
        self.setup_logging()
        self.csv_file = os.path.join(self.data_dir, f"tweets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        self.setup_csv()
        self.setup_shutdown()
        
        # Initialize counters
        self.tweet_count = 0
        self.request_count = 0
        self.running = True
        self.last_save_time = time.time()
        self.driver = None
        
    def setup_logging(self):
        """Initialize logging system with both file and console output"""
        self.log_file = os.path.join(self.logs_dir, f"scraper_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Clear any existing handlers
        logging.getLogger().handlers = []
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Create handlers
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logging.info(f"Logging initialized at: {self.log_file}")
        
    def verify_setup(self):
        """Verify directory setup and create sample CSV before proceeding"""
        try:
            logging.info("Verifying directory structure and file permissions")
            
            # Create sample CSV file using data_dir
            sample_file = os.path.join(self.data_dir, "sample_tweets.csv")
            sample_data = [
                ['id', 'date', 'username', 'content', 'url', 'keyword', 'likes', 'retweets', 'replies'],
                ['sample123', '2023-01-01', 'test_user', 'This is a sample tweet', 
                 'https://twitter.com/test_user/status/sample123', 'sample_keyword', 10, 2, 1]
            ]
            
            with open(sample_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(sample_data)
            logging.info(f"Created sample CSV file at {sample_file}")
            
            # Verify the sample file
            if os.path.exists(sample_file):
                with open(sample_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if len(rows) == 2 and len(rows[0]) == 9:
                        logging.info("Sample CSV verification successful")
                    else:
                        logging.warning("Sample CSV format doesn't match expected structure")
            
        except Exception as e:
            logging.error(f"Setup verification failed: {str(e)}")
            raise
        
    def setup_csv(self):
        """Initialize the CSV file with headers"""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'date', 'username', 'content', 'url', 'keyword', 'likes', 'retweets', 'replies'])
        logging.info(f"CSV file created at: {self.csv_file}")
        
    def init_driver(self):
        try:
            options = Options()
            # options.add_argument("--headless")  # Disable headless for debugging
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1200,900")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logging.info("WebDriver initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Driver initialization failed: {str(e)}")
            return False
        
    def login_to_twitter(self):
        try:
            logging.info("Attempting to login to Twitter")
            self.driver.get("https://twitter.com/i/flow/login")
            
            # Wait for username field
            username_field = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//input[@autocomplete="username"]')))
            self.human_type(username_field, TWITTER_USERNAME)
            
            # Click next
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Next")]')))
            next_button.click()
            time.sleep(2)
            
            # Handle possible unusual login activity check
            try:
                unusual_activity = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//span[contains(text(), "unusual login activity")]')))
                if unusual_activity:
                    logging.info("Detected unusual login activity check")
                    input("Please complete the manual verification and press Enter to continue...")
            except (NoSuchElementException, TimeoutException):
                pass
            
            # Input password
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//input[@autocomplete="current-password"]')))
            self.human_type(password_field, TWITTER_PASSWORD)
            
            # Click login
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Log in")]')))
            login_button.click()
            
            # Wait for login to complete
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//a[@aria-label="Home"]')))
            
            logging.info("Successfully logged in to Twitter")
            return True
            
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False
            
    def human_type(self, element, text):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
    def save_tweet(self, tweet_data):
        try:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    tweet_data.get('id', ''),
                    tweet_data.get('date', ''),
                    tweet_data.get('username', ''),
                    tweet_data.get('content', ''),
                    tweet_data.get('url', ''),
                    tweet_data.get('keyword', ''),
                    tweet_data.get('likes', 0),
                    tweet_data.get('retweets', 0),
                    tweet_data.get('replies', 0)
                ])
            self.tweet_count += 1
            logging.info(f"Saved tweet from @{tweet_data.get('username', '')}")
        except Exception as e:
            logging.error(f"Error saving tweet: {str(e)}")
            
    def autosave_check(self):
        current_time = time.time()
        if current_time - self.last_save_time >= LOG_INTERVAL:
            logging.info(f"Autosave checkpoint - {self.tweet_count} tweets collected so far")
            self.last_save_time = current_time
            return True
        return False
        
    def take_break(self):
        logging.info(f"Taking {BREAK_INTERVAL} second break after {BREAK_AFTER} requests")
        time.sleep(BREAK_INTERVAL)
        self.request_count = 0
        
    def scrape_tweets(self, keyword):
        if not self.init_driver():
            return False
            
        try:
            # Login first
            if not self.login_to_twitter():
                logging.error("Cannot proceed without login")
                return False
                
            encoded_keyword = keyword.replace(' ', '%20')
            url = f"https://twitter.com/search?q={encoded_keyword}%20lang%3A{LANG}&src=typed_query"
            self.driver.get(url)
            
            # Wait for tweets to load
            time.sleep(5)
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            tweets_collected = 0
            scroll_attempts = 0
            
            while tweets_collected < MAX_TWEETS_PER_KEYWORD and self.running and scroll_attempts < 5:
                # Scroll to load more tweets
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3 + random.uniform(0, 2))
                
                # Find tweet elements
                tweet_elements = []
                try:
                    tweet_elements = self.driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')
                except NoSuchElementException:
                    logging.warning("No tweets found with standard selector")
                
                if not tweet_elements:
                    try:
                        tweet_elements = self.driver.find_elements(By.XPATH, '//div[@data-testid="cellInnerDiv"]//article')
                        logging.info(f"Found {len(tweet_elements)} tweets with alternative selector")
                    except NoSuchElementException:
                        logging.warning("No tweets found with alternative selector either")
                
                for tweet in tweet_elements:
                    if not self.running or tweets_collected >= MAX_TWEETS_PER_KEYWORD:
                        break
                        
                    try:
                        tweet_data = self.extract_tweet_data(tweet, keyword)
                        if tweet_data:
                            self.save_tweet(tweet_data)
                            tweets_collected += 1
                            self.request_count += 1
                            
                            if self.autosave_check():
                                logging.info("Autosave completed")
                                
                            if self.request_count % BREAK_AFTER == 0:
                                self.take_break()
                    except StaleElementReferenceException:
                        logging.warning("Stale element reference encountered, skipping tweet")
                        continue
                    except Exception as e:
                        logging.error(f"Error processing tweet: {str(e)}")
                        continue
                
                # Check if we've reached the end of available tweets
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                    logging.info(f"No new tweets loaded after scroll (attempt {scroll_attempts}/5)")
                else:
                    scroll_attempts = 0
                last_height = new_height
                
            return tweets_collected > 0
            
        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def extract_tweet_data(self, tweet_element, keyword):
        try:
            # Extract username
            username_element = tweet_element.find_element(By.XPATH, './/div[@data-testid="User-Name"]//a[contains(@href, "/")]')
            username = username_element.get_attribute('href').split('/')[-1]
            
            # Extract tweet content
            content_element = tweet_element.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
            content = content_element.text
            
            # Extract tweet URL
            link_element = tweet_element.find_element(By.XPATH, './/a[contains(@href, "/status/")]')
            url = link_element.get_attribute('href')
            tweet_id = url.split('/')[-1]
            
            # Extract date/time
            time_element = tweet_element.find_element(By.TAG_NAME, 'time')
            date = time_element.get_attribute('datetime')
            
            # Extract engagement metrics
            def get_metric(metric_name):
                try:
                    metric_element = tweet_element.find_element(
                        By.XPATH, f'.//div[@data-testid="{metric_name}"]//span'
                    )
                    return int(metric_element.text.replace(',', '') if metric_element.text else 0)
                except (NoSuchElementException, ValueError):
                    return 0

            likes = get_metric('like')
            retweets = get_metric('retweet')
            replies = get_metric('reply')

            return {
                'id': tweet_id,
                'date': date,
                'username': username,
                'content': content,
                'url': url,
                'keyword': keyword,
                'likes': likes,
                'retweets': retweets,
                'replies': replies
            }
        except Exception as e:
            logging.warning(f"Couldn't extract all data from tweet: {str(e)}")
            return None
        
    def setup_shutdown(self):
        def shutdown_listener():
            while True:
                if keyboard.is_pressed('ctrl') and keyboard.is_pressed('alt') and keyboard.is_pressed('shift') and keyboard.is_pressed('s'):
                    logging.warning("Shutdown combo detected. Type 'STOP' to confirm.")
                    user_input = input("Type 'STOP' to confirm shutdown: ")
                    if user_input.strip().upper() == "STOP":
                        logging.info("Shutdown confirmed. Saving data and exiting...")
                        self.running = False
                        if self.driver:
                            self.driver.quit()
                        sys.exit(0)
                    else:
                        logging.info("Shutdown aborted.")
                time.sleep(0.1)
                
        shutdown_thread = Thread(target=shutdown_listener)
        shutdown_thread.daemon = True
        shutdown_thread.start()
        
    def run(self):
        logging.info("Starting scraping process")
        for keyword in KEYWORDS:
            if not self.running:
                break
                
            logging.info(f"Searching for: {keyword}")
            success = self.scrape_tweets(keyword)
            
            if not success:
                logging.warning(f"Failed to scrape keyword: {keyword}")
                
            # Random delay between keywords
            delay = 5 + random.uniform(0, 5)
            logging.info(f"Waiting {delay:.1f} seconds before next keyword...")
            time.sleep(delay)
                
        logging.info(f"Scraping completed. Total tweets collected: {self.tweet_count}")


print("Current working directory:", os.getcwd())
print("Logs directory:", os.path.abspath('logs'))
print("Data directory:", os.path.abspath('data'))
print("Can write to current directory?", os.access(os.getcwd(), os.W_OK))

if __name__ == "__main__":
    try:
        scraper = TwitterVaccineScraper()
        scraper.run()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Shutting down...")
        if hasattr(scraper, 'running'):
            scraper.running = False
        if hasattr(scraper, 'driver') and scraper.driver:
            scraper.driver.quit()
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
        if hasattr(scraper, 'driver') and scraper.driver:
            scraper.driver.quit()
    finally:
        if 'scraper' in locals():
            logging.info(f"Final count: {scraper.tweet_count} tweets saved to {getattr(scraper, 'csv_file', 'unknown')}")