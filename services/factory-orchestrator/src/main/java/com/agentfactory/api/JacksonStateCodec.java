package com.agentfactory.api;

import com.agentfactory.control.JdbcAgentStore;
import com.agentfactory.control.JdbcWorkflowLedger;
import com.agentfactory.control.Workflow;
import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

/** Strict JSON snapshot codec; no Java object deserialization or polymorphic default typing. */
public final class JacksonStateCodec implements JdbcWorkflowLedger.Codec, JdbcAgentStore.Codec {
    private final ObjectMapper mapper;
    public JacksonStateCodec(ObjectMapper configuredMapper) {
        this.mapper=configuredMapper.copy()
            .setVisibility(PropertyAccessor.FIELD, JsonAutoDetect.Visibility.ANY)
            .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS)
            .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
    }
    @Override public String encode(Workflow workflow) { return write(workflow); }
    @Override public Workflow decode(String serialized) { return read(serialized,Workflow.class); }
    @Override public String write(Object record) {
        try { return mapper.writeValueAsString(record); }
        catch(JsonProcessingException error) { throw new IllegalStateException("PERSISTENCE_ENCODING_FAILED",error); }
    }
    @Override public <T> T read(String json,Class<T> type) {
        try { return mapper.readValue(json,type); }
        catch(JsonProcessingException error) { throw new IllegalStateException("PERSISTENCE_DECODING_FAILED",error); }
    }
}
