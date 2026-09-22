import json
from pathlib import Path
import requests
from datetime import datetime
import os
import hashlib
import re
from dotenv import load_dotenv

env = Path(__file__).resolve().parent / ".env"
load_dotenv(env)

CACHE_FILE = Path(os.getenv("MARKDOWN_CONVERSION_FOLDER")) / "FILE_HASHES.json"
print(CACHE_FILE)

# Create the Cache File if it doesn't exist
if not CACHE_FILE.exists():
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        # Write an empty dictionary so that json.load() doesn't fail later
        json.dump({}, f)
    print(f"Initialized new cache file at: {CACHE_FILE}")
else:
    print(f"Using existing cache file at: {CACHE_FILE}")

# Loads the cache json file
def load_hash_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            print("There was an error finding the cache file.")
            return {}
    return {}

# Load pre-exisiting hashes
hash_cache = load_hash_cache()
existing_hashes = set(hash_cache.values()) # Adds pre-exisiting hashes to shorten time and computational resources

# Saves the content to the json file
def save_hash_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=4)


# Creates a name for a JSON note utilizing AI model
def generate_name(note):
    clean_note = {}
    try:
        clean_note = {
                "title": note["title"],
                "text": note["textContent"],
                "created": note["createdTimestampUsec"],
                "modified": note["userEditedTimestampUsec"]
        }
    except Exception:
        print(Exception)
        try:
            # Handle the case where there is a list instead of text
            clean_note = {
                            "title": note["title"],
                            "text": note["listContent"],
                            "created": note["createdTimestampUsec"],
                            "modified": note["userEditedTimestampUsec"]
            }
        except Exception:
            print(Exception)            
    # print(clean_note)
    

    # Check for duplicate content (regardless of name)
    # Convert list data to string data
    if isinstance(clean_note['text'], list):
        clean_note_list_as_string = "\n".join(map(str, clean_note['text'])) # Convert ['a', 'b'] -> "a\nb" (joins with newlines)
        new_content_hash = get_content_hash(clean_note_list_as_string)
    else:
        new_content_hash = get_content_hash(clean_note['text'])
    if new_content_hash in existing_hashes:
        print(f"Skipped: A note with this exact content already exists (regardless of name)(0).")
        return False
        #return {}
    
    # Prompt to send to the model
    prompt = f"""
    Generate a short descriptive title for this note.

    Return ONLY the title.
    Do not include quotes, "title:", or any other text.

    Note:
    {clean_note['text']}
    """

    # Makes a request to the ollama localhost.
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "gemma3:4b", # I also have gemma-4-26b-a4b
            "prompt": prompt,
            "stream": False # Ollama waits until the entire response is finished before sending back the JSON Object
        }
    )
    result = response.json()

    # Converts the response to a stripped string
    bot_response = result["response"]
    print(result["response"])

    title = bot_response
    #title = bot_response.split('"')[1]
    #print(title)

    # Takes the created time provided by the JSON and converts it to something readable
    timestamp = clean_note["created"] / 1_000_000
    created_date = datetime.fromtimestamp(timestamp)
    date_string = created_date.strftime("%Y-%m-%d")

    # Joins the date with the AI generated name.
    filename = f"{date_string} - {title}.md"
    print(filename)
    return(filename)

# Creates a unique SHA-256 fingerprint for a string to check content later for fast comparison
def get_content_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# Saves a note to a folder if its unique in name and in content
def save_note_if_unique(new_name, content, target_directory):
    # Ensure the target folder exists
    if not os.path.exists(target_directory):
        check = True
        while (check):
            user_choice = input(f"Directory '{target_directory}' does not exist. Create it? [Y/N]: ").strip().lower()
            if user_choice in ['y', 'yes']:
                os.makedirs(target_directory)
                print(f"Created directory: {target_directory}")
                check = False
            elif user_choice in ['n', 'no']:
                print("Operation cancelled: Directory was not created.")
                return False # Exits the entire program
            else:
                print("Please enter a valid answer!")

    # Prepare Hashing
    # Convert list data to string data
    if isinstance(content, list):
        content = "\n".join(map(str, content)) # Convert ['a', 'b'] -> "a\nb" (joins with newlines)
        new_content_hash = get_content_hash(content)
    else:
        new_content_hash = get_content_hash(content)
    #existing_hashes = set(hash_cache.values()) # Adds pre-exisiting hashes to shorten time and computational resources
    existing_filenames = set()

    # Scan exisiting files
    for filename in os.listdir(target_directory):
        # Add the files in the folder to the list of existing files
        existing_filenames.add(filename)

        # Track to see if there is duplicate naming
        file_path = os.path.join(target_directory, filename)
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_hashes.add(get_content_hash(f.read()))
            except Exception:
                pass # Skip unreadable files

    # Check for duplicate content (regardless of name)
    if new_content_hash in existing_hashes:
        print(f"Skipped: A note with this exact content already exists (regardless of name) (1).")
        return False

    new_name_string = str(new_name)
    # Check for duplicate names and generate a new name
    base_name, extension = os.path.splitext(new_name_string)
    if not extension:
        extension = ".md"

    final_filename = new_name_string if new_name_string.endswith(extension) else f"{new_name_string}{extension}"

    # If the name is taken, loop until we find a free one
    counter = 1
    while final_filename in existing_filenames:
        final_filename = f"{base_name}_{counter}{extension}"
        counter += 1

    # Clean the filename
    final_filename = final_filename.strip()
    final_filename = re.sub(r'[\n\r\t]', '', final_filename)
    final_filename = re.sub(r'[<>:"/\\|?*]', '', final_filename)
                            
    # Write the file
    new_file_path = os.path.join(target_directory, final_filename)
    with open(new_file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Success: Created '{final_filename}'")
    return True



# Main loop
i = 0
keep_notes_folder = Path(os.getenv("GOOGLE_KEEP_NOTES"))
for note in keep_notes_folder.glob("*.json"):
    with open(note, "r", encoding="utf-8") as file:
        json_note = json.load(file)
        print("file: ", file.name)
        new_filename = generate_name(json_note)
        print(new_filename)

        try:
            json_note["textContent"]
            save_note_if_unique(new_filename, json_note["textContent"], os.getenv("MARKDOWN_CONVERSION_FOLDER"))
        except Exception:
            print(Exception)
            # Handle the case where there is a list instead of text
            json_note["listContent"]
            save_note_if_unique(new_filename, json_note["listContent"], os.getenv("MARKDOWN_CONVERSION_FOLDER"))

        
    # print(note)
    #i += 1
    #if i >= 10: # Limits the run to 10 notes
    #    break
    


