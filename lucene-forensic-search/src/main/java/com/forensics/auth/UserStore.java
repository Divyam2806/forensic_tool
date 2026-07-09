package com.forensics.auth;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

public class UserStore {
    private final List<UserAccount> users;

    public UserStore(List<UserAccount> users) {
        this.users = users;
    }

    public static UserStore loadDefault() {
        try (InputStream in = UserStore.class.getResourceAsStream("/users.json")) {
            if (in == null) {
                return new UserStore(defaultUsers());
            }
            String json = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            return new UserStore(parse(json));
        } catch (Exception e) {
            return new UserStore(defaultUsers());
        }
    }

    public Optional<UserAccount> authenticate(String username, String password) {
        return users.stream()
                .filter(u -> u.username().equalsIgnoreCase(username) && u.password().equals(password))
                .findFirst();
    }

    private static List<UserAccount> parse(String json) {
        JSONArray arr = new JSONArray(json);
        List<UserAccount> parsed = new ArrayList<>();
        for (int i = 0; i < arr.length(); i++) {
            JSONObject obj = arr.getJSONObject(i);
            parsed.add(new UserAccount(
                    obj.getString("username"),
                    obj.getString("password"),
                    Role.valueOf(obj.getString("role").toUpperCase())
            ));
        }
        return parsed;
    }

    private static List<UserAccount> defaultUsers() {
        List<UserAccount> list = new ArrayList<>();
        list.add(new UserAccount("admin", "admin123", Role.ADMIN));
        list.add(new UserAccount("investigator", "invest123", Role.INVESTIGATOR));
        list.add(new UserAccount("analyst", "analyst123", Role.ANALYST));
        list.add(new UserAccount("auditor", "audit123", Role.AUDITOR));
        return list;
    }
}
