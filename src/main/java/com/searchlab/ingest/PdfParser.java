package com.searchlab.ingest;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class PdfParser {

    private static final Logger log = LoggerFactory.getLogger(PdfParser.class);

    public List<PageText> parse(Path pdfPath) throws IOException {
        log.debug("Parsing PDF: {}", pdfPath);
        List<PageText> pages = new ArrayList<>();

        try (PDDocument doc = Loader.loadPDF(pdfPath.toFile())) {
            int pageCount = doc.getNumberOfPages();
            PDFTextStripper stripper = new PDFTextStripper();

            for (int pageNum = 1; pageNum <= pageCount; pageNum++) {
                stripper.setStartPage(pageNum);
                stripper.setEndPage(pageNum);
                String text = stripper.getText(doc).trim();
                if (!text.isEmpty()) {
                    pages.add(new PageText(pageNum, text));
                }
            }
        }

        log.debug("Extracted {} pages from {}", pages.size(), pdfPath.getFileName());
        return pages;
    }
}
