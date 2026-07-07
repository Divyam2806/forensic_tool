package com.forensics.ui;

import com.forensics.auth.UserAccount;
import com.forensics.auth.UserStore;

import javax.swing.*;
import java.awt.*;

public class LoginDialog extends JDialog {
    private static final Color BG = new Color(245, 247, 250);
    private static final Color CARD = Color.WHITE;
    private static final Color ACCENT = new Color(31, 78, 121);
    private static final Color TEXT = new Color(33, 37, 41);

    private final JTextField usernameField = new JTextField(16);
    private final JPasswordField passwordField = new JPasswordField(16);
    private UserAccount authenticatedUser;

    public LoginDialog(Frame owner, UserStore userStore) {
        super(owner, "Login", true);

        JButton loginButton = new JButton("Login");
        JButton cancelButton = new JButton("Cancel");

        loginButton.setBackground(ACCENT);
        loginButton.setForeground(Color.WHITE);
        loginButton.setFocusPainted(false);
        cancelButton.setFocusPainted(false);

        loginButton.addActionListener(e -> {
            String username = usernameField.getText().trim();
            String password = new String(passwordField.getPassword());
            authenticatedUser = userStore.authenticate(username, password).orElse(null);
            if (authenticatedUser == null) {
                JOptionPane.showMessageDialog(this, "Invalid username or password.", "Login failed", JOptionPane.ERROR_MESSAGE);
                return;
            }
            Session.setCurrentUser(authenticatedUser);
            dispose();
        });

        cancelButton.addActionListener(e -> {
            authenticatedUser = null;
            Session.clear();
            dispose();
        });

        JLabel title = new JLabel("Forensic Toolkit");
        title.setFont(title.getFont().deriveFont(Font.BOLD, 22f));
        title.setForeground(ACCENT);

        JLabel subtitle = new JLabel("Secure login for evidence, cases, and reports");
        subtitle.setForeground(new Color(108, 117, 125));

        JPanel form = new JPanel(new GridBagLayout());
        form.setOpaque(false);
        GridBagConstraints gc = new GridBagConstraints();
        gc.insets = new Insets(8, 8, 8, 8);
        gc.fill = GridBagConstraints.HORIZONTAL;
        gc.gridx = 0;
        gc.gridy = 0;
        form.add(new JLabel("Username"), gc);
        gc.gridx = 1;
        form.add(usernameField, gc);
        gc.gridx = 0;
        gc.gridy = 1;
        form.add(new JLabel("Password"), gc);
        gc.gridx = 1;
        form.add(passwordField, gc);

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        buttons.setOpaque(false);
        buttons.add(cancelButton);
        buttons.add(loginButton);

        JPanel card = new JPanel(new BorderLayout(10, 10));
        card.setBackground(CARD);
        card.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(new Color(225, 229, 234), 1, true),
                BorderFactory.createEmptyBorder(20, 20, 20, 20)
        ));
        card.add(title, BorderLayout.NORTH);
        card.add(subtitle, BorderLayout.CENTER);
        card.add(form, BorderLayout.SOUTH);

        JPanel root = new JPanel(new BorderLayout(10, 10));
        root.setBackground(BG);
        root.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));
        root.add(card, BorderLayout.CENTER);
        root.add(buttons, BorderLayout.SOUTH);

        setContentPane(root);
        pack();
        setResizable(false);
        setLocationRelativeTo(owner);
        getRootPane().setDefaultButton(loginButton);
        usernameField.requestFocusInWindow();
    }

    public UserAccount showDialog() {
        setVisible(true);
        return authenticatedUser;
    }
}
