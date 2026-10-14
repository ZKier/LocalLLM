from pathlib import Path
from dotenv import load_dotenv
import os
from nltk.tokenize import sent_tokenize
from transformers import AutoTokenizer
import pymupdf
import psycopg

# Calculate 1/16th of the max context window
GEMMA3_CONTEXT_WINDOW = 131072
SIXTEENTH_CONTEXT_WINDOW = GEMMA3_CONTEXT_WINDOW // 16

# Environment
env = Path(__file__).resolve().parent / ".env"
load_dotenv(env)

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


# The input data (Should be the converted markdown data)
markdown_conversions = Path(os.getenv("MARKDOWN_CONVERSION_FOLDER"))

# Connect to the postgreSQL database
conn = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
)

# Detamine the chunk size to be text of 8192 * 4 characters or less
chunk_size = 8192 * 4

# Add all of the chunks and the file they originate from to the database
with conn:
    with conn.cursor() as cursor:
        for index, note in enumerate(markdown_conversions.glob("*.md")):
            # Converts the markdown into a string
            text = note.read_text(encoding="utf-8") 

            # Separate the chunks
            chunks = [
            text[i:i + chunk_size]
            for i in range(0, len(text), chunk_size)
            ]

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                id BIGSERIAL PRIMARY KEY,
                source_file TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (source_file, chunk_index)
                );
                """
            )
            for chunk_index, chunk in enumerate(chunks):
                cursor.execute(
                    """
                    INSERT INTO document_chunks
                        (source_file, chunk_index, content)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (source_file, chunk_index)
                    DO UPDATE SET content = EXCLUDED.content
                    """,
                    (note.name, chunk_index, chunk)
                )
            
            print(f"index: {index} Length: {len(chunks)}")
            #if (index == 74):
                #print(calculated_data)
                #continue
                #break
conn.close()

    
'''
# The input data (Should be the converted markdown data)
principals_of_neuroscience = Path(os.getenv("BOOK_FOLDER"))
for index, note in enumerate(principals_of_neuroscience.glob("*.pdf")):

    with pymupdf.open(note) as document:
        text = "\n\n".join(
            page.get_text("text")
            for page in document
        )

    # Splits the text into chunks of about 8192 characters
    chunk_size = 8192
    chunks = [
    text[i:i + chunk_size]
    for i in range(0, len(text), chunk_size)
    ]

    print(f"index: {index} Length: {len(chunks)}")

'''
    # Pump the chunks into the database
