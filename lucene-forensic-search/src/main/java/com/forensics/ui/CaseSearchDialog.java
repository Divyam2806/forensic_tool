package com.forensics.ui;

import com.forensics.SearchFiles;
import com.forensics.casework.CaseInfo;

import javax.swing.*;
import java.awt.*;
import java.nio.file.Path;
import java.util.List;

public class CaseSearchDialog extends JDialog {
    private final JTextField queryField = new JTextField(28);
    private final JTextArea resultsArea = new JTextArea(18, 60);
    private final CaseInfo caseInfo;

    public CaseSearchDialog(Frame owner, CaseInfo caseInfo) {
        super(owner, "Search Evidence", true);
        this.caseInfo = caseInfo;

        JButton searchButton = new JButton("Search");
        JButton closeButton = new JButton("Close");

        searchButton.addActionListener(e -> runSearch());
        closeButton.addActionListener(e -> dispose());

        JPanel top = new JPanel(new BorderLayout(8, 8));
        top.add(new JLabel("Search query"), BorderLayout.WEST);
        top.add(queryField, BorderLayout.CENTER);
        top.add(searchButton, BorderLayout.EAST);

        resultsArea.setEditable(false);
        resultsArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
        JScrollPane scroll = new JScrollPane(resultsArea);
        scroll.setBorder(BorderFactory.createTitledBorder("Results"));

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        buttons.add(closeButton);

        JPanel root = new JPanel(new BorderLayout(10, 10));
        root.setBorder(BorderFactory.createEmptyBorder(16, 16, 16, 16));
        root.add(top, BorderLayout.NORTH);
        root.add(scroll, BorderLayout.CENTER);
        root.add(buttons, BorderLayout.SOUTH);

        setContentPane(root);
        setMinimumSize(new Dimension(800, 520));
        pack();
        setLocationRelativeTo(owner);
        getRootPane().setDefaultButton(searchButton);
    }

    private void runSearch() {
        try {
            String q = queryField.getText().trim();
            if (q.isEmpty()) {
                resultsArea.setText("Enter a query first.");
                return;
            }
            Path indexPath = caseInfo.casePath().resolve("index");
            List<org.apache.lucene.document.Document> docs = SearchFiles.search(indexPath, q, 20);
            if (docs.isEmpty()) {
                resultsArea.setText("No matches found.");
                return;
            }
            StringBuilder sb = new StringBuilder();
            for (var doc : docs) {
                sb.append("==================================\n");
                for (var field : doc.getFields()) {
                    String value = doc.get(field.name());
                    if (value != null) {
                        sb.append(field.name()).append(" : ").append(value).append('\n');
                    }
                }
            }
            resultsArea.setText(sb.toString());
            resultsArea.setCaretPosition(0);
        } catch (Exception ex) {
            resultsArea.setText("Search error: " + ex.getMessage());
        }
    }

    public void showDialog() {
        setVisible(true);
    }
}
