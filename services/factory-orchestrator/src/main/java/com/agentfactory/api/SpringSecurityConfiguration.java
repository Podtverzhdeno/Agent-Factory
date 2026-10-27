package com.agentfactory.api;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

/** API is authenticated by validated JWT, never client-supplied tenant headers. */
@Configuration
public class SpringSecurityConfiguration {
    @Bean SecurityFilterChain apiSecurity(HttpSecurity http) throws Exception {
        return http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(HttpMethod.GET, "/healthz").permitAll()
                .requestMatchers(HttpMethod.GET, "/persistencez").permitAll()
                .requestMatchers(HttpMethod.GET, "/schemaz").permitAll()
                .requestMatchers(HttpMethod.POST, "/internal/events/build").hasAuthority("SCOPE_factory:events:build")
                .requestMatchers(HttpMethod.POST, "/internal/events/evaluation").hasAuthority("SCOPE_factory:events:evaluation")
                .requestMatchers(HttpMethod.POST, "/internal/events/optimization").hasAuthority("SCOPE_factory:events:optimization")
                .requestMatchers(HttpMethod.POST, "/internal/events/soup").hasAuthority("SCOPE_factory:events:soup")
                .requestMatchers("/v1/workflows/**").authenticated()
                .anyRequest().denyAll())
            .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> {}))
            .build();
    }
}
