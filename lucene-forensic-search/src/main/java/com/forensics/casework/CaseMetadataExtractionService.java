package com.forensics.casework;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

public class CaseMetadataExtractionService {
    public void extractMetadata(CaseInfo caseInfo) throws IOException, InterruptedException {
        Path evidenceDir = caseInfo.casePath().resolve("evidence");
        Path metadataDir = CaseServices.metadataDir(caseInfo);
        Files.createDirectories(metadataDir);

        String script = """
import json
from pathlib import Path
from modules.fs_metadata import scan_directory
from modules.file_metadata import extract_format_metadata

path = r"%s"
out = Path(r"%s")
fs_result = scan_directory(path, recursive=True, max_files=100000)
records = []
for fs_entry in fs_result.get("files", []):
    merged = dict(fs_entry)
    try:
        extra = extract_format_metadata(fs_entry["path"])
        for k, v in extra.items():
            if k not in merged:
                merged[k] = v
    except Exception as exc:
        merged["extract_error"] = str(exc)
    records.append(merged)
out.mkdir(parents=True, exist_ok=True)
for record in records:
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in record.get("name", "record"))
    with open(out / f"{safe_name}.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, default=str)
print(len(records))
""".formatted(evidenceDir.toAbsolutePath(), metadataDir.toAbsolutePath());

        String python = selectPythonExecutable();

        ProcessBuilder pb = new ProcessBuilder(List.of(
                python,
                "-c",
                script
        ));
        pb.directory(Path.of("../extractor").toFile());
        pb.redirectErrorStream(true);
        Process p = pb.start();
        String output = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        int exit = p.waitFor();
        if (exit != 0) {
            throw new IOException("Metadata extraction failed: " + output);
        }
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
