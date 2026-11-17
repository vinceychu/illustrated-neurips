"""Embed the corpus with bge-small (the model the browser and the chat Worker load, CLS pooling).
Usage: embed.py corpus.json out_prefix   -> out_prefix.npy (float32, normalized), out_prefix.json (corpus copy)"""
import json, sys, numpy as np
from sentence_transformers import SentenceTransformer
P = json.load(open(sys.argv[1])); out = sys.argv[2]
m = SentenceTransformer('BAAI/bge-small-en-v1.5')
E = m.encode([p['t'] + '. ' + p['ab'] for p in P], batch_size=64, show_progress_bar=False, normalize_embeddings=True)
np.save(out + '.npy', E.astype(np.float32)); json.dump(P, open(out + '.json', 'w'), ensure_ascii=False)
print(len(P), E.shape)
