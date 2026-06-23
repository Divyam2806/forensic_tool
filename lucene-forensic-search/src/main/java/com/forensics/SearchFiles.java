package com.forensics;

import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.queryparser.classic.MultiFieldQueryParser;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.MatchAllDocsQuery;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;

import java.nio.file.Paths;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

public class SearchFiles {

    private static final Set<String> EXACT_FIELDS = new HashSet<>(Arrays.asList(
            "doc_type",
            "filename",
            "filename_display",
            "path",
            "path_display",
            "extension",
            "sha256",
            "author",
            "format",
            "risk_level",
            "modified_date",
            "created_date",
            "time_modified_raw",
            "time_ctime_raw",
            "time_accessed_raw",
            "is_file",
            "is_directory",
            "is_symlink",
            "is_readable",
            "is_writable",
            "encrypted",
            "page_count",
            "size_bytes",
            "size_human",
            "platform",
            "creator_tool",
            "producer",
            "title",
            "subject",
            "ctime_meaning",
            "ntfs_readonly",
            "ntfs_hidden",
            "ntfs_system",
            "ntfs_archive",
            "ntfs_encrypted",
            "ntfs_compressed",
            "ntfs_sparse",
            "mft_file_index",
            "hard_link_count",
            "volume_serial"
    ));

    private static final String[] SEARCH_FIELDS = {
            "content",
            "filename",
            "filename_display",
            "path",
            "path_display",
            "extension",
            "sha256",
            "author",
            "format",
            "risk_level",
            "modified_date",
            "created_date",
            "time_modified_raw",
            "time_ctime_raw",
            "time_accessed_raw",
            "keywords_detected",
            "doc_type",
            "is_file",
            "is_directory",
            "is_symlink",
            "is_readable",
            "is_writable",
            "encrypted",
            "page_count",
            "size_bytes",
            "size_human",
            "platform",
            "creator_tool",
            "producer",
            "title",
            "subject",
            "ctime_meaning",
            "ntfs_readonly",
            "ntfs_hidden",
            "ntfs_system",
            "ntfs_archive",
            "ntfs_encrypted",
            "ntfs_compressed",
            "ntfs_sparse",
            "mft_file_index",
            "hard_link_count",
            "volume_serial"
    };

    private static String normalize(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    private static String stripQuotes(String value) {
        String v = value.trim();
        if ((v.startsWith("\"") && v.endsWith("\"")) || (v.startsWith("'") && v.endsWith("'"))) {
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

        if (isFieldQuery(q)) {
            int colon = q.indexOf(':');
            String field = q.substring(0, colon).trim();
            String value = q.substring(colon + 1).trim();

            String resolvedField = resolveFieldName(field);

            if (EXACT_FIELDS.contains(resolvedField)) {
                String exactValue = normalize(stripQuotes(value));
                return new TermQuery(new Term(resolvedField, exactValue));
            }
        }

        MultiFieldQueryParser parser = new MultiFieldQueryParser(SEARCH_FIELDS, analyzer);
        parser.setDefaultOperator(QueryParser.Operator.OR);
        return parser.parse(q);
    }

    private static String safe(String value) {
        return value == null ? "null" : value;
    }

    private static void printDoc(Document doc) {
        String type = doc.get("doc_type");

        System.out.println("==================================");
        System.out.println("Type : " + safe(type));

        if ("evidence".equals(type)) {
            System.out.println("Filename       : " + safe(doc.get("filename_display")));
            System.out.println("Path           : " + safe(doc.get("path_display")));
            System.out.println("Extension      : " + safe(doc.get("extension")));
            System.out.println("SHA256         : " + safe(doc.get("sha256")));
            System.out.println("File Size      : " + safe(doc.get("filesize")));
            System.out.println("Last Modified  : " + safe(doc.get("lastModified")));
            System.out.println("Matched Content: " + safe(doc.get("content")));
        } else if ("metadata".equals(type)) {
            System.out.println("Name           : " + safe(doc.get("name_display")));
            System.out.println("Path           : " + safe(doc.get("path_display")));
            System.out.println("Extension      : " + safe(doc.get("extension")));
            System.out.println("Format         : " + safe(doc.get("format")));
            System.out.println("Author         : " + safe(doc.get("author")));
            System.out.println("Creator Tool   : " + safe(doc.get("creator_tool")));
            System.out.println("Producer       : " + safe(doc.get("producer")));
            System.out.println("Title          : " + safe(doc.get("title")));
            System.out.println("Subject        : " + safe(doc.get("subject")));
            System.out.println("Platform       : " + safe(doc.get("platform")));
            System.out.println("Size Bytes     : " + safe(doc.get("size_bytes")));
            System.out.println("Page Count     : " + safe(doc.get("page_count")));
            System.out.println("Modified Date  : " + safe(doc.get("modified_date")));
            System.out.println("Created Date   : " + safe(doc.get("created_date")));
            System.out.println("Risk Level     : " + safe(doc.get("risk_level")));
            System.out.println("Keywords       : " + safe(doc.get("keywords_detected")));
            System.out.println("NTFS Hidden    : " + safe(doc.get("ntfs_hidden")));
            System.out.println("NTFS ReadOnly  : " + safe(doc.get("ntfs_readonly")));
            System.out.println("NTFS Encrypted : " + safe(doc.get("ntfs_encrypted")));
        } else {
            System.out.println("Filename       : " + safe(doc.get("filename_display")));
            System.out.println("Name           : " + safe(doc.get("name_display")));
            System.out.println("Path           : " + safe(doc.get("path_display")));
            System.out.println("Extension      : " + safe(doc.get("extension")));
            System.out.println("SHA256         : " + safe(doc.get("sha256")));
            System.out.println("Matched Content: " + safe(doc.get("content")));
            System.out.println("Format         : " + safe(doc.get("format")));
            System.out.println("Author         : " + safe(doc.get("author")));
            System.out.println("Risk Level     : " + safe(doc.get("risk_level")));
            System.out.println("Modified Date  : " + safe(doc.get("modified_date")));
            System.out.println("Created Date   : " + safe(doc.get("created_date")));
            System.out.println("Keywords       : " + safe(doc.get("keywords_detected")));
        }

        System.out.println("==================================");
    }

    public static void main(String[] args) throws Exception {
        Directory dir = FSDirectory.open(Paths.get("../index"));

        try (DirectoryReader reader = DirectoryReader.open(dir)) {
            IndexSearcher searcher = new IndexSearcher(reader);
            StandardAnalyzer analyzer = new StandardAnalyzer();

            String rawQuery = args.length > 0 ? String.join(" ", args).trim() : "bitcoin";
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