package com.forensics.audit;

import com.forensics.auth.UserAccount;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class ChainOfCustodyLogger {
    private final Path logFile;
    private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public ChainOfCustodyLogger(Path logFile) {
        this.logFile = logFile;
    }

    public synchronized void log(UserAccount user, String action, Path target) throws IOException {
        Files.createDirectories(logFile.getParent());
        String line = String.format(
                "%s | user=%s | role=%s | action=%s | target=%s%n",
                LocalDateTime.now().format(TS),
                user.username(),
                user.role(),
                action,
                target
        );
        Files.writeString(logFile, line, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }
}
