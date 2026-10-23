# 5-7 minute talk track (also embedded as notes in AutoDocumentReader.pptx)
1. (0:30) Title - what it is: ask questions about your documents, answers cite sources; local Ollama or cloud OpenAI.
2. (0:45) Why RAG - hallucination, private/fresh data, traceability; strict "answer only from context" prompt.
3. (1:00) Pipeline - load, chunk, embed+store, retrieve (with follow-up rewriting), answer with [n] citations.
4. (1:00) Source tracing - metadata per chunk, numbered passages, expandable source cards with file/page/score.
5. (1:15) Evaluation - 18 questions, Hit@3 and MRR; sentence-aware chunking best; caveats about small sample and hash embedder.
6. (1:00) Local vs cloud + next steps.
7. (1:00-2:00) LIVE DEMO: Load samples -> "What is the home office stipend?" -> follow-up "And the internet allowance?" -> expand sources -> ask something not in the docs to show the "couldn't find" fallback -> untick a document to scope search.
