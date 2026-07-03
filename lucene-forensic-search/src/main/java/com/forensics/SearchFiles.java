package com.forensics;

import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.queryparser.classic.MultiFieldQueryParser;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.*;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;

import java.nio.file.Paths;
import java.util.Locale;

public class SearchFiles {

    private static final String[] DEFAULT_SEARCH_FIELDS = {
            "content",
            "keywords_detected"
    };

    private static String normalize(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    private static String stripQuotes(String value) {
        String v = value.trim();
        if ((v.startsWith("\"") && v.endsWith("\"")) ||
                (v.startsWith("'") && v.endsWith("'"))) {
            return v.substring(1, v.length() - 1);
        }
        return v;
    }

    private static String resolveFieldName(String field) {
        String f = field.trim().toLowerCase(Locale.ROOT);

        return switch (f) {
            case "modified" -> "modified_date";
            case "created" -> "created_date";
            case "time_modified" -> "time_modified_raw";
            case "time_ctime" -> "time_ctime_raw";
            case "time_accessed" -> "time_accessed_raw";
            default -> f;
        };
    }

    private static boolean isFieldQuery(String q) {
        int colon = q.indexOf(':');
        return colon > 0;
    }

    private static Query buildQuery(String rawQuery, StandardAnalyzer analyzer) throws Exception {
        String q = rawQuery.trim();

        if (q.isEmpty()) {
            return new MatchAllDocsQuery();
        }

        // Dynamic field:value search
        if (isFieldQuery(q)) {
            int colon = q.indexOf(':');

            String field = q.substring(0, colon).trim();
            String value = q.substring(colon + 1).trim();

            String resolvedField = resolveFieldName(field);
            String exactValue = normalize(stripQuotes(value));

            return new TermQuery(new Term(resolvedField, exactValue));
        }

        // Normal keyword / boolean search
        MultiFieldQueryParser parser =
                new MultiFieldQueryParser(DEFAULT_SEARCH_FIELDS, analyzer);

        parser.setDefaultOperator(QueryParser.Operator.OR);

        return parser.parse(q);
    }

    private static String safe(String value) {
        return value == null ? "null" : value;
    }

    private static void printDoc(Document doc) {
        System.out.println("==================================");

        for (var field : doc.getFields()) {
            String fieldName = field.name();
            String fieldValue = doc.get(fieldName);

            if (fieldValue != null) {
                System.out.println(fieldName + " : " + fieldValue);
            }
        }

        System.out.println("==================================");
    }

    public static void main(String[] args) throws Exception {
        Directory dir = FSDirectory.open(Paths.get("../index"));

        try (DirectoryReader reader = DirectoryReader.open(dir)) {
            IndexSearcher searcher = new IndexSearcher(reader);
            StandardAnalyzer analyzer = new StandardAnalyzer();

            String rawQuery = args.length > 0
                    ? String.join(" ", args).trim()
                    : "bitcoin";

            Query query = buildQuery(rawQuery, analyzer);

            TopDocs results = searcher.search(query, 20);

            if (results.totalHits.value == 0) {
                System.out.println("No matches found.");
                return;
            }

            for (ScoreDoc sd : results.scoreDocs) {
                Document doc = searcher.doc(sd.doc);
                printDoc(doc);
            }
        }
    }
}