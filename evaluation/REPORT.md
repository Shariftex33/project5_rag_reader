# Evaluation report

Questions: **18** over 3 documents (PDF, DOCX, TXT) - top-k = **3**.

Hit@k = a retrieved chunk contains the gold evidence; MRR = mean reciprocal rank of the first such chunk.

| Embedder | Strategy | Size | Overlap | Chunks | Avg chars | Hit@k | MRR | Index s |
|---|---|---|---|---|---|---|---|---|
| hash | sentence | 600 | 0 | 22 | 335 | 0.944 | 0.852 | 0.06 |
| hash | sentence | 600 | 100 | 22 | 341 | 0.944 | 0.852 | 0.06 |
| hash | recursive | 300 | 0 | 36 | 204 | 0.889 | 0.833 | 0.09 |
| hash | sentence | 1000 | 100 | 20 | 374 | 0.889 | 0.833 | 0.06 |
| hash | sentence | 300 | 100 | 38 | 220 | 0.944 | 0.824 | 0.07 |
| hash | recursive | 300 | 100 | 42 | 232 | 0.889 | 0.796 | 0.09 |
| hash | sentence | 300 | 0 | 35 | 210 | 0.889 | 0.796 | 0.06 |
| hash | sentence | 1000 | 0 | 20 | 369 | 0.889 | 0.796 | 0.07 |
| hash | fixed | 600 | 0 | 21 | 352 | 0.833 | 0.741 | 0.09 |
| hash | recursive | 600 | 0 | 23 | 321 | 0.833 | 0.741 | 0.09 |
| hash | fixed | 600 | 100 | 26 | 309 | 0.778 | 0.722 | 0.09 |
| hash | fixed | 1000 | 100 | 20 | 384 | 0.778 | 0.722 | 0.07 |
| hash | recursive | 600 | 100 | 23 | 345 | 0.778 | 0.722 | 0.06 |
| hash | recursive | 1000 | 0 | 20 | 369 | 0.778 | 0.722 | 0.06 |
| hash | recursive | 1000 | 100 | 20 | 383 | 0.778 | 0.722 | 0.07 |
| hash | fixed | 1000 | 0 | 19 | 389 | 0.778 | 0.685 | 0.07 |
| hash | fixed | 300 | 100 | 48 | 208 | 0.722 | 0.667 | 0.1 |
| hash | fixed | 300 | 0 | 31 | 238 | 0.722 | 0.62 | 0.08 |

**Best configuration in this run:** hash + sentence (size 600, overlap 0) - Hit@3 0.944, MRR 0.852.

Questions the best configuration still missed: How long do I have to report a stolen laptop?.
