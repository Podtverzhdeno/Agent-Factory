package com.agentfactory.api;

import com.agentfactory.control.*;
import com.agentfactory.store.AgentStore;
import javax.sql.DataSource;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Opt-in, non-production PostgreSQL proof of concept. Only enable explicitly in an
 * isolated environment with schema V1 applied and an owner-approved test database.
 * Production service topology is not approved by ADR-0002.
 */
@Configuration
@Profile("jdbc-poc")
public class JdbcProofOfConceptConfiguration {
    /**
     * No default JDBC URL: only the isolated jdbc-poc profile can provision storage.
     * Configure spring.datasource.jdbc-url, username and password explicitly.
     */
    @Bean
    @ConfigurationProperties(prefix = "spring.datasource")
    HikariDataSource jdbcPocDataSource() {
        return new HikariDataSource();
    }

    @Bean JdbcTransactionScope jdbcControlPlaneTransactions(DataSource source) {
        return new JdbcTransactionScope(source);
    }
    @Bean JacksonStateCodec jdbcStateCodec(ObjectMapper mapper) { return new JacksonStateCodec(mapper); }
    @Bean @Primary Ports.WorkflowLedger jdbcWorkflowLedger(JdbcTransactionScope tx,JacksonStateCodec codec) {
        return new JdbcWorkflowLedger(tx,codec);
    }
    @Bean @Primary AgentStore jdbcAgentStore(JdbcTransactionScope tx,JacksonStateCodec codec) {
        return new JdbcAgentStore(tx,codec);
    }
}
