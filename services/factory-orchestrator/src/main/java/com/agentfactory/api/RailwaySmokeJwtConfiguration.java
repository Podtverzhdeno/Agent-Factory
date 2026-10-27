package com.agentfactory.api;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.security.oauth2.jwt.BadJwtException;
import org.springframework.security.oauth2.jwt.JwtDecoder;

/**
 * Internal Railway build/smoke profile only: no JWT can be accepted.
 * Never use this as a real identity provider; replace with a trusted issuer
 * and independently approved deployment profile after ADR ratification.
 */
@Configuration
@Profile("railway-smoke")
public class RailwaySmokeJwtConfiguration {
    @Bean
    JwtDecoder failClosedSmokeJwtDecoder() {
        return token -> {
            throw new BadJwtException("SMOKE_PROFILE_REJECTS_ALL_TOKENS");
        };
    }
}
