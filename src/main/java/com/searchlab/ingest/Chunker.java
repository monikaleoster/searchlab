package com.searchlab.ingest;

import com.knuddels.jtokkit.Encodings;
import com.knuddels.jtokkit.api.Encoding;
import com.knuddels.jtokkit.api.EncodingRegistry;
import com.knuddels.jtokkit.api.EncodingType;
import com.knuddels.jtokkit.api.IntArrayList;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

public class Chunker {

    private static final Logger log = LoggerFactory.getLogger(Chunker.class);
    private static final int CHUNK_SIZE = 512;

    private final Encoding encoding;

    public Chunker() {
        EncodingRegistry registry = Encodings.newDefaultEncodingRegistry();
        this.encoding = registry.getEncoding(EncodingType.CL100K_BASE);
    }

    /**
     * Splits page text into 512-token chunks (no overlap).
     * Each chunk records the page number of its first token.
     */
    public List<Chunk> chunk(List<PageText> pages) {
        // Build a flat token stream, tracking page attribution per token
        List<Integer> tokens = new ArrayList<>();
        List<Integer> tokenPages = new ArrayList<>();

        for (PageText page : pages) {
            IntArrayList pageTokens = encoding.encode(page.text());
            for (int i = 0; i < pageTokens.size(); i++) {
                tokens.add(pageTokens.get(i));
                tokenPages.add(page.pageNumber());
            }
        }

        List<Chunk> chunks = new ArrayList<>();
        int totalTokens = tokens.size();
        int position = 0;

        for (int start = 0; start < totalTokens; start += CHUNK_SIZE) {
            int end = Math.min(start + CHUNK_SIZE, totalTokens);
            IntArrayList window = new IntArrayList(end - start);
            for (int i = start; i < end; i++) {
                window.add(tokens.get(i));
            }
            String text = encoding.decode(window);
            int pageNumber = tokenPages.get(start);
            chunks.add(new Chunk(text, pageNumber, position++));
        }

        log.debug("Chunked {} tokens into {} chunks", totalTokens, chunks.size());
        return chunks;
    }
}
