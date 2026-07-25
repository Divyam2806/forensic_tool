package com.forensics.api;

import org.json.JSONObject;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

/**
 * Low-level HTTP client for the Python FastAPI forensic service.
 * Handles all HTTP mechanics — request building, response parsing,
 * error handling. No business logic or case awareness here.
 *
 * All methods throw IOException on non-200 responses or network failure.
 * Callers (CaseMetadataExtractionService) handle business-level errors.
 */
public class ForensicApiClient {

    private static final String BASE_URL = "http://127.0.0.1:8000";
    private final HttpClient httpClient  = HttpClient.newHttpClient();


    // ── Health check ───────────────────────────────────────────────────

    public boolean isServiceRunning() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(BASE_URL + "/status"))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(
                    request, HttpResponse.BodyHandlers.ofString()
            );

            return response.statusCode() == 200;

        } catch (Exception e) {
            return false;
        }
    }


    // ── Core HTTP helpers ──────────────────────────────────────────────

    /**
     * Send POST request with JSON body, return parsed response.
     * Throws IOException if response is not 200.
     */
    private JSONObject post(String endpoint, JSONObject body)
            throws IOException, InterruptedException {

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(BASE_URL + endpoint))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body.toString()))
                .build();

        HttpResponse<String> response = httpClient.send(
                request, HttpResponse.BodyHandlers.ofString()
        );

        if (response.statusCode() != 200) {
            throw new IOException(
                    "HTTP " + response.statusCode()
                    + " from " + endpoint
                    + ": " + response.body()
            );
        }

        return new JSONObject(response.body());
    }


    // ── Endpoint methods ───────────────────────────────────────────────

    /**
     * POST /scan
     * Returns response containing session_id, total_files,
     * scanned_path, manifest_hash.
     */
    public JSONObject scan(String path, int maxFiles,
                           boolean recursive, String outputFolder)
            throws IOException, InterruptedException {

        JSONObject body = new JSONObject();
        body.put("path",          path);
        body.put("max_files",     maxFiles);
        body.put("recursive",     recursive);
        body.put("output_folder", outputFolder);

        return post("/scan", body);
    }


    /**
     * POST /browser
     * Returns response containing total_cookies, nel_records, ts_domains.
     */
    public JSONObject browser(String sessionId, String networkFolderPath)
            throws IOException, InterruptedException {

        JSONObject body = new JSONObject();
        body.put("session_id", sessionId);
        body.put("path",       networkFolderPath);

        return post("/browser", body);
    }


    /**
     * POST /report
     * Returns response containing report_path and case_id.
     */
    public JSONObject report(String sessionId, String investigator, int topN, String outputPath)
            throws IOException, InterruptedException {

        JSONObject body = new JSONObject();
        body.put("session_id",   sessionId);
        body.put("investigator", investigator);
        body.put("top_n",        topN);
        body.put("output_path",  outputPath);

        return post("/report", body);
    }

    public JSONObject analyze(String filePath)
        throws IOException, InterruptedException {

        JSONObject body = new JSONObject();
        body.put("file_path", filePath);

        return post("/analyze", body);
    }
    /**
     * POST /clear
     * Frees session memory on Python side.
     */
    public void clear(String sessionId)
            throws IOException, InterruptedException {

        JSONObject body = new JSONObject();
        body.put("session_id", sessionId);

        post("/clear", body);
    }
}