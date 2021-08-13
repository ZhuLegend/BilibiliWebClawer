import os
import pickle
import sqlite3
import time
import re

from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait


class BilibiliCrawler:
    def __init__(self):
        self.is_headless = True
        self.driver = self.get_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.cookies = self.read_cookies()

    def get_driver(self):
        if self.is_headless:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            return webdriver.Chrome(executable_path='./chromedriver',options=chrome_options)
        else:
            return webdriver.Chrome(executable_path='./chromedriver')

    def get_fans_info(self, url='https://space.bilibili.com/25155419/fans/fans'):
        """
        返回fans_info，其中包含粉丝的昵称和个人简介
        :param url:默认为 https://space.bilibili.com/25155419/fans/fans
        :return: fans_info
        """

        self.driver.get(url)
        try:
            fans_info = []
            page_element = self.driver.find_element_by_xpath(
                '//*[@id="page-follows"]/div/div[2]/div[2]/div[2]/ul[2]/span[1]')
            page = re.search('[0-9]+', page_element.text).group()
            tbar = tqdm(range(int(page)))
            for i in tbar:
                tbar.set_description("正在遍历粉丝列表，目前在第%s页" % (i + 1), refresh=False)
                if i != page:
                    fans_elements = self.driver.find_elements_by_xpath(
                        '//*[@id="page-follows"]/div/div[2]/div[2]/div[2]/ul[1]/*')
                    if len(fans_elements):
                        for fans_element in fans_elements:
                            fan_uid_element = fans_element.find_element_by_class_name('cover')
                            fan_uid = re.search(r'.com/[0-9]+', fan_uid_element.get_attribute('href')).group()[5:]
                            fan_info = fans_element.text.split('\n')
                            fan_info = fan_info[:2]
                            fan_info.append(fan_uid)
                            fans_info.append(fan_info)
                        # print(fans_info)
                    else:
                        print("Can't find elements")
                        break
                    next_page_element = self.driver.find_element_by_xpath('//*[@id="page-follows"]/div/div[2]/div[\
                                                                          2]/div[2]/ul[2]/li[ @title="下一页"]')
                    next_page_element.click()
                    time.sleep(1)
        except ElementNotInteractableException:
            time.sleep(1)
            print("Get fans_info success")
        tbar.close()
        self.driver.close()
        return fans_info

    def save_fans(self, fans_info, db_path='fans.db'):
        """
        将粉丝信息储存进数据库之中
        :param fans_info: 包含粉丝昵称和个人简介的列表
        :param db_path: 数据库储存路径，默认为 fans.db
        :return: None
        """
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS
                    FANS
                    ( uid INT PRIMARY KEY NOT NULL,
                    name TEXT NOT NULL,
                    introduction TEXT NOT NULL);''')
        for fan_info in fans_info:
            cursor = c.execute("SELECT uid, name, introduction FROM FANS WHERE uid = ?", (fan_info[2],))
            fan = cursor.fetchall()
            if len(fan):
                c.execute("UPDATE FANS SET name = ? , introduction = ? WHERE uid = ?",
                          (fan_info[0], fan_info[1], fan[0][0]))
            else:
                c.execute("INSERT INTO FANS (uid, name, introduction) VALUES (?,?,?)",
                          (fan_info[2], fan_info[0], fan_info[1]))

            conn.commit()
        conn.close()
        print("save fans_info success")

    def get_cookies(self):
        """
        打开浏览器登录b站获取cookie
        :return: cookies
        """
        if self.is_headless:
            self.is_headless = False
            self.driver = self.get_driver()
        url = "https://passport.bilibili.com/account/security#/home"
        self.driver.get("https://passport.bilibili.com/login")
        while True:
            print("Please login in bilibili.com!")
            time.sleep(3)
            # if login in successfully, url  jump to www.bilibili.com
            while self.driver.current_url == url:
                Cookies = self.driver.get_cookies()
                self.driver.quit()
                cookies = {}
                for item in Cookies:
                    cookies[item['name']] = item['value']
                output_path = open('cookies.pickle', 'wb')
                pickle.dump(cookies, output_path)
                output_path.close()
                return cookies

    def read_cookies(self):
        """
        读取cookies
        :return: cookies
        """
        if os.path.exists('cookies.pickle'):
            read_path = open('cookies.pickle', 'rb')
            cookies = pickle.load(read_path)
        else:
            cookies = self.get_cookies()
        return cookies

    def login_by_cookies(self):
        """
        使用cookie登录b站，如cookie不存在，则要求登录获取cookie
        :return: None
        """
        cookies = self.read_cookies()

        self.driver.get("https://www.bilibili.com")
        for cookie in cookies:
            self.driver.add_cookie({
                "domain": ".bilibili.com",
                "name": cookie,
                "value": cookies[cookie],
                "path": '/',
                "expires": None
            })
        # time.sleep(0.5)
        self.driver.get("https://www.bilibili.com")
