package com.forensics.ui;

import com.forensics.audit.ChainOfCustodyLogger;
import com.forensics.auth.UserAccount;
import com.forensics.casework.CaseInfo;
import com.forensics.evidence.EvidenceAcquisitionService;
import com.forensics.evidence.HashService;

import javax.swing.*;
import java.awt.*;
import java.nio.file.Path;

public class EvidenceAcquireDialog extends JDialog {
    private final JTextField sourceField = new JTextField(28);
    private final JCheckBox recursiveCheck = new JCheckBox("Include subfolders", true);
    private final JLabel statusLabel = new JLabel(" ");
    private boolean completed;

    public EvidenceAcquireDialog(Frame owner, CaseInfo activeCase) {
        super(owner, "Acquire Evidence", true);

        JButton browseButton = new JButton("Browse");
        JButton acquireButton = new JButton("Acquire");
        JButton cancelButton = new JButton("Cancel");

        browseButton.addActionListener(e -> chooseFolder(owner));

        acquireButton.addActionListener(e -> {
            try {
                String text = sourceField.getText().trim();
                if (text.isEmpty()) {
                    showStatus("Choose a source folder first.", true);
                    return;
                }
                Path source = Path.of(text);
                EvidenceAcquisitionService service = new EvidenceAcquisitionService();
                var result = service.acquireFolder(source, activeCase, recursiveCheck.isSelected());
                StringBuilder summary = new StringBuilder();
                summary.append("Copied ").append(result.copiedFiles().size()).append(" file(s).");
                if (!result.copiedFiles().isEmpty()) {
                    Path first = result.copiedFiles().get(0);
                    String hash = HashService.sha256(first);
                    summary.append(" SHA-256: ").append(hash.substring(0, Math.min(hash.length(), 16))).append("...");
                }
                showStatus(summary.toString(), false);
                if (!result.errors().isEmpty()) {
                    JOptionPane.showMessageDialog(this,
                            String.join("\n", result.errors()),
                            "Some files could not be copied",
                            JOptionPane.WARNING_MESSAGE);
                }
                logAcquisition(activeCase, source, result.copiedFiles().size());
                completed = true;
                dispose();
            } catch (Exception ex) {
                showStatus(ex.getMessage(), true);
            }
        });

        cancelButton.addActionListener(e -> {
            completed = false;
            dispose();
        });

        JPanel form = new JPanel(new GridBagLayout());
        form.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));
        GridBagConstraints gc = new GridBagConstraints();
        gc.insets = new Insets(8, 8, 8, 8);
        gc.fill = GridBagConstraints.HORIZONTAL;
        gc.gridy = 0;
        gc.gridx = 0;
        form.add(new JLabel("Source folder"), gc);
        gc.gridx = 1;
        form.add(sourceField, gc);
        gc.gridx = 2;
        form.add(browseButton, gc);

        gc.gridy = 1;
        gc.gridx = 1;
        gc.gridwidth = 2;
        form.add(recursiveCheck, gc);

        gc.gridy = 2;
        gc.gridx = 0;
        gc.gridwidth = 3;
        statusLabel.setForeground(new Color(108, 117, 125));
        form.add(statusLabel, gc);

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        buttons.add(cancelButton);
        buttons.add(acquireButton);

        JPanel root = new JPanel(new BorderLayout(10, 10));
        root.setBorder(BorderFactory.createEmptyBorder(16, 16, 16, 16));
        root.add(form, BorderLayout.CENTER);
        root.add(buttons, BorderLayout.SOUTH);

        setContentPane(root);
        setMinimumSize(new Dimension(640, 220));
        pack();
        setLocationRelativeTo(owner);
        getRootPane().setDefaultButton(acquireButton);
    }

    private void chooseFolder(Component owner) {
        JFileChooser chooser = new JFileChooser();
        chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
        chooser.setDialogTitle("Choose evidence source folder");
        if (chooser.showOpenDialog(owner) == JFileChooser.APPROVE_OPTION) {
            sourceField.setText(chooser.getSelectedFile().getAbsolutePath());
            showStatus("Ready to acquire from selected folder.", false);
        }
    }

    private void showStatus(String message, boolean error) {
        statusLabel.setText(message);
        statusLabel.setForeground(error ? new Color(180, 53, 53) : new Color(108, 117, 125));
    }

    private void logAcquisition(CaseInfo activeCase, Path source, int copiedCount) {
        try {
            UserAccount current = Session.getCurrentUser();
            if (current == null) {
                return;
            }
            ChainOfCustodyLogger logger = new ChainOfCustodyLogger(activeCase.casePath().resolve("logs").resolve("chain_of_custody.log"));
            logger.log(current,
                    "ACQUIRE_EVIDENCE copied=" + copiedCount + " source=" + source,
                    activeCase.casePath().resolve("evidence"));
        } catch (Exception ignored) {
        }
    }

    public boolean showDialog() {
        setVisible(true);
        return completed;
    }
}
