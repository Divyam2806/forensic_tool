package com.forensics.ui;

import com.forensics.casework.CaseInfo;
import com.forensics.report.CaseReportService;

import javax.swing.*;
import java.awt.*;
import java.nio.file.Path;

public class ReportDialog extends JDialog {

    private final JTextField investigatorField = new JTextField(20);
    private final JLabel     statusLabel       = new JLabel(" ");
    private final JButton    generateButton    = new JButton("Generate");
    private boolean completed;

    public ReportDialog(Frame owner, CaseInfo activeCase,
                        String defaultInvestigator, String sessionId) {
        super(owner, "Generate Report", true);

        if (defaultInvestigator != null) {
            investigatorField.setText(defaultInvestigator);
        }

        JButton cancelButton = new JButton("Cancel");

        generateButton.addActionListener(e -> {
            String investigator = investigatorField.getText().trim();
            generateButton.setEnabled(false);
            statusLabel.setForeground(Color.DARK_GRAY);
            statusLabel.setText("Generating report...");

            SwingWorker<Path, Void> worker = new SwingWorker<>() {

                @Override
                protected Path doInBackground() throws Exception {
                    return new CaseReportService().generateReport(
                            activeCase, investigator, sessionId
                    );
                }

                @Override
                protected void done() {
                    generateButton.setEnabled(true);
                    try {
                        Path result = get();
                        statusLabel.setText("Report created at: " + result);
                        completed = true;
                        JOptionPane.showMessageDialog(
                                ReportDialog.this,
                                "Report generated:\n" + result,
                                "Report Complete",
                                JOptionPane.INFORMATION_MESSAGE
                        );
                        dispose();
                    } catch (Exception ex) {
                        statusLabel.setForeground(new Color(180, 53, 53));
                        statusLabel.setText(ex.getMessage());
                    }
                }
            };

            worker.execute();
        });

        cancelButton.addActionListener(e -> dispose());

        JPanel form = new JPanel(new GridBagLayout());
        GridBagConstraints gc = new GridBagConstraints();
        gc.insets = new Insets(8, 8, 8, 8);
        gc.fill = GridBagConstraints.HORIZONTAL;

        gc.gridx = 0; gc.gridy = 0;
        form.add(new JLabel("Investigator"), gc);
        gc.gridx = 1;
        form.add(investigatorField, gc);

        gc.gridx = 0; gc.gridy = 1; gc.gridwidth = 2;
        form.add(statusLabel, gc);

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        buttons.add(cancelButton);
        buttons.add(generateButton);

        JPanel root = new JPanel(new BorderLayout(10, 10));
        root.setBorder(BorderFactory.createEmptyBorder(16, 16, 16, 16));
        root.add(form, BorderLayout.CENTER);
        root.add(buttons, BorderLayout.SOUTH);
        setContentPane(root);
        pack();
        setLocationRelativeTo(owner);
    }

    public boolean showDialog() {
        setVisible(true);
        return completed;
    }
}