"""UMAP layout + two-level clustering. Usage: layout.py emb.json emb.npy out_prefix [n_fine n_coarse]
Writes out_prefix_laid.json, _clusters.json, _slim.json (for naming) and _umap.pkl (to place extra papers later)."""
import json, sys, pickle, numpy as np, umap
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
P = json.load(open(sys.argv[1])); E = np.load(sys.argv[2]); out = sys.argv[3]
NF = int(sys.argv[4]) if len(sys.argv) > 4 else 300; NC = int(sys.argv[5]) if len(sys.argv) > 5 else 30
u2 = umap.UMAP(n_neighbors=30, min_dist=0.05, metric='cosine', random_state=11).fit(E); U = u2.embedding_
lo, span = U.min(0), (U.max(0) - U.min(0)).max(); U = (U - lo) / span; off = (1 - (U.max(0) - U.min(0))) / 2 - U.min(0); U += off
u10 = umap.UMAP(n_components=10, n_neighbors=30, min_dist=0.0, metric='cosine', random_state=11).fit(E); U10 = u10.embedding_
F = np.hstack([U10, U * 4])
fine = KMeans(NF, n_init=4, random_state=0).fit_predict(F)
cen = np.array([F[fine == c].mean(0) for c in range(NF)]); big = [c for c in range(NF) if (fine == c).sum() >= 12]
for i in np.where(~np.isin(fine, big))[0]: fine[i] = big[int(((cen[big] - F[i]) ** 2).sum(1).argmin())]
remap = {c: k for k, c in enumerate(sorted(set(fine.tolist())))}; fine = np.array([remap[c] for c in fine]); NF = len(remap)
cent = np.array([np.hstack([E[fine == c].mean(0) * 3, U[fine == c].mean(0) * 4]) for c in range(NF)])
cof = AgglomerativeClustering(NC, linkage='ward').fit_predict(cent); coarse = cof[fine]
stop = list(ENGLISH_STOP_WORDS) + 'model models method methods propose proposed paper approach based results show learning existing data performance new using use task tasks framework novel work state art achieve demonstrate significantly furthermore large address problem extensive experiments code available github com https'.split()
docs = [p['t'] + ' ' + p['ab'] for p in P]
tv = TfidfVectorizer(ngram_range=(1, 2), min_df=4, max_df=0.3, stop_words=stop, sublinear_tf=True); X = tv.fit_transform(docs); V = np.array(tv.get_feature_names_out())
gm = np.asarray(X.mean(0)).ravel() ** 0.5 + 1e-9
def terms(m, n=8): return list(V[(np.asarray(X[m].mean(0)).ravel() / gm).argsort()[::-1][:n]])
def titles(m, n=12):
    idx = np.where(m)[0]; c = E[idx].mean(0); return [f"{P[i]['t']} ({P[i]['y']})" for i in idx[(E[idx] @ c).argsort()[::-1][:n]]]
def medoid(m):
    idx = np.where(m)[0]; c = U[idx].mean(0); return U[idx[((U[idx] - c) ** 2).sum(1).argmin()]].round(4).tolist()
yrs = lambda m: {int(y): int(n) for y, n in zip(*np.unique([P[i]['y'] for i in np.where(m)[0]], return_counts=True))}
info = {'fine': [dict(id=c, parent=int(cof[c]), n=int((fine == c).sum()), terms=terms(fine == c), titles=titles(fine == c), xy=medoid(fine == c), years=yrs(fine == c)) for c in range(NF)],
        'coarse': [dict(id=c, n=int((coarse == c).sum()), terms=terms(coarse == c, 10), titles=titles(coarse == c, 15), xy=U[coarse == c].mean(0).round(4).tolist(), years=yrs(coarse == c)) for c in range(NC)]}
nn = np.zeros((len(P), 10), dtype=np.int64)
for k in range(0, len(P), 2048):
    S = E[k:k + 2048] @ E.T
    for j in range(S.shape[0]): S[j, k + j] = -1
    nn[k:k + 2048] = np.argsort(-S, axis=1)[:, :10]
for i, p in enumerate(P): p.update(x=round(float(U[i, 0]), 4), y2=round(float(U[i, 1]), 4), f=int(fine[i]), c=int(coarse[i]), nn=nn[i].tolist())
json.dump(P, open(out + '_laid.json', 'w'), ensure_ascii=False); json.dump(info, open(out + '_clusters.json', 'w'))
json.dump({'coarse': [{k: c[k] for k in ('id', 'terms', 'titles', 'years')} for c in info['coarse']], 'fine': [{k: c[k] for k in ('id', 'parent', 'terms', 'titles', 'years')} for c in info['fine']]}, open(out + '_slim.json', 'w'))
pickle.dump({'u2': u2, 'u10': u10, 'lo': lo, 'span': span, 'off': off, 'fineF': np.array([F[fine == c].mean(0) for c in range(NF)]), 'fine': fine, 'coarse_of': cof}, open(out + '_umap.pkl', 'wb'))
for c in info['coarse']: print(c['id'], c['n'], c['terms'][:5])
