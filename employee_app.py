#app.py
import json
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
import time
from zk import ZK
from local_config import devices, SHIFT, START_DATE, END_DATE,ERPNEXT_URL,ERPNEXT_API_KEY,ERPNEXT_API_SECRET

# Function to fetch biometric data from a device
def fetch_biometric_data(ip, port=4370, timeout=180):
    zk = ZK(ip, port=port, timeout=timeout)
    conn = None
    attendances = []
    try:
        conn = zk.connect()
        attendances = conn.get_attendance()
        print(f"Fetched {len(attendances)} attendance records from {ip}")
    except Exception as e:
        print(f"Error fetching data from device at {ip}: {e}")
    finally:
        if conn:
            conn.disconnect()
    return [attendance.__dict__ for attendance in attendances]


# Fetch employee data from ERPNext
def fetch_employee_data():
    base_url = ERPNEXT_URL
    endpoint = 'api/resource/Employee'
    url = base_url + endpoint

    headers = {
        'Authorization': f'token {ERPNEXT_API_KEY}:{ERPNEXT_API_SECRET}'
    }

    session = requests.Session()
    retry = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    limit_start = 0
    limit_page_length = 1000
    all_data = []

    while True:
        params = {
            'fields': '["employee","employee_name","attendance_device_id"]',
            'limit_start': limit_start,
            'limit_page_length': limit_page_length
        }

        try:
            response = session.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            if 'data' in data:
                so_data = data['data']
                if not so_data:
                    break
                all_data.extend(so_data)
                limit_start += limit_page_length
            else:
                break

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            break

    if all_data:
        emp_df = pd.json_normalize(all_data)
    else:
        columns = ["employee", "employee_name", "attendance_device_id"]
        emp_df = pd.DataFrame(columns=columns)

    return emp_df


def process_and_merge_biometric_with_employee_data(devices, shift_index):
    device = devices[shift_index % len(devices)]
    shift = SHIFT[shift_index % len(SHIFT)]

    # Try to fetch biometric data for the current device
    try:
        device_data = fetch_biometric_data(device['ip'])
    except Exception as e:
        print(f"Skipping device {device['device_id']} with shift {shift} due to error: {e}")
        return None  # Return None to indicate that this device should be skipped

    # If no biometric data was fetched, skip processing this device
    if not device_data:
        print(f"No data fetched from device {device['device_id']} with shift {shift}. Skipping.")
        return None  # Return None to skip this device

    # Add shift info to the fetched data
    for attendance in device_data:
        attendance['shift'] = shift

    # Create DataFrame from the device data
    df = pd.DataFrame(device_data)
    
    # Ensure the column 'attendance_device_id' exists after renaming
    if 'user_id' in df.columns:
        df.rename(columns={'user_id': 'attendance_device_id'}, inplace=True)
    else:
        print(f"Skipping device {device['device_id']} with shift {shift} as 'user_id' not found in data.")
        return None  # Return None if 'user_id' is missing

    # Fetch employee data from ERP
    emp_df = fetch_employee_data()

    # Merge the two DataFrames on 'attendance_device_id'
    result_df = pd.merge(df, emp_df, on='attendance_device_id', how='left')

    # Filter by the date range
    start_date = pd.to_datetime(START_DATE)
    end_date = pd.to_datetime(END_DATE)
    result_df['timestamp'] = pd.to_datetime(result_df['timestamp'])
    filtered_df = result_df[(result_df['timestamp'] >= start_date) & (result_df['timestamp'] <= end_date)]

    return filtered_df


def push_data_to_erp(df, max_retries=2):
    base_url = ERPNEXT_URL
    endpoint = 'api/resource/Employee Checkin'
    headers = {
        'Authorization': f'token {ERPNEXT_API_KEY}:{ERPNEXT_API_SECRET}',
        'Content-Type': 'application/json'
    }

    for index, row in df.iterrows():
        if pd.isnull(row['employee']):
            print("Skipping row with NaN employee")
            continue

        employee = row['employee']
        time_str = row['timestamp'].isoformat() 
        payload = {
            "employee": employee,
            "time": time_str,
            "shift": row['shift']
        }

        json_payload = json.dumps(payload)

        retry_count = 0
        success = False
        while retry_count < max_retries and not success:
            try:
                response = requests.post(f"{base_url}{endpoint}", headers=headers, data=json_payload)
                
                if response.status_code in [200, 201]:
                    print(f"Successfully added data for {employee}")
                    success = True
                else:
                    print(f"Failed to add data for {employee}. Status code: {response.status_code}. Retrying...")
                    retry_count += 1
                    time.sleep(2) 

            except requests.exceptions.RequestException as e:
                print(f"Request failed for {employee}. Error: {e}.  Retrying...")
                retry_count += 1
                time.sleep(2) 

        if not success:
            print(f"Failed to push data for {employee} after {max_retries} retries. Skipping this row.")

    return True


# def main_loop():
#     shift_index = 0

#     while True:
#         print(f"Processing device {devices[shift_index % len(devices)]['device_id']} with shift {SHIFT[shift_index % len(SHIFT)]}")

#         filtered_df = process_and_merge_biometric_with_employee_data(devices, shift_index)

#         if filtered_df is None or filtered_df.empty:
#             print(f"Skipping device {devices[shift_index % len(devices)]['device_id']} and shift {SHIFT[shift_index % len(SHIFT)]} due to data fetch issues.")
#             shift_index += 1
#             time.sleep(5)
#             continue 
#         filtered_df = filtered_df.head(5)

#         print(filtered_df)
#         print(len(devices))

#         push_data_to_erp(filtered_df)

#         shift_index += 1
#         time.sleep(5) 


def main_loop():
    shift_index = 0

    while True:
        if shift_index >= len(devices):
            print("Process Completed.")
            break

        print(f"Processing device {devices[shift_index % len(devices)]['device_id']} with shift {SHIFT[shift_index % len(SHIFT)]}")

        filtered_df = process_and_merge_biometric_with_employee_data(devices, shift_index)

        if filtered_df is None or filtered_df.empty:
            print(f"Skipping device {devices[shift_index % len(devices)]['device_id']} and shift {SHIFT[shift_index % len(SHIFT)]} due to data fetch issues.")
            shift_index += 1
            time.sleep(5)
            continue 

        filtered_df = filtered_df.head(5)

        print(filtered_df)

        push_data_to_erp(filtered_df)

        shift_index += 1
        time.sleep(5)


if __name__ == "__main__":
    main_loop()
