import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import psutil
import shutil


class AvitoParse:
    def __init__(self, product_name_search: str):
        self.driver = None
        self.product_name_search = product_name_search.replace(" ", "")
        self.url = "https://www.avito.ru/all?cd=1&q=" + self.product_name_search + "&s=104"
        self.product_data = dict()
        self.final_id_product = 0

    def set_up(self):
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        
        prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.automatic_downloads": 2
        }
        options.add_experimental_option("prefs", prefs)

        chromium_path = shutil.which("chromium") or "/usr/bin/chromium"
        chromedriver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"

        options.binary_location = chromium_path

        self.driver = uc.Chrome(version_main=90, options=options)  
    
    def cleanup_driver(self):
        if self.driver:
          self.driver.quit()
          self.driver = None
      
        for proc in psutil.process_iter(['pid', 'name']):
            if 'chromedriver' in proc.info['name'] or 'chrome' in proc.info['name']:
                try:
                    psutil.Process(proc.info['pid']).kill()
                except psutil.NoSuchProcess:
                    pass

    def get_url(self):
        self.driver.get(self.url)

    def get_pictures(self, title):
        image_elements = title.find_elements(By.CSS_SELECTOR, "img[itemprop='image']")

        images_high_res = []
        for img in image_elements:
            srcset = img.get_attribute("srcset")
            if srcset:
                largest_image = srcset.split(",")[-1].split(" ")[0]
                images_high_res.append(largest_image)
            else:
                images_high_res.append(img.get_attribute("src"))
        return tuple(images_high_res)

    def parse_page(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-marker='item']"))
            )
            title = self.driver.find_element(By.CSS_SELECTOR, "[data-marker='item']")
            name_product = title.find_element(By.CSS_SELECTOR, "[itemprop='name']").text
            cost_product = title.find_element(By.CSS_SELECTOR, "[itemprop='price']").get_attribute("content")
            id_product = title.get_attribute("data-item-id")
            about_product = title.find_element(By.XPATH, "//*[@id='i4751899569']/div/div/div[2]/div[4]/div[1]/p").text[:200]
            url_product = title.find_element(By.CSS_SELECTOR, "[itemprop='url']").get_attribute("href")
            pictures_product = self.get_pictures(title)
            self.product_data.clear()
            self.product_data[id_product] = [
                name_product,
                cost_product,
                about_product,
                url_product,
                pictures_product
            ]
        finally:
            self.cleanup_driver()
            
    def parse(self):
        self.set_up()
        try:
            self.get_url()
            self.parse_page()
        finally:
            self.cleanup_driver()

    def updates_product(self):
        if list(self.product_data.keys())[0] == self.final_id_product:
            self.product_data.clear()
            return None
        else:
            self.final_id_product = list(self.product_data.keys())[0]
            self.product_data = {self.final_id_product: self.product_data[self.final_id_product]}
            return self.product_data
