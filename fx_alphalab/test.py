from transformers import pipeline
import time

pipe = pipeline("text-classification", model="ProsusAI/finbert",
                top_k=None, device=-1)

texts = ["EUR/USD rises strongly amid ECB hawkish tone"] * 100
start = time.time()
pipe(texts, batch_size=32)
print(f"100 textes en {time.time()-start:.1f}s")