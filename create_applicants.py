import requests
import os
import re
import pandas as pd
import time
from typing import List, Dict, Any, Tuple
import pprint

FOUNTAIN_URL = os.environ['FOUNTAIN_URL']
FOUNTAIN_TRUST_KEY = os.environ['FOUNTAIN_TRUST_KEY']
FOUNTAIN_API_KEY = os.environ['FOUNTAIN_API_KEY']

headers = {
    "accept": "application/json",
    "content-type": "application/son",
    "X-ACCESS-TOKEN": f"{ FOUNTAIN_API_KEY }"
}

EMAIL_VALIDATION = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_VALIDATION = re.compile(r'^\+?1?\d{10,15}$')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMPORT_FILE =  os.path.join(SCRIPT_DIR, "import_applicants_list.ods")

def read_file(filepath: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(filepath, engine="odf", dtype=str)
        print(f"Successfully read file")
        return df
    except Exception as e:
        print(f"Error reading file: {e}")

def validate_required_fields(row: pd.Series) -> tuple[bool, str]:
    required_fields = ["name", "email", "phone_number"]

    for field in required_fields:
        if field not in row or pd.isna(row[field]) or str(row[field]).strip() == '':
            return False, f"Missing required field: {field}"
    
    return True, ""

def validate_email(email: str) -> bool:
    return bool(EMAIL_VALIDATION.match(str(email).strip()))

def validate_phone(phone: str) -> bool:
    scrubbed = re.sub(r'[\s\-\(\)]', '', str(phone))
    return bool(PHONE_VALIDATION.match(scrubbed))

def validate_row(row: pd.Series) -> tuple[bool, str]:
    # Check required fields
    is_valid, error = validate_required_fields(row)
    if not is_valid:
        return False, error
    
    # Validate email
    if not validate_email(row['email']):
        return False, f"Invalid email format: {row['email']}"
    
    # Validate phone
    if not validate_phone(row['phone_number']):
        return False, f"Invalid phone format: {row['phone_number']}"
    
    return True, ""

def call_create_applicant_endpoint(applicant_data: Dict, retry_count: int = 0) -> Tuple[int, Dict, dict]:
    try:
        payload = {
            'name': applicant_data['name'],
            'email': applicant_data['email'],
            'phone': applicant_data['phone_number'],
            'check_if_applicant_is_duplicate': True 
        }
        
        print(payload)
        response = requests.post(
            FOUNTAIN_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        return response.status_code, response.json(), dict(response.headers)
    
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            backoff = 2 ** retry_count  # Exponential backoff
            print(f"Timeout occurred. Retry {retry_count + 1}/{MAX_RETRIES} after {backoff}s...")
            time.sleep(backoff)
            return call_create_applicant_endpoint(applicant_data, retry_count + 1)
        return 504, {'error': 'Max retries exceeded'}, {}
    
    except requests.exceptions.RequestException as e:
        print(f"Error calling endpoint: {e}")
        return 500, {'error': str(e)}, {}

def process_response(status_code: int, response_data: Dict, applicant_data: Dict) -> Dict:
    result = {
        'name': response_data.get('name', ''),
        'email': response_data.get('email', ''),
        'phone': response_data.get('phone', ''),
        'status_code': status_code,
        'key': response_data.get('key', ''),
        'is_duplicate': response_data.get('is_duplicate', ''),
        'stage': response_data.get('stage', {}).get('title'),
        'notes': ''
    }
    
    if status_code in [201, 200]:
        # Check for duplicate
        is_duplicate = response_data.get(data('is_duplicate',''), False)
        if is_duplicate:
            result['notes'] = 'Duplicate applicant found'
        else:
            result['notes'] = 'Applicant created successfully'
    
    elif 400 <= status_code < 500:
        result['notes'] = f'Client error: {response_data.get("error", "Unknown error")}'
    
    elif status_code == 500:
        result['notes'] = 'Internal server error: investigation'
    
    elif status_code in [503, 504]:
        result['notes'] = 'Max retries exceeded'
    
    else:
        result['notes'] = f'Unexpected error: {response_data.get("error", "Unknown")}'
    
    return result

def main():
    # Step 1: Read file
    print(f"Reading file: {IMPORT_FILE}")
    df = read_file(IMPORT_FILE)
    
    if df.empty:
        print("No data to process")
        return
    
    # Step 2: Process each row
    results = []
    invalid_rows = []
    last_response_headers = {}
    
    for index, row in df.iterrows():
        print(f"\nProcessing row {index + 1}/{len(df)}...")
        
        # Validate row data
        is_valid, error_message = validate_row(row)
        
        if not is_valid:
            print(f"Validation failed: {error_message}")
            invalid_rows.append({
                'row_number': index + 1,
                'name': row.get('name'),
                'email': row.get('email', ''),
                'phone': row.get('phone_number', ''),
                'notify_team': 'Some POC',
                'notes': error_message
            })
            continue
        
        # # Check rate limit before API call
        # if last_response_headers:
        #     check_rate_limit(last_response_headers)
        
        # Call API endpoint
        status_code, response_data, response_headers = call_create_applicant_endpoint(row.to_dict())
        last_response_headers = response_headers
        
        # Process response
        result = process_response(status_code, response_data, row.to_dict())
        results.append(result)
        
        print(f"Status: {status_code} - {result['notes']}")
        
        time.sleep(0.1)
    
    # # Combine valid and invalid results
    # all_results = results + invalid_rows
    
    
    # Summary
    print("\n" + "="*50)
    print("Pipeline complete!")
    print(f"Total rows processed: {len(df)}")
    print(f"Valid rows sent to API: {len(results)}")
    print(f"Invalid rows (validation failed): {len(invalid_rows)}")
    print("="*50)

if __name__ == "__main__":
    main()