# Dell Final Product Perfection Pack

Target repository: `prx0r/dell`
Inspected head: `e9ca0fe11052aa6422999fd848c936ef7d9a838a`
Purpose: final implementation handoff. Treat this pack as a semantic hardening and release specification, not as another brainstorming document.

## Mission

Finish Dell as a trustworthy, machine-usable inference-economics oracle/API/MCP.

Dell is already architecturally mature. Do not redesign the evidence model, identity model, or economics ontology unless a failing invariant proves it necessary.

The remaining work is concentrated in:

1. one canonical decision service;
2. exact constraint semantics;
3. defensible scoring/category semantics;
4. REST/MCP parity;
5. field-level evidence/freshness truth;
6. external-agent decision tests;
7. documentation generated from implementation;
8. final clean-room production certification.

## Non-negotiable principle

> Dell must never tell a human or autonomous agent that something is best, usable, free, live, fast, reliable, agent-ready, workhorse, or within budget unless the system can define the word, show the exact fields used, distinguish observed from inferred values, and explain exclusions.

## Do not optimize for

- route count
- badge count
- number of endpoints
- percentage of tests named PASS
- amount of documentation
- clever scoring formulas

Optimize for:

- correct decisions
- zero hidden assumptions
- zero constraint leakage
- evidence retrieval
- reproducibility
- API/MCP semantic parity
- external-agent usefulness

## Definition of DONE

Dell is DONE when `python -m app.certify_final` produces a certificate in which every critical gate is PASS and no zero-tolerance violation exists.

See `12_FINAL_RELEASE_CERTIFICATE.md`.
