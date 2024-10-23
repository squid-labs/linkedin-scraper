from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import urllib
import csv
import time
import uuid

total_job_posts_scraped = 0

location_data = {
    'greater kuala lumpur': {
        'geo_id': '90010064',
        'long_name': 'Greater Kuala Lumpur, Malysia'
    },
    'malaysia': {
        'geo_id': '106808692',
        'long_name': 'Malaysia'
    }
}

def login(browser):
    elem = browser.find_element('id','username')
    elem.send_keys('')

    elem = browser.find_element('id','password')
    elem.send_keys('')
    elem.submit()

def get_total_num_pages(browser):
    try:
        pagination_section = browser.find_element(By.XPATH, '/html/body/div[6]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div/div[4]/ul')
        list_elements = pagination_section.find_elements(By.TAG_NAME, 'li')
        #element=list_elements.find_element(By.CSS_SELECTOR, 'li[data-test-pagination-page-btn="' + (len(list_elements)-1) + '"]')
        
        val1=str(len(list_elements))
        a='/html/body/div[6]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div/div[4]/ul/li['+val1+ ']/button/span'
        val2=list_elements[len(list_elements)-1].find_element(By.XPATH, a).get_attribute("innerHTML")

        #total_num_pages = int(list_elements[len(list_elements)-1].text)
        total_num_pages = int(val2)
        return total_num_pages
    except TimeoutException:
        print('failed to find total number of pages')
        return 1

def scrape_page(jobs_on_page, browser, csvwriter):
    global total_job_posts_scraped
    for job in jobs_on_page:
        # one second delay to prevent too many requests error (HTTP code 429)
        time.sleep(1)
        try:
            job.click()
        except WebDriverException as error:
            print('click failed, skipping job post:', error)
            continue
        try:
            company_name = job.find_element(By.CLASS_NAME,'job-card-container__primary-description').get_attribute('innerText')
            print('company_name:', company_name)

            job_title = job.find_element(By.CLASS_NAME, 'job-card-list__title').get_attribute('innerText')
            print('job_title:', job_title)

            location = job.find_element(By.CSS_SELECTOR, 'ul.job-card-container__metadata-wrapper').get_attribute('innerText').replace('\n', ' ')
            print('location:', location)

            description = browser.find_element(By.CSS_SELECTOR, '#job-details > div > p').get_attribute('innerText')

            data = [uuid.uuid4().hex, company_name, job_title, location, description]
            csvwriter.writerow(data)
            total_job_posts_scraped += 1
            print('Total job posts scraped:', total_job_posts_scraped, end='\n\n')
        except Exception as error:
            print('failed to process job post, skipping:', error)
            time.sleep(1)
            continue

def main():
    chrome_service = Service(executable_path='/usr/bin/chromedriver')
    browser = webdriver.Chrome(service=chrome_service)
    browser.implicitly_wait(10)

    login_link = 'https://www.linkedin.com/checkpoint/rm/sign-in-another-account?fromSignIn=true&trk=guest_homepage-basic_nav-header-signin'
    browser.get(login_link)
    login(browser)

    search_job_title = 'machine learning engineer'
    search_location = 'malaysia'

    url_root = 'https://www.linkedin.com/jobs/search?geoId='
    job_posts_url = urllib.parse.quote(url_root
                             + location_data[search_location]['geo_id']
                             + '&keywords=' + search_job_title 
                             + '&location=' + location_data[search_location]['long_name'],
                             safe='/:?=&')

    browser.get(job_posts_url)
    time.sleep(3) # wait for the jobs page to load

    csvfile = open('linkedin-scraped-data1.csv', 'w')
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(['ID', 'Company', 'Job Title', 'Location', 'Description'])

    num_pages = get_total_num_pages(browser)
    print('num pages:', num_pages)

    consecutive_error_count = 0
    for page_num in range(1, num_pages + 1):
        jobs_on_page = browser.find_elements(By.CSS_SELECTOR,'li.jobs-search-results__list-item')
        time.sleep(2)

        scrape_page(jobs_on_page, browser, csvwriter)

        if page_num < num_pages:
            try:
                next_page_element = browser.find_element(By.XPATH, '//li/button[@aria-label="Page {}"]'.format(page_num + 1))
                next_page_element.click()
                print('clicked page {}'.format(page_num + 1))
                consecutive_error_count = 0
            except Exception as error:
                print('failed to find or click next page link:', error)
                consecutive_error_count += 1
                if consecutive_error_count > 2:
                    print('too many errors, script exiting...')
                    break
                else:
                    print('error, skipping page...')
                    continue

    csvfile.close()

if __name__ == '__main__':
    main()
