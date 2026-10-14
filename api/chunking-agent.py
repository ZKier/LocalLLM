# Building an AI driven chunking engine

# I want to build a printer-like logic. 
# I want the chunking agent to first split the file into portions of 
# 50% max context window size. 
# I then want the agent to read the file, 
# determine the first chunk's recommended size, 
# then I want it to combine the remainder of the file, 
# then repeat the above steps on the remainder of the file 
# until there is no more content remaining in the file.

from pathlib import Path
from dotenv import load_dotenv
import nltk
from nltk.tokenize import sent_tokenize
import requests
import os
from transformers import AutoTokenizer
import json

# Calculate 1/16th of the max context window
GEMMA3_CONTEXT_WINDOW = 131072
SIXTEENTH_CONTEXT_WINDOW = GEMMA3_CONTEXT_WINDOW // 16

# Environment
env = Path(__file__).resolve().parent / ".env"
load_dotenv(env)

# Function: Split document into blocks based on new line with maximum of 
# Split the text into one-sixteeth of the max context window (I should actually automate this step based on any model but I'm lazy rn)

# Document Pre=processing step utilizing the natual language tool-kit
#nltk.download("punkt")
#nltk.download("punkt_tab")

# Splits the document into sentences using the NLTK
def preprocess(text: str) -> list[str]:
    sentences = sent_tokenize(text)
    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]
# Numbers the sentences for the LLM to read, thus improving automated processing and preventing data contamination.
def number_blocks(blocks: list[str]) -> str:
    return "\n".join(
        f"[{i}] {block}"
        for i, block in enumerate(blocks)
    )

# Tokenizes the data
tokenizer = AutoTokenizer.from_pretrained(
    "nomic-ai/nomic-embed-text-v1.5"
)

# Helper function to determine token count
def token_count(blocks: list[str]) -> int:
    text = "\n".join(blocks)

    return len(
        tokenizer.encode(
            text,
            add_special_tokens=False
        )
    )

# Helper function to determine the amount of blocks that will max out the desired context window.
def blocks_within_token_limit(
    blocks: list[str],
    max_tokens: int
) -> list[str]:

    batches = []
    current_batch = []

    for block in blocks:
        candidate = current_batch + [block]

        if token_count(candidate) > max_tokens:
            if current_batch:
                batches.append(current_batch)

            current_batch = [block]
        else:
            current_batch.append(block)

    if current_batch:
        batches.append(current_batch)

    return batches

# Function: Utilize AI to make decisions about how large the chunks should be
def determine_chunk_sizing(file):
    text = file.read_text(encoding="utf-8") # Converts the markdown into a string

    data = preprocess(text) # Converts the string into a list
    number_of_blocks = number_blocks(data) # Numbers the strings in the list

    # Returns batches of data from the file that are max length of 1/16th context window
    calculated_data = blocks_within_token_limit(number_of_blocks, SIXTEENTH_CONTEXT_WINDOW) # it needs to be looped and updated...

    print("lenth of calculated data:", len(calculated_data))
    print(number_of_blocks)
    #print(calculated_data)
    chunks = []
    for iteration_of_data in calculated_data:
        # Prompt to send to the model
        prompt = f"""
        Group the numbered Markdown blocks below into semantically coherent chunks.

        Rules:
        - Return only valid JSON.
        - Refer to blocks only by their numeric IDs.
        - Every block must belong to exactly one chunk.
        - Blocks must remain in their original order.
        - A chunk may contain only consecutive blocks.
        - Prefer existing Markdown heading boundaries.
        - Do not reproduce the source text.
        - Do not omit any blocks.

        - Prefer larger, context-rich chunks. 
        - Do not create a new chunk merely because a paragraph introduces a slightly different point. 
        - Keep related arguments, examples, explanations, reflections, and supporting details together. 
        - Create a boundary only when the text meaningfully transitions to a new topic or independent thought.

        Return:

        {{
        "chunks": [
            {{
            "start_block": 0,
            "end_block": 3,
            "topic": "Short topic description"
            }}
        ]
        }}

        BLOCKS:
        {iteration_of_data}
        """
        # Makes a request to the ollama localhost.
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma3:4b",
                "prompt": prompt,
                "stream": False # Ollama waits until the entire response is finished before sending back the JSON Object
            }
        )
        '''
        # Remove Markdown code fences
        response = response.json()

        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        # Convert JSON string to Python dictionary
        response = json.loads(response.strip())
        '''
        result = response.json()
        response = result["response"]
        # Remove Markdown code fences
        response = response.strip()
        response = response.removeprefix("```json")
        response = response.removesuffix("```")

        # Convert JSON string into dictionary
        try:
            parsed = json.loads(response.strip())

        except json.JSONDecodeError as e:
            print(f"JSON Error: {e}")
            print(f"Line: {e.lineno}, Column: {e.colno}")

            print("Problematic section:")
            print(repr(response[max(0, e.pos - 100):e.pos + 100]))

            raise

        # Add chunks to your list
        chunks.extend(parsed["chunks"]) 

        # Add the chunks to your list
        #chunks.extend(response["chunks"])
        #result = response.json()
        #print(result)
        #chunks += result["response"].json()
    
    print(result["response"])
    print(chunks)
    return chunks
    #return (result["response"])

# The input data (Should be the converted markdown data)
markdown_conversions = Path(os.getenv("MARKDOWN_CONVERSION_FOLDER"))
for note in markdown_conversions.glob("*.md"):
    with open(note, "r", encoding="utf-8") as file:
        #json_note = json.load(file)


        # Parse the file and return the points at which the chunks start and end
        # This should be a recusive function
        determine_chunk_sizing(note)
        # Utilize AI to make decisions about how large the chunks should be
        break
        # Track chunked data (so add data that has already been parsed and completed to a list)

        # Write the chunks to new files labeled (File) - (Chunk number).md


