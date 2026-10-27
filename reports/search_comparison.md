# Search comparison checkpoint

Model: `BAAI/bge-small-en-v1.5`. Corpus: 946 records, 959 embedding windows. These six examples are learning checks, not a broad benchmark.

| Question | Keyword first | Semantic first | Hybrid first |
|---|---|---|---|
| What are accidental loads? | clause:1.3.1 | clause:1.3.1 | clause:1.3.1 |
| What are the clearances for fastener holes? | table:19 | clause:10.2.1 | table:19 |
| What partial safety factors apply to materials? | clause:5.4.1 | clause:13.2.3 | clause:13.2.3 |
| Diagram of plates with bolts holes in tension | figure:05 | figure:05 | figure:05 |
| What is the minimum design action on a connection? | clause:8.7.1.5 | clause:10.7 | clause:10.7 |
| What loads arise from vehicle collisions? | clause:5.6.1 | clause:1.3.1 | clause:3.2 |

Observed tradeoffs:

- The vehicle-collision paraphrase retrieves the accidental-load definition first with semantic search. Keyword and hybrid search miss that definition in their first three results.
- Semantic and hybrid search move clause 10.7 to first place for minimum connection design action.
- The general material-safety-factor question is better ranked by keyword search. Semantic search prioritizes section 13; hybrid keeps clause 5.4.1 and Table 5 in the first three, but not first.
- Table and image metadata survive all methods. The diagram is found through its caption and clause text, without image interpretation.

Scores have different scales. Use the source evidence to judge relevance; the score is not an answer-confidence percentage.
