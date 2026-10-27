package com.agentfactory.registry;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** Operational requests: only generated correlation UUID, allowlisted route, status and duration. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public final class RegistryRequestLoggingFilter extends OncePerRequestFilter {
    private static final Logger LOG = LoggerFactory.getLogger(RegistryRequestLoggingFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        // Ignore untrusted inbound X-Request-Id; no header/payload/JWT/subject/tenant logging.
        UUID requestId = UUID.randomUUID();
        String id = requestId.toString();
        response.setHeader("X-Request-Id", id);
        long start = System.nanoTime();
        boolean unhandled = false;
        MDC.put("request_id", id);
        try {
            chain.doFilter(request, response);
        } catch (IOException | ServletException | RuntimeException error) {
            unhandled = true;
            throw error;
        } finally {
            long elapsed = Math.max(0L, (System.nanoTime() - start) / 1_000_000L);
            int status = response.getStatus();
            if (unhandled && status < 500) status = 500;
            try {
                if (LOG.isInfoEnabled()) LOG.info("{}", RegistryTelemetry.eventLine(
                    requestId, request.getMethod(), request.getRequestURI(), status, elapsed));
            } finally {
                MDC.remove("request_id");
            }
        }
    }
}
