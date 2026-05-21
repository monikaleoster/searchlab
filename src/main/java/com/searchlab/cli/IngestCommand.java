package com.searchlab.cli;

import com.searchlab.ingest.Chunk;
import com.searchlab.ingest.Chunker;
import com.searchlab.ingest.Indexer;
import com.searchlab.ingest.PageText;
import com.searchlab.ingest.PdfParser;
import com.searchlab.opensearch.IndexBootstrap;
import com.searchlab.opensearch.OpenSearchClientFactory;
import org.opensearch.client.opensearch.OpenSearchClient;
import picocli.CommandLine.Command;
import picocli.CommandLine.Parameters;

import java.nio.file.Path;
import java.util.List;

@Command(name = "ingest", description = "Parse a PDF and index its chunks into OpenSearch")
public class IngestCommand implements Runnable {

    @Parameters(index = "0", description = "Path to the PDF file", paramLabel = "<pdf-path>")
    private Path pdfPath;

    @Override
    public void run() {
        try {
            OpenSearchClient client = OpenSearchClientFactory.createDefault();
            IndexBootstrap.ensureIndexExists(client);

            PdfParser parser = new PdfParser();
            Chunker chunker = new Chunker();
            Indexer indexer = new Indexer(client);

            List<PageText> pages = parser.parse(pdfPath);
            List<Chunk> chunks = chunker.chunk(pages);
            int count = indexer.index(chunks, pdfPath.getFileName().toString());

            System.out.printf("Indexed %d chunks from %s%n", count, pdfPath.getFileName());

        } catch (Exception e) {
            System.err.println("Ingest failed: " + e.getMessage());
            throw new picocli.CommandLine.ExecutionException(
                    new picocli.CommandLine(this), "Ingest failed", e);
        }
    }
}
