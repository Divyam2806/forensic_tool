package com.forensics.imaging;

import com.forensics.evidence.HashService;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class DiskImagingService {
    public record ImageResult(Path imagePath, String sourceHash, String imageHash, int exitCode, String output) {
    }

    public ImageResult createImage(Path sourcePath, Path imagePath) throws IOException, InterruptedException {
        if (sourcePath == null || !Files.exists(sourcePath)) {
            throw new IOException("Source path does not exist: " + sourcePath);
        }

        Files.createDirectories(imagePath.getParent());

        String sourceHash = Files.isRegularFile(sourcePath) ? HashService.sha256(sourcePath) : "unavailable";

        ProcessBuilder pb = new ProcessBuilder(List.of(
                "dd",
                "if=" + sourcePath.toAbsolutePath(),
                "of=" + imagePath.toAbsolutePath(),
                "bs=4M",
                "status=none"
        ));
        pb.redirectErrorStream(true);

        Process process = pb.start();
        String output = new String(process.getInputStream().readAllBytes());
        int exit = process.waitFor();
        if (exit != 0) {
            throw new IOException("dd failed with exit code " + exit + ": " + output);
        }

        String imageHash = Files.exists(imagePath) ? HashService.sha256(imagePath) : "unavailable";
        return new ImageResult(imagePath, sourceHash, imageHash, exit, output);
    }
}
