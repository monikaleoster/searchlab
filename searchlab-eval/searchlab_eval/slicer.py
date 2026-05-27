def slice_queries(
    queries: dict, qrels: dict, n: int
) -> tuple[dict, dict]:
    """Return the first n queries sorted by query ID (lexicographic).

    Filters qrels to match. n=0 or n >= len(queries) returns the full set.
    """
    if n == 0 or n >= len(queries):
        return queries, qrels

    ids = sorted(queries.keys())[:n]
    id_set = set(ids)

    sliced_queries = {qid: queries[qid] for qid in ids}
    sliced_qrels = {qid: qrels[qid] for qid in ids if qid in qrels}

    return sliced_queries, sliced_qrels
