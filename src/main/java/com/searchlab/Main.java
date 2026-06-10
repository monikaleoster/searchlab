package com.searchlab;

import com.searchlab.opensearch.IndexBootstrap;
import com.searchlab.opensearch.OpenSearchClientFactory;
import org.opensearch.client.opensearch.OpenSearchClient;
import picocli.CommandLine;
import picocli.CommandLine.Command;

@Command(
        name = "searchlab",
        mixinStandardHelpOptions = true,
        version = "0.1.0",
        description = "SearchLab — PDF ingestion and BM25 search over OpenSearch",
        subcommands = {
                com.searchlab.cli.IngestCommand.class,
                com.searchlab.cli.QueryCommand.class,
                com.searchlab.cli.RagCommand.class
        }
)
public class Main implements Runnable {

    @Override
    public void run() {
        CommandLine.usage(this, System.out);
    }

    public static void main(String[] args) {
        int exit = new CommandLine(new Main()).execute(args);
        System.exit(exit);
    }

    /** T-0.09: connect, ensure index, print OK. Used during development. */
    public static void smokeConnect() throws Exception {
        OpenSearchClient client = OpenSearchClientFactory.createDefault();
        IndexBootstrap.ensureIndexExists(client);
        System.out.println("OK — connected to OpenSearch and index is ready");
    }
}
