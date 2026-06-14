package com.searchlab.rag;

import com.searchlab.search.SearchHit;

import java.util.List;

public class ContextBuilder {

    public String build(List<SearchHit> hits) {
        if (hits.isEmpty()) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < hits.size(); i++) {
            SearchHit hit = hits.get(i);
            sb.append("[").append(i + 1).append("] ")
              .append(hit.sourceFilename()).append(": ")
              .append(hit.snippet());
            if (i < hits.size() - 1) {
                sb.append("\n");
            }
        }
        return sb.toString();
    }
}
