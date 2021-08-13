from bilibilicrawler import BilibiliCrawler

bc = BilibiliCrawler()
bc.login_by_cookies()
fans_info = bc.get_fans_info()
bc.save_fans(fans_info)


