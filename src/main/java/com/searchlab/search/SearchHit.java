package com.searchlab.search;

public record SearchHit(int rank, double score, String sourceFilename, int pageNumber, String snippet) {}
