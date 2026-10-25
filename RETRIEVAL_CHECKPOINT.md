# Keyword retrieval checkpoint

Phase 1 produced 946 records: 943 clauses, two tables, and one diagram.
Phase 2 searches this saved corpus without generating answers.

## First query

From the active `rag-is-code` repository:

```bash
python scripts/retrieve.py "What are the clearances for fastener holes?"
```

The script uses only Python's standard library and writes no files. It loads both
JSONL collections and prints the best three matches with PDF source links,
matched terms, review status, and the appropriate renderer. Table rows and image
paths are preserved in each result. Text snippets are shortened for the console;
the full chunk remains in the result object.

## How it works

1. Tokenize the question and passages: lowercase and split punctuation into words.
   Numbers and dotted numbers, such as `10.7`, are retained.
2. Remove common stop words. The question above becomes `clearances`, `fastener`,
   and `holes`. Negation words such as `not` are retained, though this simple
   word matcher does not understand sentence logic.
3. Match unique query words against each chunk's text and content type. The type
   label lets a question containing `diagram` match the diagram record.
4. Score one point for each distinct matched query word. Repeating a word adds no
   extra points. Exclude chunks with zero matches.
5. Rank by score; ties favor shorter tokenized passages, then stable ID.
6. Return the first k results. This is what `top-k` means.

These are word-match scores, not answer-confidence percentages. There is no
stemming yet, so `hole` and `holes` differ. Synonyms, OCR damage, sentence meaning,
and the preference for shorter chunks can all affect relevance. The baseline
is deliberately small enough to understand and provides a comparison for later
search methods. It neither reads the PDF nor changes existing chunks.

## Five review questions

After inspecting the first query, run:

```bash
python scripts/retrieve.py --examples
```

| Question | Expected useful evidence |
|---|---|
| What are accidental loads? | Clause 1.3.1 |
| What are the clearances for fastener holes? | Table 19 |
| What partial safety factors apply to materials? | Clause 5.4.1 and Table 5 |
| Diagram of plates with bolts holes in tension | Figure 5 |
| What is the minimum design action on a connection? | Clause 10.7 |

Check whether the useful evidence appears in the first three results. Inspect
irrelevant results too; they explain what the scoring misses. A correct passage
appearing in the first three and a correct passage ranked first are different
outcomes. No manual boosts are added for these questions.

To inspect more candidates:

```bash
python scripts/retrieve.py "What are accidental loads?" --top-k 5
```

Pause after the user reviews the results. Embeddings, hybrid retrieval, generated
answers, and the interface remain later checkpoints.
