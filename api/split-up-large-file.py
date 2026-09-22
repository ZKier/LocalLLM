import re
import json
from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import datetime

# Environment
env = Path(__file__).resolve().parent / ".env"
load_dotenv(env)

# The input data
keep_notes_folder = Path(os.getenv("GOOGLE_KEEP_NOTES"))
note = keep_notes_folder / "Chores Notes.json"
with open(note, "r", encoding="utf-8") as file:
    json_note = json.load(file)

# 1. Extract the text content
input_data = json_note

# 2. CONFIGURATION
output_folder = keep_notes_folder  # The folder where your new files will go

# Create the folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

def date_to_usec(date_str):
    """
    Converts a string like '10/9/25' to a Unix Microsecond Timestamp.
    """
    try:
        # Parse the date string (matches MM/DD/YY format from your data)
        dt = datetime.strptime(date_str, "%m/%d/%y")
        
        # Convert to unix timestamp (seconds since 1970)
        # multiply by 1,000,000 to get microseconds
        return int(dt.timestamp() * 1000000)
    except ValueError:
        # Fallback if date parsing fails
        return 0

def split_json_to_files(data, folder):
    # Extract text and keep metadata
    text = data.pop("textContent")
    metadata = data # This now contains only the metadata keys
    
    # Regex to find the start of a new date block
    # It looks for a newline followed by a date pattern
    pattern = r'\n(?=\d{1,2}/\d{1,2}/\d{2})'
    chunks = re.split(pattern, text)
    
    count = 0

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
            
        # --- Create the new object ---
        new_entry = metadata.copy()
        new_entry["textContent"] = chunk

        # 1. Find the date within the text chunk
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2})', chunk)
        
        if date_match:
            date_str = date_match.group(1)
            
            # 2. Generate the new timestamp field
            new_entry["createdTimestampUsec"] = date_to_usec(date_str)
            
            # 3. Prepare filename (replace / with - for valid filename)
            file_date = date_str.replace('/', '-')
        
        # --- Generate a Filename from the date in the text ---
        # We look for the first pattern of XX/XX/XX in the chunk
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2})', chunk)
        if date_match:
            # Replace slashes with dashes so it's a valid filename (e.g., 10-9-25.json)
            file_date = date_match.group(1).replace('/', '-')
        else:
            file_date = f"unknown_date_{count}"

        filename = f"PYTHON_GENERATED{file_date}.json"
        filepath = os.path.join(folder, filename)

        # --- Write the file ---
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(new_entry, f, indent=4)
        
        print(f"Created: {filepath}")
        count += 1

    print(f"\nSuccess! Created {count} files in '{folder}/'")

# Run the function
split_json_to_files(input_data, output_folder)