package com.forensics.report;

import com.forensics.casework.CaseInfo;
import com.forensics.casework.CaseServices;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

public class CaseReportService {
    public Path generateReport(CaseInfo caseInfo, String investigator) throws IOException, InterruptedException {
        Path evidenceDir = caseInfo.casePath().resolve("evidence");
        Path metadataDir = CaseServices.metadataDir(caseInfo);
        Path reportsDir = caseInfo.casePath().resolve("reports");
        Files.createDirectories(reportsDir);

        String timestamp = java.time.LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        Path reportPath = reportsDir.resolve(caseInfo.caseId() + "_report_" + timestamp + ".pdf");

        String script = """
from pathlib import Path
import sys
sys.path.insert(0, r"%s")
from main import combine_metadata
from modules.report_generator import generate_pdf_report
from modules.hashing import hash_directory_manifest

evidence = r"%s"
metadata = r"%s"
report = r"%s"
combined = combine_metadata(evidence)
manifest = hash_directory_manifest(evidence)
generate_pdf_report(
    combined_data=combined,
    output_path=report,
    manifest_data=manifest,
    case_id=r"%s",
    investigator=r"%s",
    top_n=20,
)
print(report)
""".formatted(
                Paths.get("../extractor").toAbsolutePath(),
                evidenceDir.toAbsolutePath(),
                metadataDir.toAbsolutePath(),
                reportPath.toAbsolutePath(),
                caseInfo.caseId(),
                investigator == null ? "" : investigator
        );

        String python = selectPythonExecutable();
        ProcessBuilder pb = new ProcessBuilder(List.of(python, "-c", script));
        pb.directory(Paths.get("../extractor").toFile());
        pb.redirectErrorStream(true);

        Process p = pb.start();
        String output = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        int exit = p.waitFor();
        if (exit != 0) {
            throw new IOException("Report generation failed: " + output);
        }
        return reportPath;
    }

    private String selectPythonExecutable() {
        Path venvPython = Paths.get("../extractor/.venv/bin/python");
        if (Files.exists(venvPython)) {
            return venvPython.toAbsolutePath().toString();
        }
        Path venvPython3 = Paths.get("../extractor/.venv/bin/python3");
        if (Files.exists(venvPython3)) {
            return venvPython3.toAbsolutePath().toString();
        }
        return "python3";
    }
}
