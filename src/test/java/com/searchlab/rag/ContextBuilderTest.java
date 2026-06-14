package com.searchlab.rag;

import com.searchlab.search.SearchHit;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ContextBuilderTest {

    private final ContextBuilder builder = new ContextBuilder();

    @Test
    void emptyListReturnsEmptyString() {
        assertEquals("", builder.build(List.of()));
    }

    @Test
    void singlePassageHasCorrectPrefix() {
        SearchHit hit = new SearchHit(1, 0.9, "doc.pdf", 1, "some text");
        String result = builder.build(List.of(hit));
        assertEquals("[1] doc.pdf: some text", result);
    }

    @Test
    void multiplePassagesHaveSequentialNumbering() {
        List<SearchHit> hits = List.of(
                new SearchHit(1, 0.9, "a.pdf", 1, "first"),
                new SearchHit(2, 0.8, "b.pdf", 2, "second"),
                new SearchHit(3, 0.7, "c.pdf", 3, "third")
        );
        String result = builder.build(hits);
        assertEquals(
                "[1] a.pdf: first\n[2] b.pdf: second\n[3] c.pdf: third",
                result
        );
    }
}
