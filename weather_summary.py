import requests
import csv
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

def fetch_weather_data():
    url = "https://api.open-meteo.com/v1/forecast?latitude=9.07&longitude=7.40&" \
    "daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max&" \
    "timezone=Africa%2FLagos&past_days=7"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print("Network error - could not reach the Open-Meteo API")
        return None
    except requests.exceptions.Timeout:
        print("Request timed out - the API took too long to respond")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"API returned an error: {e}")
        return None

def parse_weather_response(raw_data):
    try:
        daily = raw_data["daily"]
        dates = daily["time"]
        temp_max = daily["temperature_2m_max"]
        temp_min = daily["temperature_2m_min"]
        precipitation = daily["precipitation_sum"]
        wind = daily["wind_speed_10m_max"]
    except KeyError as e:
        print(f"API response is missing an expected field: {e}")
        return []
    
    records = []

    for i in range(len(dates)):
        record = {
            "date" : dates[i],
            "temp_max" : temp_max[i],
            "temp_min" : temp_min[i],
            "precipitation" : precipitation[i],
            "wind" : wind[i]
        }
        records.append(record)
    return records

def save_to_csv(records, filename):
    try: 
        with open(filename, "w", newline="") as csvfile:
            fieldnames = ["date", "temp_max", "temp_min", "precipitation", "wind"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(record)
        print(f"Data saved to: {filename}")
    except OSError as e:
        print(f"Failed to write CSV file: {e}")

def format_summary(daily_records):
    if not daily_records:
        return "No weather data available to summarize."
    highest_temp = float("-inf")
    lowest_temp = float('inf')
    total_precip = 0
    total_wind = 0
    date_of_highest_temp = ""
    date_of_lowest_temp = ""

    for record in daily_records:
        temp_max = float(record["temp_max"])
        temp_min = float(record["temp_min"])
        precip = float(record["precipitation"])
        wind = float(record["wind"])
        date = record["date"]
        
        if temp_max > highest_temp:
            highest_temp = temp_max
            date_of_highest_temp = date
            
        if temp_min < lowest_temp:
            lowest_temp = temp_min
            date_of_lowest_temp = date

        total_precip += precip
        total_wind += wind

    average_wind = total_wind / len(daily_records) if daily_records else 0

    summary = (
        f"Weather Summary - Last 7 Days\n"
        f"{'='*35}\n"
        f"Highest Temperature: {highest_temp}°C on {date_of_highest_temp}\n"
        f"Lowest Temperature: {lowest_temp}°C on {date_of_lowest_temp}\n"
        f"Total Precipitation: {total_precip} mm\n"
        f"Average Wind Speed: {average_wind:.1f} km/h\n"
    )
    return summary

def send_email(summary, attachment_path):

    load_dotenv()

    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
    APP_PASSWORD = os.getenv("APP_PASSWORD")

    content = (f"Below is the Weather Summary for the last 7 days:"
            f"\n\n{summary}\nPlease find the requested file attached."
            )

    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = "Weather Data Summary"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    try:
        with open(attachment_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="text",
                subtype="csv",
                filename=attachment_path
            )
    except OSError as e:
        print(f"Failed to read file {attachment_path}: {e}")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully.")   
    except smtplib.SMTPAuthenticationError:
        print("Authentication failed - check your email and app password in .env")
    except smtplib.SMTPException as e:
        print(f"Failed to send email: {e}")
    except KeyboardInterrupt:
        print("Send interrupted - connection was cut during transmission")

def main():
    raw_data = fetch_weather_data()
    if not raw_data:
        print("No data fetched. Exiting.")
        return
    
    records = parse_weather_response(raw_data)
    if not records:
        print("Failed to parse weather data. Exiting.")
        return
    
    save_to_csv(records, "weather_data.csv")
    summary = format_summary(records)    
    send_email(summary, attachment_path="weather_data.csv")

if __name__ == "__main__":
    main()
