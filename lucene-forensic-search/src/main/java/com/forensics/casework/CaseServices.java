package com.forensics.casework;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public final class CaseServices {
    private CaseServices() {
    }

    public static Path metadataDir(CaseInfo caseInfo) throws IOException {
        Path dir = caseInfo.casePath().resolve("metadata");
        Files.createDirectories(dir);
        return dir;
    }

    public static Path indexDir(CaseInfo caseInfo) throws IOException {
        Path dir = caseInfo.casePath().resolve("index");
        Files.createDirectories(dir);
        return dir;
    }
}
