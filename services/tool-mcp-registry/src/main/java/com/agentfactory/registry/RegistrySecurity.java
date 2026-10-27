package com.agentfactory.registry;

import java.util.List;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.oauth2.core.*;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.security.web.SecurityFilterChain;

/** Closed by default. Deployment needs pinned issuer + audience + trusted JWKS before any REST endpoint can be reached. */
@Configuration
public class RegistrySecurity {
    @Bean
    @ConditionalOnProperty(name={"registry.security.issuer-uri", "registry.security.jwk-set-uri", "registry.security.audience"})
    JwtDecoder decoder(@Value("${registry.security.issuer-uri}") String issuer,
                       @Value("${registry.security.jwk-set-uri}") String jwks,
                       @Value("${registry.security.audience}") String audience) {
        if (!issuer.startsWith("https://") || !jwks.startsWith("https://") || audience.isBlank())
            throw new IllegalArgumentException("Secure issuer, JWKS and nonblank audience required");
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withJwkSetUri(jwks).build();
        OAuth2TokenValidator<Jwt> validated = new DelegatingOAuth2TokenValidator<>(
            JwtValidators.createDefaultWithIssuer(issuer),
            token -> token.getAudience().contains(audience)
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "Wrong audience", null)));
        decoder.setJwtValidator(validated);
        return decoder;
    }
    @Bean
    SecurityFilterChain filter(HttpSecurity http, ObjectProvider<JwtDecoder> decoder) throws Exception {
        http.csrf(AbstractHttpConfigurer::disable)
            .httpBasic(AbstractHttpConfigurer::disable)
            .formLogin(AbstractHttpConfigurer::disable);
        if (decoder.getIfAvailable() == null) {
            http.authorizeHttpRequests(auth -> auth.anyRequest().denyAll());
        } else {
            http.authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
                .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> {}));
        }
        return http.build();
    }
}
