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
    public enum Status { DRAFT, APPROVED }
    public enum Decision { SELECTED, BLOCKED }
    public enum DenialCode { NO_CAPABILITY, NOT_APPROVED, WRONG_TENANT, MISSING_PERMISSION,
        EFFECT_NOT_ALLOWED, RISK_NOT_ALLOWED, SCHEMA_INCOMPATIBLE, VERSION_INCOMPATIBLE,
        ENDPOINT_UNVERIFIED, UNHEALTHY, SEARCH_LIMIT, INCOMPATIBLE_VERSIONS }

    private static final Pattern IDENTIFIER = Pattern.compile("[a-zA-Z][a-zA-Z0-9_.:-]{0,127}");
    private static final Pattern SEMVER = Pattern.compile("(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?");
    private static final Pattern REF = Pattern.compile("artifact://schemas/[A-Za-z0-9._/-]+", Pattern.CASE_INSENSITIVE);
    private static final Pattern ENDPOINT = Pattern.compile("artifact://approved/endpoints/[a-zA-Z0-9._/-]+");
    private static final Pattern SCOPE = Pattern.compile("[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*");
    private static final Pattern INJECTION = Pattern.compile("(?i)(ignore (all |any )?(previous|system|developer)|system prompt|developer message|send (me |all )?(secrets|passwords|tokens)|exfiltrat|\\bapi[_ -]?key\\b|<\\|im_(start|end)\\|>|\\[inst\\]|\\{\\{.*\\}\\}|https?://|\\bBearer\\s|\\bBEGIN (RSA |OPENSSH )?PRIVATE KEY\\b)");
    private static final int MAX_CANDIDATES = 18;

    public record Shape(Map<String, FieldType> fields, Set<String> required, boolean additionalProperties) {
        public Shape {
            Objects.requireNonNull(fields); Objects.requireNonNull(required);
            fields = Map.copyOf(fields); required = Set.copyOf(required);
            if (fields.isEmpty() || !fields.keySet().stream().allMatch(k -> IDENTIFIER.matcher(k).matches())
                || fields.values().stream().anyMatch(Objects::isNull) || !fields.keySet().containsAll(required))
                throw failure("INVALID_SCHEMA", "Invalid JSON object shape");
        }
    }
    public record Caller(String subject, String tenantId, Set<String> scopes) {
        public Caller {
            if (blank(subject) || blank(tenantId)) throw failure("UNAUTHENTICATED", "Caller identity required");
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
    // Actual throwable: typed domain error without leaking untrusted manifest text.
    public static final class RegistryFailure extends RuntimeException {
        public final String code;
        public RegistryFailure(String code, String detail) { super(detail); this.code = code; }
    }
    private static RegistryFailure failure(String code, String detail) { return new RegistryFailure(code, detail); }
    private record Key(String id, String version, String operation) implements Comparable<Key> {
        public int compareTo(Key other) { return (id + "\u0000" + version + "\u0000" + operation)
            .compareTo(other.id + "\u0000" + other.version + "\u0000" + other.operation); }
    }
    private record Entry(Manifest manifest, String creator, Status status, String approver) {}
    private final SortedMap<Key, Entry> records = new TreeMap<>();
    private final Map<String, Shape> approvedSchemas;
    private final Set<String> verifiedEndpointRefs;

    public ToolRegistry(Map<String, Shape> approvedSchemas, Set<String> verifiedEndpointRefs) {
        this.approvedSchemas = Map.copyOf(approvedSchemas);
        this.verifiedEndpointRefs = Set.copyOf(verifiedEndpointRefs);
        for (String ref : approvedSchemas.keySet()) if (!REF.matcher(ref).matches()) throw failure("INVALID_SCHEMA_REF", "Schema reference is not approved artifact URI");
        for (String ref : verifiedEndpointRefs) if (!ENDPOINT.matcher(ref).matches()) throw failure("INVALID_ENDPOINT", "Endpoint reference must be approved artifact URI");
    }
    public synchronized void registerDraft(Caller caller, Manifest manifest) {
        require(caller, "registry:register"); validate(manifest);
        if (!manifest.tenantAvailability().contains(caller.tenantId())) throw failure("FORBIDDEN", "Registrar is not in manifest tenant allowlist");
        Key key = key(manifest);
        if (records.containsKey(key)) throw failure("VERSION_EXISTS", "Tool operation version is immutable");
        records.put(key, new Entry(manifest, caller.subject(), Status.DRAFT, null));
    }
    public synchronized void approve(Caller caller, String toolId, String version, String operation) {
        require(caller, "registry:approve");
        Key key = new Key(toolId, version, operation); Entry entry = records.get(key);
        if (entry == null) throw failure("NOT_FOUND", "Unknown manifest version");
        if (!entry.manifest().tenantAvailability().contains(caller.tenantId())) throw failure("FORBIDDEN", "Approver is not in manifest tenant allowlist");
        if (entry.status() == Status.APPROVED) throw failure("IMMUTABLE", "Already approved immutable version");
        if (entry.creator().equals(caller.subject())) throw failure("SEPARATION_OF_DUTIES", "Author cannot approve their own manifest");
        validate(entry.manifest());
        if (entry.manifest().health() != Health.HEALTHY) throw failure("UNHEALTHY", "Only healthy operations may be approved");
        if (!verifiedEndpointRefs.contains(entry.manifest().endpointRef())) throw failure("ENDPOINT_UNVERIFIED", "No trusted endpoint attestation");
        records.put(key, new Entry(entry.manifest(), entry.creator(), Status.APPROVED, caller.subject()));
    }
    /** Validate a tool payload against the immutable, approved schema (the registry never executes the tool). */
    public synchronized void validatePayload(Caller caller, String toolId, String version, String operation,
                                             boolean input, Map<String, ?> payload) {
        require(caller, "registry:lookup");
        Entry entry = records.get(new Key(toolId, version, operation));
        if (entry == null || entry.status() != Status.APPROVED) throw failure("NOT_APPROVED", "Approved version required");
        Manifest m = entry.manifest();
        if (!m.tenantAvailability().contains(caller.tenantId()) || !caller.scopes().containsAll(m.requiredScopes()))
            throw failure("FORBIDDEN", "Payload schema inaccessible to caller");
        Shape shape = approvedSchemas.get(input ? m.inputSchemaRef() : m.outputSchemaRef());
        if (payload == null || !payload.keySet().containsAll(shape.required()))
            throw failure("PAYLOAD_SCHEMA_MISMATCH", "Required object fields missing");
        for (var item : payload.entrySet()) {
            FieldType expected = shape.fields().get(item.getKey());
            if (expected == null) {
                if (!shape.additionalProperties()) throw failure("PAYLOAD_SCHEMA_MISMATCH", "Undeclared field");
                continue;
            }
            Object value = item.getValue();
            boolean correct = value != null && switch (expected) {
                case STRING -> value instanceof String;
                case NUMBER -> value instanceof Number;
                case BOOLEAN -> value instanceof Boolean;
                case OBJECT -> value instanceof Map;
                case ARRAY -> value instanceof List;
            };
            if (!correct) throw failure("PAYLOAD_SCHEMA_MISMATCH", "Incorrect field type");
        }
    }
    public synchronized List<Manifest> listApproved(Caller caller) {
        require(caller, "registry:lookup");
        return records.values().stream().filter(e -> e.status() == Status.APPROVED)
            .map(Entry::manifest).filter(m -> m.tenantAvailability().contains(caller.tenantId()))
            .filter(m -> caller.scopes().containsAll(m.requiredScopes()))
            .filter(m -> m.health() == Health.HEALTHY && verifiedEndpointRefs.contains(m.endpointRef()))
            .toList();
    }
    public synchronized Selection select(Caller caller, SelectionRequest request) {
        require(caller, "registry:lookup");
        if (request.requiredCapabilities().isEmpty() || request.requiredCapabilities().stream().anyMatch(c -> !IDENTIFIER.matcher(c).matches()))
            throw failure("INVALID_TASK", "Explicit capabilities required");
        if (!request.requiredCapabilities().containsAll(request.expectedSchemas().keySet()))
            throw failure("INVALID_TASK", "Schema constraints must refer to requested capabilities");
        List<Denial> denials = new ArrayList<>();
        List<Manifest> candidates = new ArrayList<>();
        for (Entry entry : records.values()) {
            Manifest m = entry.manifest();
            Set<String> overlap = intersection(m.capabilities(), request.requiredCapabilities());
            if (overlap.isEmpty()) continue;
            DenialCode reason = null;
            if (entry.status() != Status.APPROVED) reason = DenialCode.NOT_APPROVED;
            else if (!m.tenantAvailability().contains(caller.tenantId())) reason = DenialCode.WRONG_TENANT;
            else if (!caller.scopes().containsAll(m.requiredScopes())) reason = DenialCode.MISSING_PERMISSION;
            else if (!request.allowedEffects().containsAll(m.sideEffects())) reason = DenialCode.EFFECT_NOT_ALLOWED;
            else if (m.riskLevel().ordinal() > request.maxRisk().ordinal()) reason = DenialCode.RISK_NOT_ALLOWED;
            else if (m.health() != Health.HEALTHY) reason = DenialCode.UNHEALTHY;
            else if (!verifiedEndpointRefs.contains(m.endpointRef())) reason = DenialCode.ENDPOINT_UNVERIFIED;
            else if (!request.pinnedVersions().isEmpty() && !m.version().equals(request.pinnedVersions().get(m.toolId()))) reason = DenialCode.VERSION_INCOMPATIBLE;
            else if (overlap.stream().anyMatch(c -> !schemaCompatible(request.expectedSchemas().get(c), m))) reason = DenialCode.SCHEMA_INCOMPATIBLE;
            if (reason != null) for (String capability : overlap)
                denials.add(new Denial(capability, m.toolId(), reason, message(reason)));
            else candidates.add(m);
        }
        candidates.sort(Comparator.comparing(Manifest::toolId).thenComparing(Manifest::version).thenComparing(Manifest::operation));
        Set<String> coverage = new HashSet<>();
        for (Manifest m : candidates) coverage.addAll(m.capabilities());
        Set<String> missing = new TreeSet<>(request.requiredCapabilities()); missing.removeAll(coverage);
        for (String capability : missing) if (denials.stream().noneMatch(d -> d.capability().equals(capability)))
            denials.add(new Denial(capability, "", DenialCode.NO_CAPABILITY, message(DenialCode.NO_CAPABILITY)));
        denials.sort(Comparator.comparing(Denial::capability).thenComparing(Denial::toolId).thenComparing(d -> d.code().name()));
        String revision = revision();
        if (!missing.isEmpty()) return new Selection(Decision.BLOCKED, revision, List.of(), List.copyOf(denials), "Required capability has no eligible implementation");
        if (candidates.size() > MAX_CANDIDATES) {
            denials.add(new Denial("*", "", DenialCode.SEARCH_LIMIT, message(DenialCode.SEARCH_LIMIT)));
            return new Selection(Decision.BLOCKED, revision, List.of(), List.copyOf(denials), "Search budget exceeded; manual candidate narrowing required");
        }
        List<Manifest> best = new ArrayList<>();
        int limit = 1 << candidates.size();
        for (int mask = 1; mask < limit; mask++) {
            int size = Integer.bitCount(mask);
            if (!best.isEmpty() && size > best.size()) continue;
            List<Manifest> subset = new ArrayList<>(size);
            Set<String> covered = new HashSet<>(); Map<String, String> versions = new HashMap<>();
            boolean valid = true;
            for (int i = 0; i < candidates.size(); i++) if ((mask & (1 << i)) != 0) {
                Manifest m = candidates.get(i); subset.add(m); covered.addAll(m.capabilities());
                String id = m.toolId();
                if (versions.putIfAbsent(id, m.version()) != null && !versions.get(id).equals(m.version())) { valid = false; break; }
            }
            if (valid && covered.containsAll(request.requiredCapabilities()) && (best.isEmpty() || compare(subset, best) < 0)) best = subset;
        }
        if (best.isEmpty()) {
            denials.add(new Denial("*", "", DenialCode.INCOMPATIBLE_VERSIONS, message(DenialCode.INCOMPATIBLE_VERSIONS)));
            return new Selection(Decision.BLOCKED, revision, List.of(), List.copyOf(denials), "All covering sets contain incompatible operation versions");
        }
        List<Binding> selected = new ArrayList<>();
        for (Manifest m : best) {
            Set<String> matched = intersection(m.capabilities(), request.requiredCapabilities());
            selected.add(new Binding(m.toolId(), m.version(), m.operation(), m.manifestDigest(),
                m.requiredScopes(), matched, "Approved, tenant-available, schema-compatible; explicit scopes: "
                    + String.join(",", new TreeSet<>(m.requiredScopes()))));
        }
        return new Selection(Decision.SELECTED, revision, List.copyOf(selected), List.copyOf(denials),
            "Minimal authorized cover: " + selected.size() + " operation(s); no permissions granted by registry");
    }
    private static int compare(List<Manifest> a, List<Manifest> b) {
        int v = Integer.compare(a.size(), b.size()); if (v != 0) return v;
        v = Integer.compare(a.stream().mapToInt(m -> m.riskLevel().ordinal()).sum(), b.stream().mapToInt(m -> m.riskLevel().ordinal()).sum());
        if (v != 0) return v;
        v = Integer.compare(a.stream().mapToInt(m -> m.requiredScopes().size()).sum(), b.stream().mapToInt(m -> m.requiredScopes().size()).sum());
        if (v != 0) return v;
        return signature(a).compareTo(signature(b));
    }
    private static String signature(List<Manifest> x) {
        return x.stream().map(m -> m.toolId() + "@" + m.version() + "/" + m.operation()).sorted().collect(Collectors.joining("|"));
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
    }; }
    private synchronized String revision() {
        String x = records.values().stream().filter(e -> e.status() == Status.APPROVED)
            .map(e -> e.manifest().manifestDigest()).sorted().collect(Collectors.joining("|"));
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
        if (blank(m.provenance()) || !m.provenance().startsWith("trusted:") || m.provenance().length() > 200 || suspicious(m.provenance()))
            throw failure("UNTRUSTED_PROVENANCE", "Verified non-secret provenance required");
        if (blank(m.description()) || m.description().length() > 300 || suspicious(m.description()))
            throw failure("MALICIOUS_DESCRIPTION", "Untrusted description or instruction injection");
        if (m.manifestDigest() == null || !m.manifestDigest().equals(digest(m)))
            throw failure("INVALID_DIGEST", "Manifest digest mismatch");
    }
    private static boolean suspicious(String text) {
        return INJECTION.matcher(text).find() || text.chars().anyMatch(c -> Character.isISOControl(c));
    }
    private static String digest(Manifest m) {
        String canonical = String.join("\n", m.schemaVersion(), m.toolId(), m.version(), m.operation(),
            String.valueOf(m.transport()), sorted(m.capabilities()), m.inputSchemaRef(), m.outputSchemaRef(),
            sorted(m.sideEffects()), sorted(m.requiredScopes()), String.valueOf(m.riskLevel()),
            sorted(m.tenantAvailability()), m.endpointRef(), String.valueOf(m.health()), m.provenance(), m.description());
        return "sha256:" + sha256(canonical);
    }
    private static String sha256(String raw) {
        try {
            byte[] h = MessageDigest.getInstance("SHA-256").digest(raw.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(h);
        } catch (NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
    private static String sorted(Collection<?> xs) { return xs.stream().map(String::valueOf).sorted().collect(Collectors.joining(",")); }
    private static Set<String> intersection(Set<String> a, Set<String> b) { Set<String> x = new TreeSet<>(a); x.retainAll(b); return Set.copyOf(x); }
    private static Key key(Manifest m) { return new Key(m.toolId(), m.version(), m.operation()); }
    private static boolean valid(String s) { return s != null && IDENTIFIER.matcher(s).matches(); }
    private static boolean blank(String s) { return s == null || s.isBlank(); }
    private static String nonNull(String s) { return s == null ? "" : s; }
    private static void require(Caller c, String scope) {
        if (c == null || !c.has(scope)) throw failure("FORBIDDEN", "Missing registry permission " + scope);
    }
}
