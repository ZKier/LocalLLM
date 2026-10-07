import requests
text = "I am building a personal AI assistant using PostgreSQL and pgvector."

response = requests.post(
    "http://localhost:11434/api/embed",
    json={
        "model": "nomic-embed-text",
        "input": text
    }
)

embedding = response.json()["embeddings"][0]

print(embedding)
print("Dimensions:", len(embedding))