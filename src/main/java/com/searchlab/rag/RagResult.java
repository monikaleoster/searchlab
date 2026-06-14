package com.searchlab.rag;

import com.searchlab.search.SearchHit;
import java.util.List;

public record RagResult(String answer, List<SearchHit> sources, String error) {}
