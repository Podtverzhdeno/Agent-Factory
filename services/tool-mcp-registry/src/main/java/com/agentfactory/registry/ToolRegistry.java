package com.agentfactory.registry;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/** Contract-first, in-memory trusted registry. No network access, MCP execution, or permissions issuance. */
public final class ToolRegistry {
    public enum Transport { LOCAL, MCP }
    public enum Risk { LOW, MEDIUM, HIGH, CRITICAL }
    public enum Effect { READ, DRAFT_FILE, WRITE, PAYMENT, DESTRUCTIVE }
    public enum FieldType { STRING, NUMBER, BOOLEAN, OBJECT, ARRAY }
    public enum Health { HEALTHY, DEGRADED, UNKNOWN }
    public enum Status { DRAFT, APPROVED, REVOKED }
    public enum Decision { SELECTED, BLOCKED }
    public enum DenialCode { NO_CAPABILITY, NOT_APPROVED, WRONG_TENANT, MISSING_PERMISSION,
        EFFECT_NOT_ALLOWED, RISK_NOT_ALLOWED, SCHEMA_INCOMPATIBLE, VERSION_INCOMPATIBLE,
        ENDPOINT_UNVERIFIED, UNHEALTHY, SEARCH_LIMIT, INCOMPATIBLE_VERSIONS, REVOKED }

    private static final Pattern IDENTIFIER = Pattern.compile("[a-zA-Z][a-zA-Z0-9_.:-]{0,127}");
    private static final Pattern SEMVER = Pattern.compile("(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?");
    private static final Pattern REF = Pattern.compile("artifact://schemas/[A-Za-z0-9._/-]+", Pattern.CASE_INSENSITIVE);
    private static final Pattern ENDPOINT = Pattern.compile("artifact://approved/endpoints/[a-zA-Z0-9._/-]+");
    private static final Pattern SCOPE = Pattern.compile("[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*");
    private static final Pattern INJECTION = Pattern.compile("(?i)(ignore (all |any )?(previous|system|developer)|system prompt|developer message|send (me |all )?(secrets|passwords|tokens)|exfiltrat|\\bapi[_ -]?key\\b|<\\|im_(start|end)\\|>|\\[inst\\]|\\{\\{.*\\}\\}|https?://|\\bBearer\\s|\\bBEGIN (RSA |OPENSSH )?PRIVATE KEY\\b)");
    private static final int MAX_CANDIDATES = 256;
    private static final int MAX_CAPABILITIES = 16;
    private static final int MAX_COLLECTION_SIZE = 512;
    private static final int MAX_MANIFESTS = 10_000;

    /** Recursive, closed-by-default structural schema. This is NOT the JSON Schema standard. */
    public record FieldSpec(FieldType type, Shape objectShape, FieldSpec arrayItem) {
        public FieldSpec {
            Objects.requireNonNull(type, "field type");
            if (type == FieldType.OBJECT ? objectShape == null : objectShape != null)
                throw failure("INVALID_SCHEMA", "Object fields need an object schema");
            if (type == FieldType.ARRAY ? arrayItem == null : arrayItem != null)
                throw failure("INVALID_SCHEMA", "Array fields need an item schema");
        }
        public static FieldSpec scalar(FieldType type) { return new FieldSpec(type, null, null); }
        public static FieldSpec object(Shape shape) { return new FieldSpec(FieldType.OBJECT, shape, null); }
        public static FieldSpec array(FieldSpec item) { return new FieldSpec(FieldType.ARRAY, null, item); }
    }
    public record Shape(Map<String, FieldSpec> fields, Set<String> required, boolean additionalProperties) {
        public Shape {
            Objects.requireNonNull(fields); Objects.requireNonNull(required);
            fields = Map.copyOf(fields); required = Set.copyOf(required);
            if (fields.isEmpty() || fields.size() > MAX_COLLECTION_SIZE
                || !fields.keySet().stream().allMatch(k -> IDENTIFIER.matcher(k).matches())
                || fields.values().stream().anyMatch(Objects::isNull) || !fields.keySet().containsAll(required))
                throw failure("INVALID_SCHEMA", "Invalid closed typed-object schema");
            if (additionalProperties) throw failure("INVALID_SCHEMA", "Open schemas are not trusted");
        }
    }
    public record Caller(String subject, String tenantId, Set<String> scopes) {
        public Caller {
            if (blank(subject) || blank(tenantId) || !valid(tenantId) || subject.length() > 200
                || subject.codePoints().anyMatch(c -> Character.isISOControl(c)
                    || c == 0x202A || c == 0x202B || c == 0x202D || c == 0x202E || c == 0x2066
                    || c == 0x2067 || c == 0x2068 || c == 0x2069))
                throw failure("UNAUTHENTICATED", "Valid bounded caller identity required");
            scopes = Set.copyOf(Objects.requireNonNull(scopes));
        }
        public boolean has(String scope) { return scopes.contains(scope); }
    }
    public record Manifest(String schemaVersion, String toolId, String version, String operation,
                           Transport transport, Set<String> capabilities, String inputSchemaRef,
                           String outputSchemaRef, Set<Effect> sideEffects, Set<String> requiredScopes,
                           Risk riskLevel, Set<String> tenantAvailability, String endpointRef, Health health,
                           String provenance, String description, String manifestDigest) {
        public Manifest {
            capabilities = Set.copyOf(Objects.requireNonNull(capabilities));
            sideEffects = Set.copyOf(Objects.requireNonNull(sideEffects));
            requiredScopes = Set.copyOf(Objects.requireNonNull(requiredScopes));
            tenantAvailability = Set.copyOf(Objects.requireNonNull(tenantAvailability));
        }
        public Manifest withComputedDigest() {
            return new Manifest(schemaVersion, toolId, version, operation, transport, capabilities,
                inputSchemaRef, outputSchemaRef, sideEffects, requiredScopes, riskLevel,
                tenantAvailability, endpointRef, health, provenance, description, digest(this));
        }
    }
    public record Requirement(String inputSchemaRef, String outputSchemaRef) {}
    public record SelectionRequest(Set<String> requiredCapabilities, Set<Effect> allowedEffects,
                                   Risk maxRisk, Map<String, String> pinnedVersions,
                                   Map<String, Requirement> expectedSchemas) {
        public SelectionRequest {
            requiredCapabilities = Set.copyOf(Objects.requireNonNull(requiredCapabilities));
            allowedEffects = Set.copyOf(Objects.requireNonNull(allowedEffects));
            pinnedVersions = Map.copyOf(Objects.requireNonNull(pinnedVersions));
            expectedSchemas = Map.copyOf(Objects.requireNonNull(expectedSchemas));
            Objects.requireNonNull(maxRisk);
        }
    }
    public record Binding(String toolId, String version, String operation, String manifestDigest,
                          Set<String> grantedScopes, Set<String> coveredCapabilities, String explanation) {}
    public record Denial(String capability, String toolId, DenialCode code, String reason) {}
    public record Selection(Decision decision, String registryRevision, List<Binding> selectedTools,
                            List<Denial> denials, String explanation) {}
    public record AuditEvent(long sequence, String tenantId, String action, String toolId,
                             String version, String operation, String actor, String digest) {}
    // Actual throwable: typed domain error without leaking untrusted manifest text.
    public static final class RegistryFailure extends RuntimeException {
        private static final long serialVersionUID = 1L;
        public final String code;
        public RegistryFailure(String code, String detail) { super(detail); this.code = code; }
    }
    private static RegistryFailure failure(String code, String detail) { return new RegistryFailure(code, detail); }
    /** Tenant identity is part of the immutable catalog key; tenants may reuse public tool IDs safely. */
    private record Key(String tenantId, String id, String version, String operation) implements Comparable<Key> {
        @Override public int compareTo(Key other) {
            int result = tenantId.compareTo(other.tenantId);
            if (result != 0) return result;
            result = id.compareTo(other.id);
            if (result != 0) return result;
            result = version.compareTo(other.version);
            return result != 0 ? result : operation.compareTo(other.operation);
        }
    }
    private record Entry(Manifest manifest, String creator, Status status, String approver) {}
    private final SortedMap<Key, Entry> records = new TreeMap<>();
    private final List<AuditEvent> audit = new ArrayList<>();
    private final Map<String, Long> auditSequences = new HashMap<>();
    private final Map<String, Shape> approvedSchemas;
    private final Set<String> verifiedEndpointRefs;
    private final Set<String> verifiedProvenanceRefs;

    /** References are supplied by an independent trust administrator, never learned from incoming manifests. */
    public ToolRegistry(Map<String, Shape> approvedSchemas, Set<String> verifiedEndpointRefs,
                        Set<String> verifiedProvenanceRefs) {
        this.approvedSchemas = Map.copyOf(approvedSchemas);
        this.verifiedEndpointRefs = Set.copyOf(verifiedEndpointRefs);
        this.verifiedProvenanceRefs = Set.copyOf(verifiedProvenanceRefs);
        for (String ref : approvedSchemas.keySet()) if (!REF.matcher(ref).matches()) throw failure("INVALID_SCHEMA_REF", "Schema reference is not approved artifact URI");
        for (String ref : verifiedEndpointRefs) if (!ENDPOINT.matcher(ref).matches()) throw failure("INVALID_ENDPOINT", "Endpoint reference must be approved artifact URI");
        for (String ref : verifiedProvenanceRefs)
            if (!validProvenance(ref)) throw failure("UNTRUSTED_PROVENANCE", "Invalid trust-provenance identifier");
    }
    public synchronized void registerDraft(Caller caller, Manifest manifest) {
        require(caller, "registry:register");
        if (manifest == null) throw failure("INVALID_MANIFEST", "Manifest required");
        // Authorization precedes validation: avoid cross-tenant schema/endpoint side channels.
        if (!manifest.tenantAvailability().equals(Set.of(caller.tenantId())))
            throw failure("FORBIDDEN", "Only own-tenant registration is permitted");
        validate(manifest);
        long count = records.keySet().stream().filter(key -> key.tenantId().equals(caller.tenantId())).count();
        if (count >= MAX_MANIFESTS) throw failure("CAPACITY_EXCEEDED", "Tenant registry capacity reached");
        Key key = key(caller.tenantId(), manifest);
        if (records.containsKey(key)) throw failure("VERSION_EXISTS", "Tool operation version is immutable");
        records.put(key, new Entry(manifest, caller.subject(), Status.DRAFT, null));
        audit(caller, "REGISTERED", manifest);
    }
    public synchronized void approve(Caller caller, String toolId, String version, String operation) {
        require(caller, "registry:approve");
        requireCoordinates(toolId, version, operation);
        Key key = new Key(caller.tenantId(), toolId, version, operation); Entry entry = records.get(key);
        if (entry == null) throw failure("NOT_FOUND", "Unknown manifest version");
        if (!entry.manifest().tenantAvailability().contains(caller.tenantId())) throw failure("FORBIDDEN", "Approver is not in manifest tenant allowlist");
        if (entry.status() != Status.DRAFT) throw failure("IMMUTABLE", "Approved or revoked version cannot be re-approved");
        if (entry.creator().equals(caller.subject())) throw failure("SEPARATION_OF_DUTIES", "Author cannot approve their own manifest");
        validate(entry.manifest());
        if (entry.manifest().health() != Health.HEALTHY) throw failure("UNHEALTHY", "Only healthy operations may be approved");
        if (!verifiedEndpointRefs.contains(entry.manifest().endpointRef())) throw failure("ENDPOINT_UNVERIFIED", "No trusted endpoint attestation");
        records.put(key, new Entry(entry.manifest(), entry.creator(), Status.APPROVED, caller.subject()));
        audit(caller, "APPROVED", entry.manifest());
    }
    /** Revoke eligibility without mutating the historical approved manifest. */
    public synchronized void revoke(Caller caller, String toolId, String version, String operation) {
        require(caller, "registry:approve");
        requireCoordinates(toolId, version, operation);
        Entry entry = records.get(new Key(caller.tenantId(), toolId, version, operation));
        if (entry == null) throw failure("NOT_FOUND", "Unknown manifest version");
        if (!entry.manifest().tenantAvailability().contains(caller.tenantId()))
            throw failure("FORBIDDEN", "Wrong tenant");
        if (entry.status() != Status.APPROVED) throw failure("INVALID_STATE", "Only approved versions may be revoked");
        records.put(key(caller.tenantId(), entry.manifest()), new Entry(entry.manifest(), entry.creator(), Status.REVOKED, caller.subject()));
        audit(caller, "REVOKED", entry.manifest());
    }
    /** Audit records contain only manifest identity and digest, never raw tool arguments or credentials. */
    public synchronized List<AuditEvent> auditTrail(Caller caller) {
        require(caller, "registry:audit");
        return audit.stream().filter(e -> e.tenantId().equals(caller.tenantId())).toList();
    }
    private void audit(Caller caller, String action, Manifest m) {
        long sequence = auditSequences.merge(caller.tenantId(), 1L, Long::sum);
        audit.add(new AuditEvent(sequence, caller.tenantId(), action,
            m.toolId(), m.version(), m.operation(), caller.subject(), m.manifestDigest()));
    }
    /** Validate a tool payload against the immutable, approved schema (the registry never executes the tool). */
    public synchronized void validatePayload(Caller caller, String toolId, String version, String operation,
                                             boolean input, Map<String, ?> payload) {
        require(caller, "registry:lookup");
        requireCoordinates(toolId, version, operation);
        Entry entry = records.get(new Key(caller.tenantId(), toolId, version, operation));
        if (entry == null || entry.status() != Status.APPROVED) throw failure("NOT_APPROVED", "Approved version required");
        Manifest m = entry.manifest();
        if (!m.tenantAvailability().contains(caller.tenantId()) || !caller.scopes().containsAll(m.requiredScopes()))
            throw failure("FORBIDDEN", "Payload schema inaccessible to caller");
        Shape shape = approvedSchemas.get(input ? m.inputSchemaRef() : m.outputSchemaRef());
        PayloadShapeValidator.validate(payload, shape);
    }
    public synchronized List<Manifest> listApproved(Caller caller) {
        require(caller, "registry:lookup");
        return records.entrySet().stream().filter(e -> e.getKey().tenantId().equals(caller.tenantId()))
            .map(Map.Entry::getValue).filter(e -> e.status() == Status.APPROVED)
            .map(Entry::manifest)
            .filter(m -> caller.scopes().containsAll(m.requiredScopes()))
            .filter(m -> m.health() == Health.HEALTHY && verifiedEndpointRefs.contains(m.endpointRef()))
            .toList();
    }
    public synchronized Selection select(Caller caller, SelectionRequest request) {
        require(caller, "registry:lookup");
        if (request == null) throw failure("INVALID_TASK", "Selection request required");
        if (request.requiredCapabilities().isEmpty() || request.requiredCapabilities().stream().anyMatch(c -> !IDENTIFIER.matcher(c).matches()))
            throw failure("INVALID_TASK", "Explicit capabilities required");
        if (request.requiredCapabilities().size() > MAX_CAPABILITIES ||
            !request.requiredCapabilities().containsAll(request.expectedSchemas().keySet()))
            throw failure("INVALID_TASK", "Schema constraints must refer to requested capabilities");
        if (request.pinnedVersions().entrySet().stream().anyMatch(e -> !valid(e.getKey())
            || e.getValue() == null || !SEMVER.matcher(e.getValue()).matches()))
            throw failure("INVALID_TASK", "Invalid pinned tool version");
        if (request.expectedSchemas().values().stream().anyMatch(Objects::isNull))
            throw failure("INVALID_TASK", "Null schema requirement");
        List<Denial> denials = new ArrayList<>();
        List<Manifest> candidates = new ArrayList<>();
        for (var record : records.entrySet()) {
            // Never reveal whether another tenant registered a tool, even via a denial code.
            if (!record.getKey().tenantId().equals(caller.tenantId())) continue;
            Entry entry = record.getValue();
            Manifest m = entry.manifest();
            Set<String> overlap = intersection(m.capabilities(), request.requiredCapabilities());
            if (overlap.isEmpty()) continue;
            DenialCode reason = null;
            if (entry.status() == Status.REVOKED) reason = DenialCode.REVOKED;
            else if (entry.status() != Status.APPROVED) reason = DenialCode.NOT_APPROVED;
            else if (!caller.scopes().containsAll(m.requiredScopes())) reason = DenialCode.MISSING_PERMISSION;
            else if (!request.allowedEffects().containsAll(m.sideEffects())) reason = DenialCode.EFFECT_NOT_ALLOWED;
            else if (m.riskLevel().ordinal() > request.maxRisk().ordinal()) reason = DenialCode.RISK_NOT_ALLOWED;
            else if (m.health() != Health.HEALTHY) reason = DenialCode.UNHEALTHY;
            else if (!verifiedEndpointRefs.contains(m.endpointRef())) reason = DenialCode.ENDPOINT_UNVERIFIED;
            else if (request.pinnedVersions().containsKey(m.toolId()) &&
                !m.version().equals(request.pinnedVersions().get(m.toolId()))) reason = DenialCode.VERSION_INCOMPATIBLE;
            else if (overlap.stream().anyMatch(c -> !schemaCompatible(request.expectedSchemas().get(c), m))) reason = DenialCode.SCHEMA_INCOMPATIBLE;
            if (reason != null) for (String capability : overlap)
                denials.add(new Denial(capability,
                    (reason == DenialCode.WRONG_TENANT || reason == DenialCode.MISSING_PERMISSION ||
                     reason == DenialCode.NOT_APPROVED || reason == DenialCode.REVOKED ||
                     reason == DenialCode.ENDPOINT_UNVERIFIED) ? "" : m.toolId(),
                    reason, message(reason)));
            else candidates.add(m);
        }
        candidates.sort(Comparator.comparing(Manifest::toolId).thenComparing(Manifest::version).thenComparing(Manifest::operation));
        Set<String> coverage = new HashSet<>();
        for (Manifest m : candidates) coverage.addAll(m.capabilities());
        Set<String> missing = new TreeSet<>(request.requiredCapabilities()); missing.removeAll(coverage);
        for (String capability : missing) if (denials.stream().noneMatch(d -> d.capability().equals(capability)))
            denials.add(new Denial(capability, "", DenialCode.NO_CAPABILITY, message(DenialCode.NO_CAPABILITY)));
        denials.sort(Comparator.comparing(Denial::capability).thenComparing(Denial::toolId).thenComparing(d -> d.code().name()));
        String revision = revision(caller.tenantId());
        if (!missing.isEmpty()) return new Selection(Decision.BLOCKED, revision, List.of(), List.copyOf(denials), "Required capability has no eligible implementation");
        if (candidates.size() > MAX_CANDIDATES) {
            denials.add(new Denial("*", "", DenialCode.SEARCH_LIMIT, message(DenialCode.SEARCH_LIMIT)));
            return new Selection(Decision.BLOCKED, revision, List.of(), List.copyOf(denials), "Search budget exceeded; manual candidate narrowing required");
        }
        // Bounded branch-and-bound set cover: choose the hardest uncovered capability first.
        // Search space scales with required capabilities, not with all registered operations.
        MinimumCapabilityCover.Result result = MinimumCapabilityCover.find(candidates, request.requiredCapabilities());
        List<Manifest> best = new ArrayList<>(result.selected());
        best.sort(Comparator.comparing(Manifest::toolId).thenComparing(Manifest::version).thenComparing(Manifest::operation));
        if (result.exhausted()) {
            denials.add(new Denial("*", "", DenialCode.SEARCH_LIMIT, message(DenialCode.SEARCH_LIMIT)));
            return new Selection(Decision.BLOCKED, revision, List.of(), List.copyOf(denials),
                "Search complexity budget exhausted; no unsafe approximate selection");
        }
        if (best.isEmpty()) {
            denials.add(new Denial("*", "", DenialCode.INCOMPATIBLE_VERSIONS, message(DenialCode.INCOMPATIBLE_VERSIONS)));
            return new Selection(Decision.BLOCKED, revision, List.of(), List.copyOf(denials), "All covering sets contain incompatible operation versions");
        }
        List<Binding> selected = new ArrayList<>();
        for (Manifest m : best) {
            Set<String> matched = intersection(m.capabilities(), request.requiredCapabilities());
            selected.add(new Binding(m.toolId(), m.version(), m.operation(), m.manifestDigest(),
                Collections.unmodifiableSet(new TreeSet<>(m.requiredScopes())), matched, "Approved, tenant-available, schema-compatible; explicit scopes: "
                    + String.join(",", new TreeSet<>(m.requiredScopes()))));
        }
        return new Selection(Decision.SELECTED, revision, List.copyOf(selected), List.copyOf(denials),
            "Minimal authorized cover: " + selected.size() + " operation(s); no permissions granted by registry");
    }
    private boolean schemaCompatible(Requirement expected, Manifest m) {
        if (expected == null) return true;
        // Exact pinned schema references are conservative: no implicit structural coercion.
        return (expected.inputSchemaRef() == null || expected.inputSchemaRef().equals(m.inputSchemaRef()))
            && (expected.outputSchemaRef() == null || expected.outputSchemaRef().equals(m.outputSchemaRef()));
    }
    private static String message(DenialCode c) { return switch (c) {
        case NO_CAPABILITY -> "No registered matching capability";
        case NOT_APPROVED -> "Tool version not approved";
        case WRONG_TENANT -> "Tool unavailable for authenticated tenant";
        case MISSING_PERMISSION -> "Caller lacks explicitly granted scopes";
        case EFFECT_NOT_ALLOWED -> "Operation effects are outside task allowance";
        case RISK_NOT_ALLOWED -> "Operation risk exceeds task policy";
        case SCHEMA_INCOMPATIBLE -> "Input or output schema reference incompatible";
        case VERSION_INCOMPATIBLE -> "Pinned version mismatch";
        case ENDPOINT_UNVERIFIED -> "Endpoint is not on verified allowlist";
        case UNHEALTHY -> "Operation health is not verified healthy";
        case SEARCH_LIMIT -> "Candidate limit exceeded";
        case INCOMPATIBLE_VERSIONS -> "Conflicting tool versions or operations";
        case REVOKED -> "Approved version revoked; new review and version required";
    }; }
    private synchronized String revision(String tenant) {
        String x = records.entrySet().stream()
            .filter(e -> e.getKey().tenantId().equals(tenant) && e.getValue().status() == Status.APPROVED)
            .map(e -> e.getValue().manifest().manifestDigest()).sorted().collect(Collectors.joining("|"));
        return "sha256:" + sha256(x);
    }
    private void validate(Manifest m) {
        if (!"0.1".equals(m.schemaVersion())) throw failure("INVALID_MANIFEST", "Unsupported manifest schema version");
        if (!valid(m.toolId()) || !valid(m.operation()) || m.capabilities().isEmpty() || !m.capabilities().stream().allMatch(ToolRegistry::valid))
            throw failure("INVALID_MANIFEST", "Invalid identifier or capability");
        if (!SEMVER.matcher(m.version()).matches()) throw failure("INVALID_VERSION", "Semantic version required");
        if (m.transport() == null || m.riskLevel() == null || m.health() == null) throw failure("INVALID_MANIFEST", "Missing typed transport/risk/health");
        if (m.sideEffects().isEmpty() || m.sideEffects().stream().anyMatch(Objects::isNull)) throw failure("INVALID_EFFECTS", "Declare all side effects");
        if ((m.sideEffects().contains(Effect.PAYMENT) || m.sideEffects().contains(Effect.DESTRUCTIVE)) && m.riskLevel() != Risk.CRITICAL)
            throw failure("RISK_UNDERSTATED", "Payment/destructive effects must be critical risk");
        if (m.sideEffects().contains(Effect.WRITE) && m.riskLevel().ordinal() < Risk.MEDIUM.ordinal())
            throw failure("RISK_UNDERSTATED", "Writes require medium-or-higher risk");
        if (m.requiredScopes().isEmpty() || !m.requiredScopes().stream().allMatch(s -> SCOPE.matcher(s).matches()))
            throw failure("INVALID_SCOPES", "Explicit well-formed required scopes necessary");
        if (m.tenantAvailability().isEmpty() || m.tenantAvailability().stream().anyMatch(ToolRegistry::blank)) throw failure("INVALID_TENANTS", "Explicit tenant allowlist required");
        if (!REF.matcher(nonNull(m.inputSchemaRef())).matches() || !REF.matcher(nonNull(m.outputSchemaRef())).matches()
            || !approvedSchemas.containsKey(m.inputSchemaRef()) || !approvedSchemas.containsKey(m.outputSchemaRef()))
            throw failure("INVALID_SCHEMA", "Input/output schema must resolve to an approved typed shape");
        if (!ENDPOINT.matcher(nonNull(m.endpointRef())).matches() || !verifiedEndpointRefs.contains(m.endpointRef()))
            throw failure("ENDPOINT_UNVERIFIED", "Raw URLs and unknown MCP endpoints are forbidden");
        if (!validProvenance(m.provenance()) || !verifiedProvenanceRefs.contains(m.provenance()))
            throw failure("UNTRUSTED_PROVENANCE", "Only independently allowlisted provenance is accepted");
        if (blank(m.description()) || m.description().length() > 300 || suspicious(m.description()))
            throw failure("MALICIOUS_DESCRIPTION", "Untrusted description or instruction injection");
        if (m.manifestDigest() == null || !m.manifestDigest().equals(digest(m)))
            throw failure("INVALID_DIGEST", "Manifest digest mismatch");
    }
    private static boolean validProvenance(String provenance) {
        return provenance != null && provenance.matches("trusted:[A-Za-z0-9._-]{1,100}");
    }
    private static boolean suspicious(String text) {
        return INJECTION.matcher(text).find() || text.chars().anyMatch(c -> Character.isISOControl(c));
    }
    private static String digest(Manifest m) {
        // Length-prefix each field to remove separator collision ambiguity.
        String canonical = Arrays.stream(new String[] {m.schemaVersion(), m.toolId(), m.version(), m.operation(),
            String.valueOf(m.transport()), sorted(m.capabilities()), m.inputSchemaRef(), m.outputSchemaRef(),
            sorted(m.sideEffects()), sorted(m.requiredScopes()), String.valueOf(m.riskLevel()),
            sorted(m.tenantAvailability()), m.endpointRef(), String.valueOf(m.health()), m.provenance(), m.description()})
            .map(s -> s.length() + ":" + s).collect(Collectors.joining());
        return "sha256:" + sha256(canonical);
    }
    private static String sha256(String raw) {
        try {
            byte[] h = MessageDigest.getInstance("SHA-256").digest(raw.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(h);
        } catch (NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
    private static String sorted(Collection<?> xs) { return xs.stream().map(String::valueOf).sorted()
        .map(s -> s.length() + ":" + s).collect(Collectors.joining()); }
    private static Set<String> intersection(Set<String> a, Set<String> b) {
        Set<String> ordered = new TreeSet<>(a);
        ordered.retainAll(b);
        return Collections.unmodifiableSet(ordered);
    }
    private static Key key(String tenant, Manifest m) { return new Key(tenant, m.toolId(), m.version(), m.operation()); }
    private static void requireCoordinates(String toolId, String version, String operation) {
        if (!valid(toolId) || !valid(operation) || version == null || !SEMVER.matcher(version).matches())
            throw failure("INVALID_TASK", "Well-formed tool ID, version and operation required");
    }
    private static boolean valid(String s) { return s != null && IDENTIFIER.matcher(s).matches(); }
    private static boolean blank(String s) { return s == null || s.isBlank(); }
    private static String nonNull(String s) { return s == null ? "" : s; }
    private static void require(Caller c, String scope) {
        if (c == null || !c.has(scope)) throw failure("FORBIDDEN", "Missing registry permission " + scope);
    }
}
