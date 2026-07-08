package com.forensics.evidence;

import com.forensics.casework.CaseInfo;
import com.forensics.ui.Session;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

public class EvidenceAcquisitionService {
    public record AcquisitionResult(List<Path> copiedFiles, List<String> errors) {
    }

    public AcquisitionResult acquireFolder(Path sourceFolder, CaseInfo caseInfo, boolean recursive) throws IOException {
        if (sourceFolder == null || !Files.exists(sourceFolder) || !Files.isDirectory(sourceFolder)) {
            throw new IOException("Source folder does not exist: " + sourceFolder);
        }
        if (caseInfo == null) {
            throw new IOException("No active case selected.");
        }

        Path targetRoot = caseInfo.casePath().resolve("evidence");
        if (sourceFolder.normalize().startsWith(targetRoot.normalize())) {
            throw new IOException("Source folder cannot be inside the case evidence folder.");
        }
        Files.createDirectories(targetRoot);

        List<Path> copied = new ArrayList<>();
        List<String> errors = new ArrayList<>();

        if (recursive) {
            Files.walkFileTree(sourceFolder, new SimpleFileVisitor<>() {
                @Override
                public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) throws IOException {
                    Path relative = sourceFolder.relativize(dir);
                    Path targetDir = targetRoot.resolve(relative);
                    Files.createDirectories(targetDir);
                    return FileVisitResult.CONTINUE;
                }

                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                    try {
                        Path relative = sourceFolder.relativize(file);
                        Path targetFile = targetRoot.resolve(relative);
                        copyPreservingMetadata(file, targetFile);
                        copied.add(targetFile);
                    } catch (IOException ex) {
                        errors.add(file + " -> " + ex.getMessage());
                    }
                    return FileVisitResult.CONTINUE;
                }
            });
        } else {
            try (DirectoryStream<Path> stream = Files.newDirectoryStream(sourceFolder)) {
                for (Path file : stream) {
                    if (Files.isRegularFile(file)) {
                        try {
                            Path targetFile = targetRoot.resolve(file.getFileName());
                            copyPreservingMetadata(file, targetFile);
                            copied.add(targetFile);
                        } catch (IOException ex) {
                            errors.add(file + " -> " + ex.getMessage());
                        }
                    }
                }
            }
        }

        return new AcquisitionResult(copied, errors);
    }

    private void copyPreservingMetadata(Path source, Path target) throws IOException {
        Files.createDirectories(target.getParent());
        Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.COPY_ATTRIBUTES);
    }
}
