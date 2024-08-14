from flask import Flask, render_template
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time

app = Flask(__name__)

# User credentials
username = os.getenv('username')
password = os.getenv('password')
login_url = 'https://reporting.smg.com/index.aspx'
my_score_url = 'https://reporting.smg.com/dashboard.aspx?id=4'

# Email settings
email_subject = "Bhai laude lag gaye"
email_body = "The score has fallen to or below 50%. Please check the SMG360 dashboard for details."

def send_email(to_emails, subject, body):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587  # TLS
    smtp_user = os.getenv('smtp_user')
    smtp_password = os.getenv('smtp_password')
    
    for email in to_emails:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, email, msg.as_string())
            print(f"Email sent successfully to {email}.")
        except Exception as e:
            print(f"Error sending email to {email}: {e}")

def monitor_score():
    while True:
        driver = webdriver.Chrome()  # Ensure you have the Chrome WebDriver installed
        driver.get(login_url)

        driver.find_element(By.ID, 'ctl00_cphMain_txtUserName').send_keys(username)
        driver.find_element(By.ID, 'ctl00_cphMain_txtPassword').send_keys(password)
        driver.find_element(By.ID, 'smg360LoginButton').click()

        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, 'ctl00_cphMain_rblSelections_0')))
            radio_button = driver.find_element(By.ID, 'ctl00_cphMain_rblSelections_0')
            driver.execute_script("arguments[0].scrollIntoView();", radio_button)
            driver.execute_script("arguments[0].click();", radio_button)
            submit_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, 'ctl00_cphMain_BtnSubmit')))
            submit_button.click()
        except TimeoutException:
            print("Error: Element not found or not interactable within the given time.")
            driver.save_screenshot('timeout_error.png')
            driver.quit()
            continue

        driver.get(my_score_url)

        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'donut-knob-container')))
            container_div = driver.find_element(By.CLASS_NAME, 'donut-knob-container')
            center_label = container_div.find_element(By.ID, 'CenterLabel')
            score_text = center_label.text
            print(f"Raw Score Text: '{score_text}'")
            
            try:
                score = int(score_text.replace('%', '').strip())
                print(f"Score: {score}")
                
                if score <= 50:
                    with open('email.txt', 'r') as file:
                        to_emails = [line.strip() for line in file]
                    send_email(to_emails, email_subject, email_body)
            except ValueError:
                print("Score value is not in the expected format.")
        except TimeoutException:
            print("Error: Div with class 'donut-knob-container' not found within the given time.")
            driver.save_screenshot('div_error.png')
        
        driver.quit()
        time.sleep(3600)  # Wait for 1 hour before checking again

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    threading.Thread(target=monitor_score).start()
    app.run(host='0.0.0.0', port=5000)
