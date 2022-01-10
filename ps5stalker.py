from datetime import datetime
import os
import time
import traceback
import threading
from urllib.parse import urlparse
import webbrowser as wb

from bs4 import BeautifulSoup
import keyring
import requests
from selenium.webdriver import Chrome,  Firefox
from selenium.webdriver.common.by import By

from time import sleep
from selenium.common.exceptions import ElementClickInterceptedException

from datetime import datetime, timedelta
from selenium import webdriver
import logging
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.DEBUG,
                             format='%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s',
                             filename="log_ps5stalker.log")
logger = logging.getLogger(__name__)

opts = webdriver.ChromeOptions()

try:
    sys.cmd("Xvfb -ac :99 -screen 0 1280x1024x16 & export DISPLAY=:99")
except Exception as e:
    logger.exception("Xvfb failed to start.\t", repr(e))
else:
    opts.add_argument('--headless')

# opts.page_load_strategy = 'none'
opts.add_argument('--no-sandbox')
opts.add_argument('start-maximized')
opts.add_argument('enable-automation')
opts.add_argument('--disable-infobars')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--disable-browser-side-navigation')
opts.add_argument('--disable-gpu')
#chrome_opts.add_argument('--disable-extensions')
#opts.add_argument('--no-sandbox')
#opts.add_argument('headless')
#chrome_opts.add_argument('--disable-gpu')
#chrome_opts.add_argument('--disable-dev-shm-usage')
#chrome_opts.headless = True

#firefox_opts = webdriver.FirefoxOptions()
# firefox_opts.headless = True

COSTCO_EMAIL =  'yourcostcoemail@gmail.com'
PURCHASE = FALSE

class PS5Stalker:
    def __init__(self, url=None):
        self.driver = webdriver.Chrome(options=opts)
        if url is not None:
            self.url = url
        else:
            self.url = "https://www.costco.com/CatalogSearch?dept=All&keyword=playstation+5+console"
        self.driver.get(self.url)
        self.src = self.driver.page_source
        self.already_purchased = False
        # self.driver.minimize_window()

    def get_search_results(self):
        try:
            self.driver.get(self.url)
        except TimeoutException as e:
            logger.exception(repr(e))
            try:
                self.driver.close()
            except Exception:
                pass
            self.driver = Chrome(options=opts)
            self.driver.get(self.url)
        src = self.driver.page_source
        self.src = src
        return src

    def find_inventory(self, src):
        product_page = None
        # Finding Inventory
        soup = BeautifulSoup(src, 'html.parser')
        pl = soup.find(attrs={'class': 'product-list'})
        partNumbs = list(partNumb['value'] for partNumb in pl.find_all(attrs={'class': "partNumb"}))

        for partNumb in partNumbs:
            product = pl.find(attrs={"id": "in_Stock_" + partNumb})
            if product['value'] == '2':
                product_page = pl.find(attrs={'itemid': partNumb}).find("a")['href']

        return product_page

    def until_success(self, expression):
        try:
            expression
        except Exception:
            sleep(.1)
            self.until_success(expression)

    def add_product_to_cart(self):
    #     # This clicks on the product page
    #     element = self.driver.find_elements(By.PARTIAL_LINK_TEXT, value)[0]
    #     element.click()
        # This clicks sign in to buy
        self.until_success(self.driver.find_element(By.ID, 'sign-in-to-buy-button-v2').click())
        # Wait a bit
        # Send login info
        self.until_success(self.driver.find_element(By.ID, "logonId").send_keys(COSTCO_EMAIL))
        __password = keyring.get_password('costco.com', COSTCO_EMAIL)
        self.until_success(self.driver.find_element(By.ID, "logonPassword").send_keys(__password))
        self.until_success(self.driver.find_element(By.XPATH, '//*[@id="LogonForm"]/fieldset/div[6]/input').click())
        #driver.find_element(By.XPATH, "/html/body/div[8]/div[3]/div/div/div/div/form/fieldset/div[6]/input").click()

        # Clicks add to cart on page
        self.until_success(self.driver.find_element(By.ID, 'add-to-cart-btn').click())

    def retry_checkout(self):
        try:
            element = self.driver.find_element(By.ID, 'checkout-button-wrapper')
            element.find_element(By.CLASS_NAME, 'primary-button-green-v2').click()
        except ElementClickInterceptedException:
            sleep(.1)
            self.retry_checkout() 

    def click_checkout_until_success(self):
        try:
            self.driver.find_element(By.CLASS_NAME, 'primary-button-green-v2').click()
        except (ElementClickInterceptedException, Exception) as e:
            print(repr(e))
            sleep(.1)
            self.click_checkout_until_success()

    def enter_cc_details(self):
        # Click Credit or Debit payment
        rbs = self.driver.find_element(By.ID, 'payment-method-radio-buttons')
        rbs.find_element(By.CLASS_NAME, 'control__indicator').click()
        # Enter CC code
        iframe = self.driver.find_element(By.CSS_SELECTOR, "#cc_cvv_div > iframe")
        self.driver.switch_to.frame(iframe)
        # Enter CC Security Code
        __cvv = keyring.get_password('cc', 'cvv')
        self.driver.find_element(By.ID, 'securityCode').send_keys(__cvv)
        self.driver.switch_to.default_content()


    def checkout(self):
        if self.already_purchased is False:
            # Going to need to add some resiliancy here to beat out other bots / traffic load
            self.driver.get('https://www.costco.com/CheckoutCartView')
            # Click until success
            self.retry_checkout()
            # Enter CC Details
            self.enter_cc_details()
            # Continue to shipping opts
            self.click_checkout_until_success()
            #Checkout
            self.click_checkout_until_success()
            self.already_purchased = True

    def shopper(self):
        start = datetime.now()
        if self.already_purchased is False and PURCHASE is True:
            src = self.get_search_results()
            logger.info(f"get_search_results time: {(datetime.now() - start)}.")
            product_page = self.find_inventory(src)
            logger.info(f"find_inventory time: {(datetime.now() - start)}.")
            if bool(product_page):
                # Go to product page
                self.driver.get(product_page)
                self.add_product_to_cart()
                self.checkout()
            else:
                print(f"Out of stock at {datetime.now().strftime('%c')}")
        else:
            print('Already purchased. Please Quit.')
        logger.info(f"shopper time: {(datetime.now() - start)}.")

    def every(self, delay, task):
        next_time = time.time() + delay
        while True:
            time.sleep(max(0, next_time - time.time()))
            try:
                task()
            except Exception:
                traceback.print_exc()
            # skip should we fall behind
            next_time += (time.time() - next_time) // delay * delay + delay

    def main(self):
        return threading.Thread(target=lambda: self.every(30, self.shopper)).start()

if __name__ == "__main__":
    bot = PS5Stalker()
    bot.main()
