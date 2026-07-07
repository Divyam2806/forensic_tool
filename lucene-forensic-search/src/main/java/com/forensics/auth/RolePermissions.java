package com.forensics.auth;

import java.util.EnumSet;
import java.util.Set;

public final class RolePermissions {
    private RolePermissions() {
    }

    public static Set<Permission> permissionsFor(Role role) {
        return switch (role) {
            case ADMIN -> EnumSet.allOf(Permission.class);
            case INVESTIGATOR -> EnumSet.of(
                    Permission.ACQUIRE_EVIDENCE,
                    Permission.SEARCH_EVIDENCE,
                    Permission.CREATE_CASE,
                    Permission.OPEN_CASE,
                    Permission.CREATE_DISK_IMAGE,
                    Permission.EXTRACT_METADATA,
                    Permission.INDEX_FILES
            );
            case ANALYST -> EnumSet.of(
                    Permission.OPEN_CASE,
                    Permission.SEARCH_EVIDENCE,
                    Permission.GENERATE_REPORT,
                    Permission.EXTRACT_METADATA
            );
            case AUDITOR -> EnumSet.of(
                    Permission.VIEW_AUDIT_LOGS,
                    Permission.SEARCH_EVIDENCE
            );
        };
    }

    public static boolean allows(Role role, Permission permission) {
        return permissionsFor(role).contains(permission);
    }
}
