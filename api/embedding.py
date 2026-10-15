import os
import requests
import psycopg
from pathlib import Path
from dotenv import load_dotenv

# Organize the environment
env = Path(__file__).resolve().parent / ".env"
load_dotenv(env)

# Generate a connection to the postgresql database
conn = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
)

# Pull data from PostgreSQL
with conn:
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, content
            FROM document_chunks
            WHERE embedding IS NULL
            ORDER BY id;
        """)

        rows = cursor.fetchall() # runs the cursor.execute and returns all of the retrieved data to a list of tuples
        count = 0
        for chunk_id, content in rows:
            #print(chunk_id, ": " ,content[:100])
            # Run content through the embedding model
            response = requests.post(
                "http://localhost:11434/api/embed",
                json={
                    "model": "nomic-embed-text",
                    "input": content
                }
            )
            embedding = response.json()["embeddings"][0]

            # Place the data back into PostgreSQL
            cursor.execute("""
                UPDATE document_chunks
                SET embedding = %s
                WHERE id = %s;
            """, (embedding, chunk_id))

            print(f"Embedded chunk ID: {chunk_id}")

            # Commits changes every 10 chunks to reduce data loss
            count += 1
            if count >= 10:
                conn.commit()
                print("Commited 10 Embedded Chunks!")
                count = 0

        conn.commit()

