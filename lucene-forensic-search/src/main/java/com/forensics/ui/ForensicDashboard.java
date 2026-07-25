package com.forensics.ui;

import com.forensics.api.ForensicApiClient;
import com.forensics.casework.CaseInfo;
import com.forensics.casework.CaseMetadataExtractionService;
import org.json.JSONObject;
import javax.swing.SwingWorker;
import java.nio.file.Path;
import java.io.IOException;

import com.forensics.auth.Permission;
import com.forensics.auth.RolePermissions;
import com.forensics.auth.UserAccount;
import com.forensics.casework.CaseMetadataExtractionService;
import com.forensics.casework.CaseManager;
import com.forensics.casework.CaseServices;
import com.forensics.MetadataIndexer;
import com.forensics.report.CaseReportService;

import javax.swing.*;
import java.awt.*;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;

public class ForensicDashboard extends JFrame {
    private static final Color BG = new Color(242, 245, 249);
    private static final Color CARD = Color.WHITE;
    private static final Color ACCENT = new Color(31, 78, 121);
    private static final Color SOFT = new Color(108, 117, 125);

    private enum ActionKey {
        CREATE_CASE,
        OPEN_CASE,
        ACQUIRE_EVIDENCE,
        CREATE_DISK_IMAGE,
        EXTRACT_METADATA,
        INDEX_FILES,
        SEARCH_EVIDENCE,
        GENERATE_REPORT,
        VIEW_AUDIT_LOGS,
        ANALYZE_WITH_AI
    }

    private final UserAccount user;
    private final CaseManager caseManager;
    private final Map<ActionKey, JButton> buttons = new LinkedHashMap<>();
    private final JLabel activeCaseLabel = new JLabel("Active case: none");
    private final JLabel summaryLabel = new JLabel("Ready");
    private final CaseMetadataExtractionService extractionService = new CaseMetadataExtractionService();

    public ForensicDashboard(UserAccount user) {
        super("Forensic Toolkit - " + user.username() + " (" + user.role() + ")");
        this.user = user;
        this.caseManager = new CaseManager(Paths.get("cases"));
        buildUi();
        applyPermissions();
        refreshActiveCaseLabel();
    }

    private void buildUi() {
        setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
        setSize(1100, 720);
        setLocationRelativeTo(null);
        setMinimumSize(new Dimension(980, 640));

        JPanel root = new JPanel(new BorderLayout(16, 16));
        root.setBackground(BG);
        root.setBorder(BorderFactory.createEmptyBorder(18, 18, 18, 18));

        JPanel header = new JPanel(new BorderLayout(10, 4));
        header.setBackground(BG);
        JLabel title = new JLabel("Forensic Evidence Preservation & Cyber Forensics");
        title.setFont(title.getFont().deriveFont(Font.BOLD, 22f));
        title.setForeground(ACCENT);
        JLabel roleLabel = new JLabel("Logged in as: " + user.username() + "  |  Role: " + user.role());
        roleLabel.setForeground(SOFT);
        activeCaseLabel.setForeground(TEXT());
        header.add(title, BorderLayout.NORTH);
        header.add(roleLabel, BorderLayout.CENTER);
        header.add(activeCaseLabel, BorderLayout.SOUTH);

        JPanel cards = new JPanel(new GridLayout(0, 3, 14, 14));
        cards.setOpaque(false);
        cards.setBorder(BorderFactory.createEmptyBorder(4, 0, 0, 0));

        addCard(cards, ActionKey.CREATE_CASE, Permission.CREATE_CASE, "Create Case", "Start a new investigation case.");
        addCard(cards, ActionKey.OPEN_CASE, Permission.OPEN_CASE, "Open Case", "Resume an existing case folder.");
        addCard(cards, ActionKey.ACQUIRE_EVIDENCE, Permission.ACQUIRE_EVIDENCE, "Acquire Evidence", "Copy evidence into the active case.");
        addCard(cards, ActionKey.CREATE_DISK_IMAGE, Permission.CREATE_DISK_IMAGE, "Create Disk Image", "Generate a forensic image.");
        addCard(cards, ActionKey.EXTRACT_METADATA, Permission.EXTRACT_METADATA, "Extract Metadata", "Extract file and artifact metadata.");
        addCard(cards, ActionKey.INDEX_FILES, Permission.INDEX_FILES, "Index Files", "Build Lucene search indexes.");
        addCard(cards, ActionKey.SEARCH_EVIDENCE, Permission.SEARCH_EVIDENCE, "Search Evidence", "Search content and metadata.");
        addCard(cards, ActionKey.GENERATE_REPORT, Permission.GENERATE_REPORT, "Generate Report", "Create forensic PDF reports.");
        addCard(cards, ActionKey.VIEW_AUDIT_LOGS, Permission.VIEW_AUDIT_LOGS, "Audit Logs", "Inspect chain-of-custody trails.");
        addCard(cards, ActionKey.ANALYZE_WITH_AI, Permission.ANALYZE_WITH_AI, "AI Analysis", "Analyze metadata using local LLM model.");

        JPanel statusBar = new JPanel(new BorderLayout());
        statusBar.setBackground(CARD);
        statusBar.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(new Color(225, 229, 234), 1, true),
                BorderFactory.createEmptyBorder(10, 14, 10, 14)
        ));
        summaryLabel.setForeground(SOFT);
        statusBar.add(summaryLabel, BorderLayout.WEST);

        root.add(header, BorderLayout.NORTH);
        root.add(cards, BorderLayout.CENTER);
        root.add(statusBar, BorderLayout.SOUTH);

        setContentPane(root);
    }

    private void addCard(JPanel panel, ActionKey key, Permission requiredPermission, String title, String description) {
        JButton button = new JButton("<html><center><b>" + title + "</b><br/><span style='font-size:10px;'>" + description + "</span></center></html>");
        button.setHorizontalAlignment(SwingConstants.CENTER);
        button.setVerticalAlignment(SwingConstants.CENTER);
        button.setFocusPainted(false);
        button.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(new Color(217, 223, 229), 1, true),
                BorderFactory.createEmptyBorder(16, 16, 16, 16)
        ));
        button.setBackground(CARD);
        button.setOpaque(true);
        button.setContentAreaFilled(true);
        button.setRolloverEnabled(true);

        button.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override
            public void mouseEntered(java.awt.event.MouseEvent e) {
                if (button.isEnabled()) button.setBackground(new Color(248, 250, 252));
            }

            @Override
            public void mouseExited(java.awt.event.MouseEvent e) {
                if (button.isEnabled()) button.setBackground(CARD);
            }
        });

        if (key == ActionKey.CREATE_CASE) {
            button.addActionListener(e -> openCaseDialog(CaseDialog.ActionType.CREATE));
        } else if (key == ActionKey.OPEN_CASE) {
            button.addActionListener(e -> openCaseDialog(CaseDialog.ActionType.OPEN));
        } else if (key == ActionKey.ACQUIRE_EVIDENCE) {
            button.addActionListener(e -> openEvidenceAcquireDialog());
        } else if (key == ActionKey.CREATE_DISK_IMAGE) {
            button.addActionListener(e -> openDiskImageDialog());
        } else if (key == ActionKey.EXTRACT_METADATA) {
            button.addActionListener(e -> openMetadataExtraction());
        } else if (key == ActionKey.INDEX_FILES) {
            button.addActionListener(e -> indexCaseMetadata());
        } else if (key == ActionKey.SEARCH_EVIDENCE) {
            button.addActionListener(e -> openSearchDialog());
        } else if (key == ActionKey.GENERATE_REPORT) {
            button.addActionListener(e -> openReportDialog());
        } else if (key == ActionKey.ANALYZE_WITH_AI) {
            button.addActionListener(e -> openAiAnalysisDialog());
        }
        else {
            button.addActionListener(e -> JOptionPane.showMessageDialog(this,
                    "Module placeholder: " + title,
                    "Coming soon",
                    JOptionPane.INFORMATION_MESSAGE));
        }
        buttons.put(key, button);
        panel.add(button);
    }

    private void openCaseDialog(CaseDialog.ActionType actionType) {
        CaseDialog dialog = new CaseDialog(this, actionType, caseManager);
        String caseId = dialog.showDialog();
        if (caseId != null) {
            refreshActiveCaseLabel();
            JOptionPane.showMessageDialog(this,
                    "Case " + caseId + " is ready.\nStructure created under: " + caseManager.getCasesRoot().resolve(caseId),
                    "Case updated",
                    JOptionPane.INFORMATION_MESSAGE);
        }
    }

    private void openEvidenceAcquireDialog() {
        var active = caseManager.getActiveCase();
        if (active.isEmpty()) {
            JOptionPane.showMessageDialog(this,
                    "Please create or open a case first.",
                    "No active case",
                    JOptionPane.WARNING_MESSAGE);
            return;
        }

        EvidenceAcquireDialog dialog = new EvidenceAcquireDialog(this, active.get());
        boolean done = dialog.showDialog();
        if (done) {
            JOptionPane.showMessageDialog(this,
                    "Evidence copied into case " + active.get().caseId() + ".",
                    "Acquire complete",
                    JOptionPane.INFORMATION_MESSAGE);
        }
    }

    private void openDiskImageDialog() {
        var active = caseManager.getActiveCase();
        if (active.isEmpty()) {
            JOptionPane.showMessageDialog(this,
                    "Please create or open a case first.",
                    "No active case",
                    JOptionPane.WARNING_MESSAGE);
            return;
        }

        DiskImageDialog dialog = new DiskImageDialog(this, active.get());
        boolean done = dialog.showDialog();
        if (done) {
            JOptionPane.showMessageDialog(this,
                    "Disk image stored under case " + active.get().caseId() + "/images.",
                    "Imaging complete",
                    JOptionPane.INFORMATION_MESSAGE);
        }
    }

    private void openMetadataExtraction() {
        var active = caseManager.getActiveCase();
        if (active.isEmpty()) {
            JOptionPane.showMessageDialog(this,
                    "Please create or open a case first.",
                    "No active case",
                    JOptionPane.WARNING_MESSAGE);
            return;
        }

        CaseInfo caseInfo = active.get();

        // Check Python service is running before starting worker
        if (!extractionService.isServiceRunning()) {
            JOptionPane.showMessageDialog(this,
                    "Python forensic service is not running.\n" +
                    "Start it with: uvicorn api:app --host 127.0.0.1 --port 8000\n" +
                    "from the extractor/ directory.",
                    "Service Unavailable",
                    JOptionPane.ERROR_MESSAGE);
            return;
        }

        // Disable button to prevent double-click during scan
        buttons.get(ActionKey.EXTRACT_METADATA).setEnabled(false);

        SwingWorker<JSONObject, Void> worker = new SwingWorker<>() {

            @Override
            protected JSONObject doInBackground() throws Exception {
                // Runs on background thread — safe to do long operations here
                return extractionService.extractMetadata(caseInfo, 1000);
            }

            @Override
            protected void done() {
                // Runs back on EDT when doInBackground() finished
                buttons.get(ActionKey.EXTRACT_METADATA).setEnabled(true);
                try {
                    JSONObject result = get();
                    JOptionPane.showMessageDialog(
                            ForensicDashboard.this,
                            "Metadata extracted successfully.\n" +
                            "Files processed: " + result.getInt("total_files") + "\n" +
                            "Manifest hash: " + result.getString("manifest_hash"),
                            "Extraction Complete",
                            JOptionPane.INFORMATION_MESSAGE
                    );
                } catch (Exception ex) {
                    JOptionPane.showMessageDialog(
                            ForensicDashboard.this,
                            "Extraction failed: " + ex.getMessage(),
                            "Metadata Extraction Failed",
                            JOptionPane.ERROR_MESSAGE
                    );
                }
            }
        };

        worker.execute();
    }

    private void indexCaseMetadata() {
        var active = caseManager.getActiveCase();
        if (active.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Please create or open a case first.", "No active case", JOptionPane.WARNING_MESSAGE);
            return;
        }
        try {
            MetadataIndexer.main(new String[] {
                    CaseServices.metadataDir(active.get()).toString(),
                    CaseServices.indexDir(active.get()).toString()
            });
            JOptionPane.showMessageDialog(this,
                    "Case metadata indexed into " + CaseServices.indexDir(active.get()),
                    "Index complete",
                    JOptionPane.INFORMATION_MESSAGE);
        } catch (Exception ex) {
            JOptionPane.showMessageDialog(this, ex.getMessage(), "Indexing failed", JOptionPane.ERROR_MESSAGE);
        }
    }

    private void openSearchDialog() {
        var active = caseManager.getActiveCase();
        if (active.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Please create or open a case first.", "No active case", JOptionPane.WARNING_MESSAGE);
            return;
        }
        new CaseSearchDialog(this, active.get()).showDialog();
    }

    private void openReportDialog() {
        var active = caseManager.getActiveCase();
        if (active.isEmpty()) {
            JOptionPane.showMessageDialog(this,
                    "Please create or open a case first.",
                    "No active case",
                    JOptionPane.WARNING_MESSAGE);
            return;
        }

        String sessionId = extractionService.getCurrentSessionId();
        if (sessionId == null) {
            JOptionPane.showMessageDialog(this,
                    "No active extraction session.\n" +
                    "Please run Extract Metadata first.",
                    "No Session",
                    JOptionPane.WARNING_MESSAGE);
            return;
        }

        String investigator = user.username();
        ReportDialog dialog = new ReportDialog(this, active.get(), investigator, sessionId);
        boolean done = dialog.showDialog();
        if (done) {
            JOptionPane.showMessageDialog(this,
                    "Report generated in " + active.get().casePath().resolve("reports"),
                    "Report complete",
                    JOptionPane.INFORMATION_MESSAGE);
        }
    }

    private void refreshActiveCaseLabel() {
        var active = caseManager.getActiveCase();
        if (active.isPresent()) {
            activeCaseLabel.setText("Active case: " + active.get().caseId() + "   |   Root: " + active.get().casePath());
        } else {
            activeCaseLabel.setText("Active case: none");
        }
        summaryLabel.setText(activeCaseLabel.getText());
    }

    private void openAiAnalysisDialog() {
        var active = caseManager.getActiveCase();
        if (active.isEmpty()) {
            JOptionPane.showMessageDialog(this,
                    "Please create or open a case first.",
                    "No active case",
                    JOptionPane.WARNING_MESSAGE);
            return;
        }

        // Open file picker pointing at case metadata folder
        Path metadataDir;
        try {
            metadataDir = CaseServices.metadataDir(active.get());
        } catch (IOException ex) {
            JOptionPane.showMessageDialog(this,
                    "Could not resolve metadata directory: " + ex.getMessage(),
                    "Error",
                    JOptionPane.ERROR_MESSAGE);
            return;
        }

        JFileChooser fileChooser = new JFileChooser(metadataDir.toFile());
        fileChooser.setDialogTitle("Select Metadata File for AI Analysis");
        fileChooser.setFileFilter(new javax.swing.filechooser.FileNameExtensionFilter(
                "JSON files", "json"
        ));

        int result = fileChooser.showOpenDialog(this);
        if (result != JFileChooser.APPROVE_OPTION) return;

        Path selectedFile = fileChooser.getSelectedFile().toPath();

        buttons.get(ActionKey.ANALYZE_WITH_AI).setEnabled(false);

        SwingWorker<String, Void> worker = new SwingWorker<>() {

            @Override
            protected String doInBackground() throws Exception {
                ForensicApiClient apiClient = new ForensicApiClient();
                JSONObject result = apiClient.analyze(
                        selectedFile.toAbsolutePath().toString()
                );
                return result.toString(2); // pretty print JSON
            }

            @Override
            protected void done() {
                buttons.get(ActionKey.ANALYZE_WITH_AI).setEnabled(true);
                try {
                    String analysisResult = get();
                    JOptionPane.showMessageDialog(
                            ForensicDashboard.this,
                            analysisResult,
                            "AI Analysis Complete",
                            JOptionPane.INFORMATION_MESSAGE
                    );
                } catch (Exception ex) {
                    JOptionPane.showMessageDialog(
                            ForensicDashboard.this,
                            "AI analysis failed: " + ex.getMessage(),
                            "Error",
                            JOptionPane.ERROR_MESSAGE
                    );
                }
            }
        };

        worker.execute();
    }

    private void applyPermissions() {
        for (var entry : buttons.entrySet()) {
            boolean enabled = switch (entry.getKey()) {
                case CREATE_CASE -> RolePermissions.allows(user.role(), Permission.CREATE_CASE);
                case OPEN_CASE -> RolePermissions.allows(user.role(), Permission.OPEN_CASE);
                case ACQUIRE_EVIDENCE -> RolePermissions.allows(user.role(), Permission.ACQUIRE_EVIDENCE);
                case CREATE_DISK_IMAGE -> RolePermissions.allows(user.role(), Permission.CREATE_DISK_IMAGE);
                case EXTRACT_METADATA -> RolePermissions.allows(user.role(), Permission.EXTRACT_METADATA);
                case INDEX_FILES -> RolePermissions.allows(user.role(), Permission.INDEX_FILES);
                case SEARCH_EVIDENCE -> RolePermissions.allows(user.role(), Permission.SEARCH_EVIDENCE);
                case GENERATE_REPORT -> RolePermissions.allows(user.role(), Permission.GENERATE_REPORT);
                case VIEW_AUDIT_LOGS -> RolePermissions.allows(user.role(), Permission.VIEW_AUDIT_LOGS);
                case ANALYZE_WITH_AI -> RolePermissions.allows(user.role(), Permission.ANALYZE_WITH_AI);
            };
            entry.getValue().setEnabled(enabled);
            if (!enabled) {
                entry.getValue().setBackground(new Color(235, 238, 242));
                entry.getValue().setForeground(Color.GRAY);
            } else {
                entry.getValue().setForeground(TEXT());
            }
        }
    }

    private Color TEXT() {
        return new Color(33, 37, 41);
    }
}
