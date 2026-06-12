"""
One-time script: generates all-MiniLM-L6-v2 embeddings for all sp500_embeddings rows
and writes them back to Supabase.
"""
import os
from sentence_transformers import SentenceTransformer
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
BATCH_SIZE = 50

def main():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # Fetch all rows
    result = client.table("sp500_embeddings").select("ticker, name, sector, summary").execute()
    rows = result.data or []
    print(f"Generating embeddings for {len(rows)} companies...")

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        texts = [f"{r['name']} — {r['sector']}. {r['summary']}" for r in batch]
        embeddings = model.encode(texts, normalize_embeddings=True)

        for row, emb in zip(batch, embeddings):
            client.table("sp500_embeddings").update(
                {"embedding": emb.tolist()}
            ).eq("ticker", row["ticker"]).execute()

        print(f"  [{i + len(batch)}/{len(rows)}] done")

    print("All embeddings generated and stored.")

if __name__ == "__main__":
    main()
