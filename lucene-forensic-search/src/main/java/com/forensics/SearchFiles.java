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

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Properties;
import java.io.InputStream;



public class SearchFiles {

    private static EmbeddingService embeddingService;

    static {
        try {
            Properties config = new Properties();
            try (InputStream input = SearchFiles.class.getClassLoader().getResourceAsStream("config.properties")) {
                config.load(input);
            }
            String modelPath = config.getProperty("minilm.model.path");
            String tokenizerPath = config.getProperty("minilm.tokenizer.path");
            embeddingService = new EmbeddingService(
                     modelPath, tokenizerPath
            );
        } catch (Exception e) {
            throw new RuntimeException("Failed to initialize embedding model.", e);
        }
    }

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

    public static Query buildQuery(String rawQuery, StandardAnalyzer analyzer) throws Exception {
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

    public static List<Document> search(Path indexPath, String rawQuery, int limit) throws Exception {
        Directory dir = FSDirectory.open(indexPath);

        try (DirectoryReader reader = DirectoryReader.open(dir)) {
            IndexSearcher searcher = new IndexSearcher(reader);
            StandardAnalyzer analyzer = new StandardAnalyzer();
            Query query = buildQuery(rawQuery, analyzer);
            TopDocs results = searcher.search(query, limit);

            List<Document> docs = new ArrayList<>();
            for (ScoreDoc sd : results.scoreDocs) {
                docs.add(searcher.doc(sd.doc));
            }
            return docs;
        }
    }

    public static List<Document> semanticSearch(
        Path indexPath,
        String queryText,
        int limit) throws Exception
    {

        Directory dir = FSDirectory.open(indexPath);

        try (DirectoryReader reader = DirectoryReader.open(dir)) {
            IndexSearcher searcher = new IndexSearcher(reader);
            float[] queryVector = embeddingService.embed(queryText);

            KnnFloatVectorQuery knnQuery =
                    new KnnFloatVectorQuery(
                            "artifact_embedding",
                            queryVector,
                            limit
                    );

            TopDocs results = searcher.search(knnQuery, limit);

            List<Document> docs = new ArrayList<>();

            for (ScoreDoc sd : results.scoreDocs) {
                docs.add(searcher.doc(sd.doc));
            }



            return docs;
        }
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

        Path indexPath = Paths.get("../index");
        boolean semantic = false;
        StringBuilder queryBuilder = new StringBuilder();

        for (String arg : args) {
            if (arg.equals("--semantic")) {
                semantic = true;
                continue;
            }
            if (arg.startsWith("--index=")) {
                indexPath = Paths.get(arg.substring("--index=".length()));
                continue;
            }
            if (!queryBuilder.isEmpty()) {
                queryBuilder.append(' ');
            }
            queryBuilder.append(arg);
        }

        if (queryBuilder.isEmpty()) {
            System.out.println("Usage:");
            System.out.println("  SearchFiles <query>");
            System.out.println("  SearchFiles --semantic <query>");
            return;
        }

        String rawQuery = queryBuilder.toString().trim();

        List<Document> results;

        if (semantic) {
            results = semanticSearch(indexPath, rawQuery, 5);
        } else {
            results = search(indexPath, rawQuery, 20);
        }

        if (results.isEmpty()) {
            System.out.println("No matches found.");
            return;
        }

        for (Document doc : results) {
            printDoc(doc);
        }
    }
}
