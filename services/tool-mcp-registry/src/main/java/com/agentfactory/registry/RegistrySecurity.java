package com.agentfactory.registry;

import java.net.URI;
import java.util.Locale;
import java.util.regex.Pattern;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Qualifier;
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
    JwtDecoder registryJwtDecoder(@Value("${registry.security.issuer-uri}") String issuer,
                       @Value("${registry.security.jwk-set-uri}") String jwks,
                       @Value("${registry.security.audience}") String audience) {
        validateIdentityEndpoint(issuer, jwks, audience);
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withJwkSetUri(jwks).build();
        OAuth2TokenValidator<Jwt> validated = new DelegatingOAuth2TokenValidator<>(
            JwtValidators.createDefaultWithIssuer(issuer),
            token -> token.getAudience().contains(audience)
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "Wrong audience", null)));
        decoder.setJwtValidator(validated);
        return decoder;
    }
    static void validateIdentityEndpoint(String issuer, String jwks, String audience) {
        try {
            URI issuerUri = URI.create(issuer);
            URI jwksUri = URI.create(jwks);
            String hostname = issuerUri.getHost();
            if (!"https".equals(issuerUri.getScheme()) || !"https".equals(jwksUri.getScheme())
                || hostname == null || !hostname.equalsIgnoreCase(jwksUri.getHost())
                || !Pattern.matches("[a-zA-Z0-9-]+(\\.[a-zA-Z0-9-]+)+", hostname)
                || hostname.matches("[0-9.]+")
                || hostname.toLowerCase(Locale.ROOT).endsWith(".local")
                || hostname.toLowerCase(Locale.ROOT).endsWith(".internal")
                || hostname.toLowerCase(Locale.ROOT).endsWith(".localhost")
                || issuerUri.getUserInfo() != null || jwksUri.getUserInfo() != null
                || issuerUri.getQuery() != null || jwksUri.getQuery() != null
                || issuerUri.getFragment() != null || jwksUri.getFragment() != null
                || !validPort(issuerUri) || !validPort(jwksUri)
                || audience == null || audience.isBlank())
                throw new IllegalArgumentException("Untrusted issuer or JWKS configuration");
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Untrusted issuer or JWKS configuration", e);
        }
    }
    private static boolean validPort(URI uri) { return uri.getPort() == -1 || uri.getPort() == 443; }

    @Bean
    SecurityFilterChain filter(HttpSecurity http,
                               @Qualifier("registryJwtDecoder") ObjectProvider<JwtDecoder> decoder,
                               @Value("${registry.security.issuer-uri:}") String issuer,
                               @Value("${registry.security.jwk-set-uri:}") String jwks,
                               @Value("${registry.security.audience:}") String audience) throws Exception {
        http.csrf(AbstractHttpConfigurer::disable)
            .httpBasic(AbstractHttpConfigurer::disable)
            .formLogin(AbstractHttpConfigurer::disable);
        if (issuer.isBlank() || jwks.isBlank() || audience.isBlank() || decoder.getIfAvailable() == null) {
            http.authorizeHttpRequests(auth -> auth.anyRequest().denyAll());
        } else {
            http.authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
                .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> jwt.decoder(decoder.getObject())));
        }
        return http.build();
    }
}
