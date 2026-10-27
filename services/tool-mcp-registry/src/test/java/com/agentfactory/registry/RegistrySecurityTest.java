package com.agentfactory.registry;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class RegistrySecurityTest {
    @Test void rejectsUntrustedIssuerAndJwks() {
        assertDoesNotThrow(() -> RegistrySecurity.validateIdentityEndpoint(
            "https://auth.example.org/issuer", "https://auth.example.org/jwks", "agent-factory"));
        for (String url : new String[]{
            "http://auth.example.org/issuer", "https://127.0.0.1/token",
            "https://10.0.0.1/token", "https://localhost.local/issuer",
            "https://auth.internal/token", "https://auth.example.org:444/token",
            "https://user:password@auth.example.org/token",
            "https://auth.example.org/token?q=x"
        }) {
            assertThrows(IllegalArgumentException.class,
                () -> RegistrySecurity.validateIdentityEndpoint(url, url, "agent-factory"), url);
        }
        assertThrows(IllegalArgumentException.class,
            () -> RegistrySecurity.validateIdentityEndpoint(
                "https://auth.example.org/issuer", "https://different.example.org/jwks", "agent-factory"));
        assertThrows(IllegalArgumentException.class,
            () -> RegistrySecurity.validateIdentityEndpoint(
                "https://auth.example.org/issuer", "https://auth.example.org/jwks", ""));
    }
}
