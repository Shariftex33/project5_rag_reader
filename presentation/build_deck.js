const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/mnt/skills/public/pptx/scripts/apply_theme.js");

const THEME = { name: "RAG Reader", headFontFace: "Georgia", bodyFontFace: "Calibri",
  colors: { dk1: "1F2A37", lt1: "FFFFFF", dk2: "0F3D3E", lt2: "F3F6F4", accent1: "0E7C7B", accent2: "D17A22",
            accent3: "5B8E7D", accent4: "8A9BA8", accent5: "B5483A", accent6: "3E5C76", hlink: "0E7C7B", folHlink: "5B8E7D" } };

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";           // 10 x 5.625 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Auto-Document Reader (RAG)";
const C = pres.SchemeColor;

pres.defineSlideMaster({ title: "CONTENT", background: { color: C.background1 },
  objects: [{ rect: { x: 0, y: 0, w: 0.18, h: 5.625, fill: { color: C.accent1 } } }],
  slideNumber: { x: 9.2, y: 5.2, w: 0.5, h: 0.3, fontSize: 10, color: C.accent4 } });
pres.defineSlideMaster({ title: "DARK", background: { color: C.text2 } });

const title = (s, t, dark) => s.addText(t, dark
  ? { x: 0.8, y: 1.5, w: 8.4, h: 1.2, fontSize: 40, bold: true, color: C.background1, valign: "middle", isTextBox: true, margin: 0 }
  : { x: 0.6, y: 0.35, w: 8.8, h: 0.8, fontSize: 28, bold: true, color: C.text2, valign: "middle", isTextBox: true, margin: 0 });
const card = (s, x, y, w, h, head, body, accent) => {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: "card" });
  s.addShape(pres.ShapeType.rect, { x, y, w: 0.06, h, fill: { color: accent }, line: { color: accent } });
  s.addText(head, { x: x + 0.2, y: y + 0.1, w: w - 0.3, h: 0.4, fontSize: 15, bold: true, color: C.text2, margin: 0, isTextBox: true });
  s.addText(body, { x: x + 0.2, y: y + 0.52, w: w - 0.3, h: h - 0.6, fontSize: 12, color: C.text1, margin: 0, valign: "top", isTextBox: true });
};

// 1 Title
pres.addSection({ title: "Intro" });
let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Intro" });
title(s, "Auto-Document Reader", true);
s.addText("Retrieval-Augmented Q&A with traceable sources - local (Ollama qwen2.5:3b) or cloud (OpenAI)", { x: 0.8, y: 2.8, w: 8.2, h: 0.7, fontSize: 18, color: "BFD8D2", isTextBox: true, margin: 0 });
s.addText("PDF · DOCX · TXT · Web  |  ChromaDB  |  Streamlit", { x: 0.8, y: 4.6, w: 8, h: 0.4, fontSize: 13, color: "8FB8B0", isTextBox: true, margin: 0 });
s.addNotes("(0:30) Hi - this is Auto-Document Reader. You upload documents, ask questions in plain language, and get answers that are grounded in your files, with the exact passages shown. It runs fully locally with Ollama and qwen2.5:3b, or in the cloud with OpenAI - one switch in the sidebar.");

// 2 Problem
pres.addSection({ title: "Approach" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Approach" });
title(s, "Why RAG instead of just asking the model?");
card(s, 0.6, 1.4, 2.8, 2.6, "Hallucination", "LLMs produce fluent but unsupported claims. Retrieval gives them evidence to stay within.", C.accent5);
card(s, 3.6, 1.4, 2.8, 2.6, "Private & fresh data", "Models have a cutoff and never saw your files. Documents can be added without retraining.", C.accent2);
card(s, 6.6, 1.4, 2.8, 2.6, "Traceability", "Every answer cites [n] passages with file and page, so a human can verify in seconds.", C.accent1);
s.addText("Rule in the prompt: answer only from the context, cite sources, otherwise say \"I couldn't find that in the uploaded documents.\"", { x: 0.6, y: 4.1, w: 8.8, h: 0.6, fontSize: 13, italic: true, color: C.text1, isTextBox: true, margin: 0 });
s.addNotes("(0:45) Three reasons: models hallucinate, they don't know your private documents, and you want to be able to check the answer. RAG solves all three. The key design choice is a strict prompt: use only the numbered passages, cite them, and admit when the answer isn't there.");

// 3 Pipeline
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Approach" });
title(s, "The pipeline");
const steps = [["1  Load", "PDF, DOCX, TXT, URL -> text with page / heading locators"], ["2  Chunk", "Split with overlap: fixed, recursive or sentence"], ["3  Embed + store", "MiniLM / Ollama / OpenAI vectors in ChromaDB"], ["4  Retrieve", "Follow-up -> standalone query -> top-k cosine search"], ["5  Answer", "LLM answers with [n] citations; UI shows chunks"]];
steps.forEach((st, i) => {
  const x = 0.6 + i * 1.78;
  s.addShape(pres.ShapeType.roundRect, { x, y: 1.6, w: 1.62, h: 2.3, fill: { color: i % 2 ? C.accent3 : C.accent1 }, line: { color: C.background1 }, rectRadius: 0.08, objectName: "step" });
  s.addText(st[0], { x: x + 0.1, y: 1.7, w: 1.42, h: 0.5, fontSize: 14, bold: true, color: C.background1, isTextBox: true, margin: 0 });
  s.addText(st[1], { x: x + 0.1, y: 2.25, w: 1.42, h: 1.5, fontSize: 11, color: C.background1, valign: "top", isTextBox: true, margin: 0 });
});
s.addText("Multi-document: one index over every file; tick documents to narrow scope.  Conversation: history is used only to rewrite the query.", { x: 0.6, y: 4.3, w: 8.8, h: 0.6, fontSize: 13, color: C.text1, isTextBox: true, margin: 0 });
s.addNotes("(1:00) Five steps. Load and keep locators like page numbers. Chunk with overlap. Embed into ChromaDB - each chunking and embedding configuration has its own collection so I can compare them. At question time, a follow-up like 'and the internet allowance?' is rewritten into a standalone query using the chat history, then we run top-k similarity search across all selected documents, and the model answers with citations.");

// 4 Source tracing
pres.addSection({ title: "Accuracy" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Accuracy" });
title(s, "Source tracing: how an answer is verified");
s.addText([
  { text: "Chunk metadata travels with every vector: doc name, page/heading, chunk index.", options: { bullet: true, breakLine: true } },
  { text: "Retrieved passages are numbered [1]..[k] in the prompt; the model must cite them.", options: { bullet: true, breakLine: true } },
  { text: "UI shows each passage with file, page and similarity score - and the rewritten search query.", options: { bullet: true, breakLine: true } },
  { text: "Min-similarity filter + fixed fallback sentence prevent answers from thin evidence.", options: { bullet: true } }],
  { x: 0.6, y: 1.4, w: 4.6, h: 3.3, fontSize: 14, color: C.text1, paraSpaceAfter: 10, valign: "top", isTextBox: true });
s.addShape(pres.ShapeType.rect, { x: 5.5, y: 1.4, w: 3.9, h: 3.1, fill: { color: C.background2 }, line: { color: C.accent4 }, objectName: "example" });
s.addText("Q: What is the home office stipend?", { x: 5.7, y: 1.5, w: 3.5, h: 0.4, fontSize: 12, bold: true, color: C.text2, isTextBox: true, margin: 0 });
s.addText("A: One-time stipend of 600 euros [1].", { x: 5.7, y: 1.95, w: 3.5, h: 0.5, fontSize: 12, color: C.text1, isTextBox: true, margin: 0 });
s.addText("[1] remote_work_policy.docx · Equipment and expenses · similarity score\n\"...a one-time home office stipend of 600 euros and a monthly internet allowance of 35 euros...\"", { x: 5.7, y: 2.6, w: 3.5, h: 1.7, fontSize: 11, italic: true, color: C.accent6, valign: "top", isTextBox: true, margin: 0 });
s.addNotes("(1:00) Accuracy here means two things: finding the right passage, and the answer staying faithful to it. For traceability, metadata travels with each chunk, passages are numbered in the prompt and the model must cite them. In the UI you can expand each source and see file, page, score and the actual text, so verifying is one click. If nothing relevant is retrieved the system says it couldn't find the answer instead of guessing.");

// 5 Evaluation chart
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Accuracy" });
title(s, "Evaluation: chunking strategy matters");
s.addChart(pres.charts.BAR, [
  { name: "Hit@3", labels: ["fixed", "recursive", "sentence"], values: [0.768, 0.824, 0.916] },
  { name: "MRR", labels: ["fixed", "recursive", "sentence"], values: [0.693, 0.756, 0.826] }],
  { x: 0.6, y: 1.3, w: 5.2, h: 3.7, barDir: "col", chartColors: [THEME.colors.accent1, THEME.colors.accent2], showLegend: true, legendPos: "b", legendFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", dataLabelFontFace: "+mn-lt", dataLabelFontSize: 10, valAxisMinVal: 0, valAxisMaxVal: 1, valAxisLabelFormatCode: "0.0", valAxisLabelFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: "E1E6E3", size: 0.5 }, catGridLine: { style: "none" }, showTitle: true, title: "Mean over size/overlap grid (hash embedder)", titleFontSize: 12, titleFontFace: "+mn-lt" });
s.addText([
  { text: "18 questions, 3 documents (PDF/DOCX/TXT)", options: { bullet: true, breakLine: true } },
  { text: "Sentence-aware chunks beat fixed windows by ~15 pts Hit@3", options: { bullet: true, breakLine: true } },
  { text: "Best: sentence, 600 chars -> Hit@3 0.94, MRR 0.85", options: { bullet: true, breakLine: true } },
  { text: "Overlap ~neutral on short paragraphs; helps fixed windows", options: { bullet: true, breakLine: true } },
  { text: "Rerun with MiniLM / Ollama / OpenAI via run_eval.py", options: { bullet: true } }],
  { x: 6.0, y: 1.5, w: 3.5, h: 3.4, fontSize: 12.5, color: C.text1, paraSpaceAfter: 8, valign: "top", isTextBox: true });
s.addNotes("(1:15) I compared 3 chunking strategies, 3 sizes and 2 overlaps on 18 questions with known evidence. Metrics: Hit@3 - did a top-3 chunk contain the answer; MRR - how high it ranked. Sentence-aware chunking wins because fixed windows cut facts in half. 600 characters was the sweet spot. Honest caveat: these numbers are from the offline hashing embedder; the harness also compares MiniLM, Ollama and OpenAI embeddings plus answer correctness and groundedness - run it to fill in those rows. Sample is small, so one question is about 5 points.");

// 6 Local vs cloud + limits
pres.addSection({ title: "Wrap-up" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Wrap-up" });
title(s, "Local vs cloud, and limits");
card(s, 0.6, 1.4, 4.2, 1.7, "Local: Ollama qwen2.5:3b", "Private, free, offline. Best with top-k 3-5 and chunks <= 800 chars; weaker at multi-step reasoning.", C.accent3);
card(s, 5.2, 1.4, 4.2, 1.7, "Cloud: OpenAI", "Stronger reasoning and embeddings; costs money and sends text to a third party.", C.accent6);
card(s, 0.6, 3.3, 8.8, 1.5, "Next steps", "Hybrid BM25 + vector search, cross-encoder re-ranking, OCR for scanned PDFs, larger evaluation set with LLM-judged faithfulness.", C.accent2);
s.addNotes("(1:00) Local gives privacy and zero cost, but a 3B model reasons less well, so keep context small. Cloud is stronger but not private. Next: hybrid search, a re-ranker, OCR, and a bigger evaluation set. Then a quick live demo: load samples, ask the stipend question, follow up about the internet allowance, expand the sources. Thank you. (Total about 5.5 minutes plus demo.)");

(async () => { await pres.writeFile({ fileName: "AutoDocumentReader.pptx" }); await applyTheme("AutoDocumentReader.pptx", THEME); console.log("ok"); })();
