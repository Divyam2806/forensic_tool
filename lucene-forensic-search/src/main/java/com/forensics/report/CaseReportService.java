package com.forensics.report;

import com.forensics.api.ForensicApiClient;
import com.forensics.casework.CaseInfo;
import org.json.JSONObject;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public class CaseReportService {

    private final ForensicApiClient apiClient = new ForensicApiClient();

    public Path generateReport(CaseInfo caseInfo, String investigator, String sessionId)
            throws IOException, InterruptedException {

        Path reportsDir = caseInfo.casePath().resolve("reports");
        Files.createDirectories(reportsDir);

        String timestamp = java.time.LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));

        String outputPath = reportsDir
                .resolve(caseInfo.caseId() + "_report_" + timestamp + ".pdf")
                .toAbsolutePath()
                .toString();

        JSONObject result = apiClient.report(sessionId, investigator, 20, outputPath);

        // Python service saves PDF to extractor/output/ —
        // return that path so caller can show it to user
        return Path.of(result.getString("report_path"));
    }
}