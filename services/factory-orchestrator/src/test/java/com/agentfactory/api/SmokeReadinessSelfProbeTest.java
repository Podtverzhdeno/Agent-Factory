package com.agentfactory.api;

import static org.junit.jupiter.api.Assertions.*;

import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

/** The trace probe is deliberately read-only, loopback-only and fail-closed. */
final class SmokeReadinessSelfProbeTest {
    @Test void bothAvailableLocalProbesPassWithoutCredentialsOrUserData() throws Exception {
        var requests=new AtomicInteger();
        var server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        for(String path:new String[]{"/persistencez","/schemaz"}) {
            server.createContext(path,exchange->{
                try {
                    requests.incrementAndGet();
                    assertEquals("GET",exchange.getRequestMethod());
                    assertNull(exchange.getRequestHeaders().getFirst("Authorization"));
                    assertNull(exchange.getRequestHeaders().getFirst("X-Tenant-Id"));
                    exchange.sendResponseHeaders(200,-1);
                } finally {exchange.close();}
            });
        }
        server.start();
        try {
            assertTrue(SmokeReadinessSelfProbe.checkLocalOnly(server.getAddress().getPort()));
            assertEquals(2,requests.get());
        } finally {server.stop(0);}
    }

    @Test void unavailableSqlProbeCannotBeReportedAsSuccess() throws Exception {
        var server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        server.createContext("/persistencez",e->{
            try {e.sendResponseHeaders(200,-1);} finally {e.close();}
        });
        server.createContext("/schemaz",e->{
            try {e.sendResponseHeaders(503,-1);} finally {e.close();}
        });
        server.start();
        try {
            assertFalse(SmokeReadinessSelfProbe.checkLocalOnly(server.getAddress().getPort()));
        } finally {server.stop(0);}
    }

    @Test void invalidOrClosedLoopbackPortsFailClosed() {
        assertFalse(SmokeReadinessSelfProbe.checkLocalOnly(-1));
        assertFalse(SmokeReadinessSelfProbe.checkLocalOnly(65536));
    }
}
