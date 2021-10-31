import scrapy
from scrapy import Selector
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver

import pandas as pd


class CarSalesSpider(scrapy.Spider):
    name = 'cardeals'

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.edmunds.com"
        self.start_url = "https://www.edmunds.com/cars-for-sale-by-owner/"
        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service)
        self.postal_code = ""
        self.slider_input = 0
        self.original_response = Selector(text="")
        self.data = {
            "Name": [],
            "Price": [],
            "VIN": [],
            "Vehicle Summary": [],
            "Top Feature Specs": []
                }

        self.next_page = Selector(text="")

    @staticmethod
    def check_code(postal):
        """
        Checks the postal code input to ensure its in the right format.
        Args:
            postal (str): Postal code input

        Returns:

        """
        is_good = True
        code_length = len(postal)
        if code_length == 5:
            for char in postal:
                is_good = char.isdigit()
                if not is_good:
                    break
        else:
            is_good = False

        return is_good

    @staticmethod
    def check_slider_input(slider_input):
        """
        Checks the slider input to ensure its in the right format.
        Args:
            slider_input (int): The slider input in integer

        Returns:

        """
        is_good = isinstance(slider_input, int)
        if is_good:
            if 0 < slider_input < 7:
                return is_good
        return is_good

    def input_data(self):
        """
        This function is used to handle user data input for both the postal code and the slider.
        Returns:

        """
        valid_postal = valid_slider_input = False

        while not valid_postal:
            self.postal_code = str(input("Enter postal code, no spaces, 5 digits: "))
            valid_postal = self.check_code(self.postal_code)

            if not valid_postal:
                print("Error please try again")

        print("Postal Code is correct")

        while not valid_slider_input:
            print(f"""Please select mile radius
                                    Type 0: for 10 mile radius,
                                    Type 1: For 25 mile radius,
                                    Type 2: For 50 mile radius,
                                    Type 3: For 75 mile radius,
                                    Type 4: For 100 mile radius,
                                    Type 5: For 200 mile radius,
                                    Type 6: For 500 mile radius,
                        """)
            self.slider_input = int(input())
            valid_slider_input = self.check_slider_input(self.slider_input)

            if not valid_slider_input:
                print("Error please try again")

        print("Mile Radius Correct")

    def get_selector(self):
        """
        This function is used to obtain the Scrapy Selector object for the first page.
        Returns:
            self.original_response (Selector object)

        """
        self.driver.get(self.start_url)
        # Maximize Window to ensure all fields are obtained
        self.driver.maximize_window()

        # Input postal code inside postal code element
        postal_input_element = self.driver.find_element(By.XPATH, "//input[@name='zip']")
        actions = ActionChains(self.driver)
        actions.click(on_element=postal_input_element)
        actions.send_keys_to_element(postal_input_element, self.postal_code)
        actions.perform()

        # Input slider value
        slide_element = self.driver.find_element(By.XPATH, "//input[@id='search-radius-range-min']")
        ActionChains(self.driver).click_and_hold(slide_element).pause(1).move_by_offset(-2, 0).perform()  # reset slider
        ActionChains(self.driver).click_and_hold(slide_element).pause(1).move_by_offset(self.slider_input, 0).perform()

        # Get Selenium response and convert it to a scrapy's Selector object
        selenium_response_html = self.driver.page_source
        self.original_response = Selector(text=selenium_response_html)
        return self.original_response

    def get_next_page_selector(self, url):
        """
        This is used to generate selector objects for the next page.
        Args:
            url:

        Returns:
            next_page: The Selector object for the next page

        """

        absolute_url = f"{self.base_url}{url}"
        self.driver.get(absolute_url)
        next_page_html = self.driver.page_source
        next_page = Selector(text=next_page_html)

        return next_page

    def get_data(self, response):
        """
        This is used to extract the data for all the selector objects
        Args:
            response: The selector object of a web page.

        Returns:

        """
        # Get all the spans in the page
        spans = response.xpath("//a[@class='usurp-inventory-card-vdp-link']")

        for span in spans:
            if span.xpath(".//@aria-label").get():
                # Get the name of the vehicles
                self.data["Name"].append(span.xpath(".//@aria-label").get())
                # Enter each of the links
                self.driver.get(f"{self.base_url}{span.xpath('.//@href').get()}")

                # Turn the inside page into another scrapy selector object
                selenium_span_response = self.driver.page_source
                span_selector = Selector(text=selenium_span_response)

                # Extract the rest of the data
                self.data["Price"].append(span_selector.xpath("//span[@data-test='vdp-price-row']/text()").get())
                self.data["VIN"].append(span_selector.xpath("//span[@class='mr-1']//text()[2]").get())
                self.data["Vehicle Summary"].append(span_selector.xpath("//div[@class='col']/text()").getall())
                # To get a dictionary of Top Feature and Specs
                spec_dict = {}
                spec_category = span_selector.xpath(
                    "//div[@class='mb-1 col-12 col-md-6']/div[@class='font-weight-bold mb-0_5']//text()").getall()

                if spec_category:  # get the individual specs and features if it exists
                    for i, spec in enumerate(spec_category):
                        spec_dict[spec] = span_selector.xpath(f"(//ul[@class='pl-1 mb-0'])[{i + 1}]//text()").getall()

                self.data["Top Feature Specs"].append(spec_dict)

        next_page_url = response.xpath("//a[@data-tracking-value='next']/@href").get()
        if next_page_url:
            next_page_selector = self.get_next_page_selector(next_page_url)
            self.get_data(next_page_selector)
        else:
            output = pd.DataFrame.from_dict(self.data)
            output.to_excel("All_pages.xlsx")


if __name__ == '__main__':
    car_sales = CarSalesSpider()
    car_sales.input_data()
    first_page = car_sales.get_selector()
    car_sales.get_data(first_page)
