'''
Kibana Dev Tools Console Parser

'''
import os
import json
import time
import re
import logging
import logging.config

import yaml
import getpass
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from typing import List, Union


logger = logging.getLogger('console_parser')


class ConsoleParser:
    '''
    Startup kibana console, send search query and parse response

    '''

    XPATH_CONFIG_JSON = os.path.join('resources', 'constants.json')
    AUTH_JSON = os.path.join('resources', 'auth.json')
    BS_TEXT_SPLITTER = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    GET_LOOP_MAX_TIME = 60

    def __init__(self, auth_with_json: bool = False) -> None:
        # Read XPATHs and URLs
        with open(ConsoleParser.XPATH_CONFIG_JSON, 'r') as fin:
            self.constants = json.load(fin)

        # Startup browser
        logger.info('[ConsoleParser] Start web driver')
        self.driver = webdriver.Chrome(ChromeDriverManager().install())
        self.driver.get(self.constants['START_URL'])
        self.driver.implicitly_wait(1000)
        logger.info('[ConsoleParser] Web driver started')

        # Get auth data
        if auth_with_json:
            logger.info('[ConsoleParser] Read auth data from json')
            with open(ConsoleParser.AUTH_JSON, 'r') as fin:
                auth_data = json.load(fin)
        else:
            logger.info('[ConsoleParser] Read auth data from input')
            auth_data = {
                'login': input('login: '),
                'password': getpass.getpass('password: ')
            }

        self.startup_kibana_console(auth_data)

    def wait_for_element(self, xpath: str, wait_time: int = 1000):
        '''Wait for xpath to be located on page'''

        wait = WebDriverWait(self.driver, wait_time)
        wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        time.sleep(1)

    def startup_kibana_console(self, auth_data: dict) -> webdriver.Chrome:
        '''Login in Kibana and open Kibana DevTools console'''

        # Authorize and go to console
        try:
            logger.info('[startup_kibana_console] Start setup console')
            email_element = self.driver.find_element_by_xpath(self.constants['EMAIL_XPATH'])
            login_button_element = self.driver.find_element_by_xpath(self.constants['LOGIN_BUTTON_XPATH'])
            email_element.send_keys(auth_data['login'])
            login_button_element.click()
            self.wait_for_element(self.constants['PASSWORD_XPATH'])
            password_element = self.driver.find_element_by_xpath(self.constants['PASSWORD_XPATH'])
            password_element.send_keys(auth_data['password'])
            password_login_button_element = self.driver.find_element_by_xpath(self.constants['PASSWORD_LOGIN_XPATH'])
            password_login_button_element.click()
            self.wait_for_element(self.constants['DEV_TOOLS_XPATH'])
            self.driver.find_element_by_xpath(self.constants['DEV_TOOLS_XPATH']).click()
            self.wait_for_element(self.constants['CLOSE_INFO_XPATH'])
            self.driver.find_element_by_xpath(self.constants['CLOSE_INFO_XPATH']).click()

            # Change font size
            self.driver.execute_script("document.body.style.zoom = '0.1'")

            # Delete auth data
            del auth_data

        except Exception as ex:
            logger.error('[startup_kibana_console] ' + str(ex))
            raise ex

        logger.info('[startup_kibana_console] Console setup finished')

    def insert_console_text(self, text: str):
        '''Write text in console'''

        # self.wait_for_element(self.constants['INPUT_AREA_XPATH'])
        query_element = self.driver.find_element_by_xpath(self.constants['INPUT_AREA_XPATH'])
        # query_element.click()
        query_element.send_keys(text)

    def clear_console(self):
        '''Clear console input area'''

        self.insert_console_text(Keys.CONTROL + 'a')
        self.insert_console_text(Keys.DELETE)

    def send_query(self):
        '''Start search'''

        self.insert_console_text(Keys.CONTROL + Keys.ENTER)

    def get(self, query: dict, sleep_time=2) -> dict:
        '''Get search response for passed query'''

        query_str = json.dumps(query)
        search_src = self.constants['SEARCH_SRC']
        response_text = ""
        loop_ctr = 0

        logger.info(f'[get] query={query_str}')

        self.clear_console()
        self.insert_console_text(search_src + query_str)
        self.send_query()

        while len(response_text) == 0:
            logger.info(f'[get] Loop count = {loop_ctr}')

            if loop_ctr * sleep_time > ConsoleParser.GET_LOOP_MAX_TIME:
                logger.error('[get] Query timeout error')
                raise Exception("Get timeout excided")

            time.sleep(sleep_time)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            response_text = soup.get_text()
            logger.info(f'[get] Full response: <FULLRESPONSE>{response_text}<FULLRESPONSE>')

            if 'took' in response_text:
                response_text = response_text.split(self.BS_TEXT_SPLITTER)[-2]
                response_text = re.sub(r'^.*?{', '{', response_text)
                # response_text = re.sub(r'"""', '"', response_text)
            else:
                response_text = ""

            loop_ctr += 1

        response = Response(response_text)

        logger.info(f'[get] Parsed response: {response_text}')

        return response

    def close(self):
        '''Close browser'''

        self.driver.quit()
        logger.info('[close] Web driver closed')


class Response:
    '''
    Console parser response class

    '''

    def __init__(self, response_text: str):
        '''Create response from plain text'''

        self.__plane_text = response_text
        self.__log = self.get_log(self.__plane_text)
        self.__message = self.get_message(self.__log)

    @staticmethod
    def get_log(response: str) -> List[dict]:
        '''Extract logs from Dev Console response'''

        logger.info(f"[get_log] Start parse response text")
        result = []

        if 'message' in response:
            if '"""' not in response:
                response = re.sub('"message" : "', '"message" : """', response)
                response = re.sub('",     "@version"', '""",     "@version"', response)
            response = re.sub('"timed_out" : false', '"timed_out" : False', response)
            response = re.sub('"timed_out" : true', '"timed_out" : True', response)
            # TODO get rid of eval()
            response = eval(response)
            response_lst = response['hits']['hits']

            for itm in response_lst:
                if isinstance(itm, dict) and '_source' in itm:
                    result.append(itm['_source'])
                else:
                    result.append(dict())

        logger.info(f"[get_log] Response: {str(result)}")

        return result

    @staticmethod
    def get_message(logs_lst: List[dict]) -> List[str]:
        '''Extract message(s) from log'''

        msg_lst = []

        for log in logs_lst:

            if isinstance(log, dict) and 'message' in log.keys():
                msg_lst.append(log['message'])
            else:
                msg_lst.append(str())

        return msg_lst

    def __repr__(self):
        return self.plane_text

    def __str__(self):
        return self.plane_text

    @property
    def plane_text(self) -> Union[List[dict], dict, None]:
        '''Return formatted self.__plane_text'''

        if self.__plane_text and len(self.__plane_text) > 0:
            if len(self.__plane_text) > 1:
                res = self.__plane_text
            else:
                res = self.__plane_text[0]
        else:
            res = ""

        return res

    @property
    def log(self) -> Union[List[dict], dict]:
        '''Return formatted self.__log'''

        if self.__log and len(self.__log) > 0:
            if len(self.__log) > 1:
                res = self.__log
            else:
                res = self.__log[0]
        else:
            res = dict()

        return res

    @property
    def message(self) -> Union[List[str], str]:
        '''Return formatted self.plane_text'''

        if self.__message and len(self.__message) > 0:
            if len(self.__message) > 1:
                res = self.__message
            else:
                res = self.__message[0]
        else:
            res = str()

        return res


def setup_logging(logging_config):
    '''Setup logger'''

    if logging_config:
        with open(logging_config) as config_fin:
            logging.config.dictConfig(yaml.safe_load(config_fin))
