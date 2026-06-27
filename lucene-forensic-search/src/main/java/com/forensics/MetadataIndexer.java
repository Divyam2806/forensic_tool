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
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MetadataIndexer {

    private static final Pattern ISO_DATE = Pattern.compile("^(\\d{4})-(\\d{2})-(\\d{2}).*$");
    private static final Pattern NTFS_DATE = Pattern.compile("^D:(\\d{4})(\\d{2})(\\d{2}).*$");

    private static String normalize(String value) {
        if (value == null) return "";
        String v = value.trim();
        if (v.isEmpty() || v.equalsIgnoreCase("unavailable") || v.equalsIgnoreCase("null")) {
            return "";
        }
        return v.toLowerCase(Locale.ROOT);
    }

    private static String normalizeExtension(String ext) {
        if (ext == null) return "";
        String v = ext.trim().toLowerCase(Locale.ROOT);
        if (v.startsWith(".")) {
            v = v.substring(1);
        }
        return v;
    }

    private static String extractDate(String raw) {
        if (raw == null) return "";
        String v = raw.trim();
        if (v.isEmpty() || v.equalsIgnoreCase("unavailable") || v.equalsIgnoreCase("null")) {
            return "";
        }

        Matcher iso = ISO_DATE.matcher(v);
        if (iso.matches()) {
            return iso.group(1) + "-" + iso.group(2) + "-" + iso.group(3);
        }

        Matcher ntfs = NTFS_DATE.matcher(v);
        if (ntfs.matches()) {
            return ntfs.group(1) + "-" + ntfs.group(2) + "-" + ntfs.group(3);
        }

        if (v.length() >= 10 && v.charAt(4) == '-' && v.charAt(7) == '-') {
            return v.substring(0, 10);
        }

        return v.toLowerCase(Locale.ROOT);
    }

    private static void addExact(Document doc, String field, String value) {
        String normalized = normalize(value);
        if (!normalized.isEmpty()) {
            doc.add(new StringField(field, normalized, Field.Store.YES));
        }
    }

    private static void addStored(Document doc, String field, String value) {
        if (value != null && !value.trim().isEmpty()) {
            doc.add(new StoredField(field, value));
        }
    }

    private static void addStoredLong(Document doc, String field, long value) {
        if (value >= 0) {
            doc.add(new StoredField(field, value));
        }
    }

    private static String joinKeywords(JSONArray arr) {
        if (arr == null || arr.length() == 0) return "";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < arr.length(); i++) {
            String item = arr.optString(i, "").trim();
            if (!item.isEmpty()) {
                if (sb.length() > 0) sb.append(' ');
                sb.append(item.toLowerCase(Locale.ROOT));
            }
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        Path indexPath = Paths.get("../index");
        Directory dir = FSDirectory.open(indexPath);
        StandardAnalyzer analyzer = new StandardAnalyzer();

        IndexWriterConfig config = new IndexWriterConfig(analyzer);
        config.setOpenMode(IndexWriterConfig.OpenMode.CREATE_OR_APPEND);

        File folder = new File("../metadata-json");
        if (!folder.exists() || !folder.isDirectory()) {
            System.err.println("Metadata folder not found: " + folder.getAbsolutePath());
            return;
        }

        try (IndexWriter writer = new IndexWriter(dir, config)) {
            File[] files = folder.listFiles();
            if (files == null) {
                System.err.println("No metadata files found.");
                return;
            }

            for (File file : files) {
                if (!file.isFile() || !file.getName().toLowerCase(Locale.ROOT).endsWith(".json")) {
                    continue;
                }

                String jsonContent = Files.readString(file.toPath());
                JSONObject json = new JSONObject(jsonContent);

                Document doc = new Document();
                doc.add(new StringField("doc_type", "metadata", Field.Store.YES));

                // Core file identity
                String name = json.optString("name", file.getName());
                String path = json.optString("path", "");
                String extension = normalizeExtension(json.optString("extension", ""));

                addExact(doc, "name", name);
                addStored(doc, "name_display", name);

                addExact(doc, "path", path);
                addStored(doc, "path_display", path);

                addExact(doc, "extension", extension);

                // General metadata
                addExact(doc, "is_file", String.valueOf(json.optBoolean("is_file", true)));
                addExact(doc, "is_directory", String.valueOf(json.optBoolean("is_directory", false)));
                addExact(doc, "is_symlink", String.valueOf(json.optBoolean("is_symlink", false)));
                addExact(doc, "is_readable", String.valueOf(json.optBoolean("is_readable", true)));
                addExact(doc, "is_writable", String.valueOf(json.optBoolean("is_writable", true)));

                long sizeBytes = json.optLong("size_bytes", -1);
                addExact(doc, "size_bytes", sizeBytes >= 0 ? String.valueOf(sizeBytes) : "");
                addStoredLong(doc, "size_bytes_num", sizeBytes);
                addExact(doc, "size_human", json.optString("size_human", ""));

                addExact(doc, "platform", json.optString("platform", ""));
                addExact(doc, "format", json.optString("format", ""));
                addExact(doc, "author", json.optString("author", ""));
                addExact(doc, "creator_tool", json.optString("creator_tool", ""));
                addExact(doc, "producer", json.optString("producer", ""));
                addExact(doc, "title", json.optString("title", ""));
                addExact(doc, "subject", json.optString("subject", ""));
                addExact(doc, "ctime_meaning", json.optString("ctime_meaning", ""));
                addExact(doc, "risk_level", json.optString("risk_level", ""));
                addExact(doc, "encrypted", String.valueOf(json.optBoolean("encrypted", false)));
                addExact(doc, "page_count", json.has("page_count") ? String.valueOf(json.optInt("page_count")) : "");

                // Time fields: store raw + derived date field for exact date search
                String timeModified = json.optString("time_modified", "");
                String timeAccessed = json.optString("time_accessed", "");
                String timeCtime = json.optString("time_ctime", "");
                String created = json.optString("created", "");
                String modified = json.optString("modified", "");

                addExact(doc, "time_modified_raw", timeModified);
                addStored(doc, "time_modified_display", timeModified);

                addExact(doc, "time_accessed_raw", timeAccessed);
                addStored(doc, "time_accessed_display", timeAccessed);

                addExact(doc, "time_ctime_raw", timeCtime);
                addStored(doc, "time_ctime_display", timeCtime);

                addExact(doc, "created_raw", created);
                addStored(doc, "created_display", created);

                addExact(doc, "modified_raw", modified);
                addStored(doc, "modified_display", modified);

                String modifiedDateSource = !timeModified.isBlank() ? timeModified : modified;
                String createdDateSource = !timeCtime.isBlank() ? timeCtime : created;

                addExact(doc, "modified_date", extractDate(modifiedDateSource));
                addExact(doc, "created_date", extractDate(createdDateSource));

                // NTFS attributes
                JSONObject ntfsAttrs = json.optJSONObject("ntfs_attributes");
                if (ntfsAttrs != null) {
                    addExact(doc, "ntfs_readonly", String.valueOf(ntfsAttrs.optBoolean("readonly", false)));
                    addExact(doc, "ntfs_hidden", String.valueOf(ntfsAttrs.optBoolean("hidden", false)));
                    addExact(doc, "ntfs_system", String.valueOf(ntfsAttrs.optBoolean("system", false)));
                    addExact(doc, "ntfs_archive", String.valueOf(ntfsAttrs.optBoolean("archive", false)));
                    addExact(doc, "ntfs_encrypted", String.valueOf(ntfsAttrs.optBoolean("encrypted", false)));
                    addExact(doc, "ntfs_compressed", String.valueOf(ntfsAttrs.optBoolean("compressed", false)));
                    addExact(doc, "ntfs_sparse", String.valueOf(ntfsAttrs.optBoolean("sparse", false)));
                }

                JSONObject mftInfo = json.optJSONObject("ntfs_mft_info");
                if (mftInfo != null) {
                    addExact(doc, "mft_file_index", mftInfo.has("mft_file_index") ? String.valueOf(mftInfo.optLong("mft_file_index")) : "");
                    addExact(doc, "hard_link_count", mftInfo.has("hard_link_count") ? String.valueOf(mftInfo.optInt("hard_link_count")) : "");
                    addExact(doc, "volume_serial", mftInfo.optString("volume_serial", ""));
                }

                // Keywords detected
                JSONArray keywords = json.optJSONArray("keywords_detected");
                String keywordText = joinKeywords(keywords);
                if (!keywordText.isBlank()) {
                    doc.add(new TextField("keywords_detected", keywordText, Field.Store.YES));
                }

                // Full text content
                String content = json.optString("content", "");
                if (!content.isBlank()) {
                    doc.add(new TextField("content", content, Field.Store.YES));
                }

                writer.addDocument(doc);
                System.out.println("Metadata Indexed: " + name);
            }
        }

        System.out.println("Metadata indexing complete.");
    }
}