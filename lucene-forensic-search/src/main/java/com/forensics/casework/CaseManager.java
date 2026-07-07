package com.forensics.casework;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;

public class CaseManager {
    private static final Pattern CASE_ID = Pattern.compile("CASE\\d{3,}");

    private final Path casesRoot;
    private CaseInfo activeCase;

    public CaseManager(Path casesRoot) {
        this.casesRoot = casesRoot;
    }

    public Path getCasesRoot() {
        return casesRoot;
    }

    public Optional<CaseInfo> getActiveCase() {
        return Optional.ofNullable(activeCase);
    }

    public CaseInfo createCase(String caseId) throws IOException {
        validateCaseId(caseId);
        Path casePath = casesRoot.resolve(caseId);
        createStructure(casePath);
        activeCase = new CaseInfo(caseId, casePath);
        return activeCase;
    }

    public CaseInfo openCase(String caseId) throws IOException {
        validateCaseId(caseId);
        Path casePath = casesRoot.resolve(caseId);
        if (!Files.exists(casePath)) {
            throw new IOException("Case not found: " + caseId);
        }
        activeCase = new CaseInfo(caseId, casePath);
        return activeCase;
    }

    public List<String> listCases() throws IOException {
        if (!Files.exists(casesRoot)) {
            return List.of();
        }
        List<String> ids = new ArrayList<>();
        try (var stream = Files.list(casesRoot)) {
            stream.filter(Files::isDirectory)
                    .map(path -> path.getFileName().toString())
                    .filter(name -> CASE_ID.matcher(name).matches())
                    .sorted(Comparator.naturalOrder())
                    .forEach(ids::add);
        }
        return ids;
    }

    public static void createStructure(Path casePath) throws IOException {
        Files.createDirectories(casePath.resolve("evidence"));
        Files.createDirectories(casePath.resolve("metadata"));
        Files.createDirectories(casePath.resolve("index"));
        Files.createDirectories(casePath.resolve("reports"));
        Files.createDirectories(casePath.resolve("logs"));
        Files.createDirectories(casePath.resolve("images"));
    }

    public static void validateCaseId(String caseId) {
        if (caseId == null || !CASE_ID.matcher(caseId.trim()).matches()) {
            throw new IllegalArgumentException("Case ID must look like CASE001, CASE002, etc.");
        }
    }
}
