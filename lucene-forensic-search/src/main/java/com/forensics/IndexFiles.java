package com.forensics;

import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.StoredField;
import org.apache.lucene.document.StringField;
import org.apache.lucene.document.TextField;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

public class IndexFiles {

    private static String normalize(String value) {
        if (value == null) return "";
        return value.trim().toLowerCase(Locale.ROOT);
    }

    private static String stripExtensionDot(String ext) {
        if (ext == null) return "";
        String v = ext.trim().toLowerCase(Locale.ROOT);
        if (v.startsWith(".")) {
            v = v.substring(1);
        }
        return v;
    }

    private static String getExtension(String fileName) {
        int dot = fileName.lastIndexOf('.');
        if (dot < 0 || dot == fileName.length() - 1) {
            return "";
        }
        return stripExtensionDot(fileName.substring(dot));
    }

    private static String sha256(File file) throws Exception {
        byte[] fileBytes = Files.readAllBytes(file.toPath());
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hashBytes = digest.digest(fileBytes);

        StringBuilder sb = new StringBuilder();
        for (byte b : hashBytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        Path indexPath = Paths.get("../index");
        Directory dir = FSDirectory.open(indexPath);
        StandardAnalyzer analyzer = new StandardAnalyzer();

        IndexWriterConfig config = new IndexWriterConfig(analyzer);
        config.setOpenMode(IndexWriterConfig.OpenMode.CREATE_OR_APPEND);

        File folder = new File("../evidence");
        if (!folder.exists() || !folder.isDirectory()) {
            System.err.println("Evidence folder not found: " + folder.getAbsolutePath());
            return;
        }

        try (IndexWriter writer = new IndexWriter(dir, config)) {
            File[] files = folder.listFiles();
            if (files == null) {
                System.err.println("No files found inside evidence folder.");
                return;
            }

            for (File file : files) {
                if (!file.isFile()) continue;

                String originalName = file.getName();
                String originalPath = file.getAbsolutePath();
                String content = Files.readString(file.toPath());
                String hash = sha256(file);
                String extension = getExtension(originalName);

                Document doc = new Document();
                doc.add(new StringField("doc_type", "evidence", Field.Store.YES));

                // Searchable exact fields
                doc.add(new StringField("filename", normalize(originalName), Field.Store.YES));
                doc.add(new StringField("path", normalize(originalPath), Field.Store.YES));
                doc.add(new StringField("extension", extension, Field.Store.YES));
                doc.add(new StringField("sha256", hash, Field.Store.YES));

                // Display fields
                doc.add(new StoredField("filename_display", originalName));
                doc.add(new StoredField("path_display", originalPath));

                // Full text content
                doc.add(new TextField("content", content, Field.Store.YES));

                // Basic filesystem metadata
                doc.add(new StoredField("filesize", file.length()));
                doc.add(new StoredField("lastModified", file.lastModified()));

                writer.addDocument(doc);
                System.out.println("Indexed: " + originalName);
            }
        }

        System.out.println("Evidence indexing complete.");
    }
}