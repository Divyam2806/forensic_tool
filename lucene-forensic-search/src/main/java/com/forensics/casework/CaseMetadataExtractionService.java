package com.forensics.casework;

import com.forensics.api.ForensicApiClient;
import org.json.JSONObject;

import java.io.IOException;
import java.nio.file.Path;

/**
 * Case-level orchestration for metadata extraction.
 * Uses ForensicApiClient for HTTP communication with Python service.
 * Handles case path resolution and session lifecycle.
 *
 * Session lifecycle:
 *   extractMetadata()        → creates session
 *   extractBrowserArtifacts() → optional, adds to session
 *   generateReport()          → generates PDF from session
 *   clearSession()            → frees session memory
 */
public class CaseMetadataExtractionService {

    private final ForensicApiClient apiClient = new ForensicApiClient();
    private String currentSessionId = null;


    // ── Health check ───────────────────────────────────────────────────

    public boolean isServiceRunning() {
        return apiClient.isServiceRunning();
    }


    // ── Scan ───────────────────────────────────────────────────────────

    public JSONObject extractMetadata(CaseInfo caseInfo, int maxFiles)
            throws IOException, InterruptedException {

        Path evidenceDir = caseInfo.casePath().resolve("evidence");
        Path metadataDir = CaseServices.metadataDir(caseInfo);

        JSONObject result = apiClient.scan(
                evidenceDir.toAbsolutePath().toString(),
                maxFiles,
                true,
                metadataDir.toAbsolutePath().toString()
        );

        currentSessionId = result.getString("session_id");
        return result;
    }


    // ── Browser artifacts ──────────────────────────────────────────────

    public JSONObject extractBrowserArtifacts(String networkFolderPath)
            throws IOException, InterruptedException {

        ensureSessionExists("extractBrowserArtifacts");
        return apiClient.browser(currentSessionId, networkFolderPath);
    }


    // ── Report ─────────────────────────────────────────────────────────

    public JSONObject generateReport(String investigator, int topN)
            throws IOException, InterruptedException {

        ensureSessionExists("generateReport");
        return apiClient.report(currentSessionId, investigator, topN, null);
    }


    // ── Clear ──────────────────────────────────────────────────────────

    public void clearSession() throws IOException, InterruptedException {
        if (currentSessionId == null) return;
        apiClient.clear(currentSessionId);
        currentSessionId = null;
    }


    // ── Getters ────────────────────────────────────────────────────────

    public String getCurrentSessionId() {
        return currentSessionId;
    }


    // ── Helpers ────────────────────────────────────────────────────────

    private void ensureSessionExists(String callerMethod) throws IOException {
        if (currentSessionId == null) {
            throw new IOException(
                callerMethod + "() called before extractMetadata() — no active session"
            );
        }
    }
}