package com.forensics;

import com.forensics.auth.UserAccount;
import com.forensics.auth.UserStore;
import com.forensics.ui.ForensicDashboard;
import com.forensics.ui.LoginDialog;

import javax.swing.*;

public class ForensicApp {
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            UserStore userStore = UserStore.loadDefault();
            LoginDialog login = new LoginDialog(null, userStore);
            UserAccount user = login.showDialog();
            if (user == null) {
                System.exit(0);
            }
            new ForensicDashboard(user).setVisible(true);
        });
    }
}
