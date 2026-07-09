package com.forensics.ui;

import com.forensics.auth.UserAccount;

public final class Session {
    private static UserAccount currentUser;

    private Session() {
    }

    public static void setCurrentUser(UserAccount user) {
        currentUser = user;
    }

    public static UserAccount getCurrentUser() {
        return currentUser;
    }

    public static void clear() {
        currentUser = null;
    }
}
