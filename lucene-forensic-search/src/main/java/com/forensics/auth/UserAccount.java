package com.forensics.auth;

public record UserAccount(String username, String password, Role role) {
}
