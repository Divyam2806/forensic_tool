package com.forensics.ui;

import com.forensics.casework.CaseManager;

import javax.swing.*;
import java.awt.*;
import java.io.IOException;
import java.util.List;

public class CaseDialog extends JDialog {
    public enum ActionType { CREATE, OPEN }

    private final JTextField caseIdField = new JTextField(12);
    private final JList<String> caseList = new JList<>();
    private String selectedCaseId;

    public CaseDialog(Frame owner, ActionType actionType, CaseManager caseManager) {
        super(owner, actionType == ActionType.CREATE ? "Create Case" : "Open Case", true);

        JButton confirmButton = new JButton(actionType == ActionType.CREATE ? "Create" : "Open");
        JButton cancelButton = new JButton("Cancel");

        confirmButton.addActionListener(e -> {
            String caseId = getSelectedCaseId(actionType);
            try {
                if (actionType == ActionType.CREATE) {
                    caseManager.createCase(caseId);
                } else {
                    caseManager.openCase(caseId);
                }
                selectedCaseId = caseId;
                dispose();
            } catch (IllegalArgumentException ex) {
                JOptionPane.showMessageDialog(this, ex.getMessage(), "Invalid case id", JOptionPane.ERROR_MESSAGE);
            } catch (IOException ex) {
                JOptionPane.showMessageDialog(this, ex.getMessage(), "Case error", JOptionPane.ERROR_MESSAGE);
            }
        });

        cancelButton.addActionListener(e -> {
            selectedCaseId = null;
            dispose();
        });

        JPanel form = new JPanel();
        form.setLayout(new BoxLayout(form, BoxLayout.Y_AXIS));
        form.setBorder(BorderFactory.createEmptyBorder(8, 8, 8, 8));

        JLabel hint = new JLabel(actionType == ActionType.CREATE
                ? "Enter a new case ID like CASE001"
                : "Choose an existing case or type one manually");
        hint.setForeground(new Color(108, 117, 125));

        JPanel fieldRow = new JPanel(new BorderLayout(10, 10));
        fieldRow.add(new JLabel("Case ID"), BorderLayout.WEST);
        fieldRow.add(caseIdField, BorderLayout.CENTER);

        form.add(hint);
        form.add(Box.createVerticalStrut(12));
        form.add(fieldRow);

        if (actionType == ActionType.OPEN) {
            List<String> cases;
            try {
                cases = caseManager.listCases();
            } catch (IOException ex) {
                cases = List.of();
            }

            caseList.setListData(cases.toArray(new String[0]));
            caseList.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
            caseList.setVisibleRowCount(6);
            caseList.addListSelectionListener(ev -> {
                if (!ev.getValueIsAdjusting()) {
                    String selected = caseList.getSelectedValue();
                    if (selected != null) {
                        caseIdField.setText(selected);
                    }
                }
            });

            JScrollPane listPane = new JScrollPane(caseList);
            listPane.setPreferredSize(new Dimension(260, 140));
            listPane.setBorder(BorderFactory.createTitledBorder("Existing cases"));

            form.add(Box.createVerticalStrut(12));
            form.add(listPane);
        }

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        buttons.add(cancelButton);
        buttons.add(confirmButton);

        JPanel content = new JPanel(new BorderLayout(10, 10));
        content.setBorder(BorderFactory.createEmptyBorder(16, 16, 16, 16));
        content.add(form, BorderLayout.CENTER);
        content.add(buttons, BorderLayout.SOUTH);

        setContentPane(content);
        setMinimumSize(new Dimension(460, actionType == ActionType.OPEN ? 360 : 220));
        pack();
        setLocationRelativeTo(owner);
        getRootPane().setDefaultButton(confirmButton);
    }

    private String getSelectedCaseId(ActionType actionType) {
        String caseId = caseIdField.getText().trim().toUpperCase();
        if (actionType == ActionType.OPEN && caseId.isBlank()) {
            caseId = caseList.getSelectedValue() != null ? caseList.getSelectedValue().trim().toUpperCase() : "";
        }
        return caseId;
    }

    public String showDialog() {
        setVisible(true);
        return selectedCaseId;
    }
}
