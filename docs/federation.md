# Federation

Most "federated" claims are aspirational — a roadmap item that requires a specification
nobody has written and an identity scheme nobody has agreed to.

This one is unusual: **the hard prerequisite is already satisfied**, and it was
satisfied by Learning Commons, whether or not they framed it that way.

## The finding

Every node id in the published Knowledge Graph is a **UUID version 5**.

```
node id UUID versions: {5: 60000}      # 60,000-node sample, no exceptions
```

UUID v5 is *name-based*: the id is a SHA-1 hash of a namespace plus a name. It is not
random and not assigned by a counter. The same inputs always produce the same id, on
any machine, at any time, with no coordination.

For comparison, `caseIdentifierUUID` — the upstream CASE identifier — is a mix of v1,
v4, and v5. That one is an external identifier with external history. The *internal*
identity Learning Commons assigns is uniformly derived.

## Why that matters

The expensive part of federating any graph is identity reconciliation. If two instances
assign their own ids, then merging means maintaining a correspondence table between
them, keeping it current, and resolving conflicts when two instances disagree about
whether two records are the same thing. That layer is where federated systems usually
die.

Deterministic ids remove it entirely:

- **Two independently built mirrors are byte-identical in identity.** A district in
  Ohio and a district in Oregon that each sync the same upstream release produce the
  same ids for the same standards, with no communication.
- **Local extensions merge without translation.** A district aligning its own
  curriculum to `69d536ac-…` is referring to the same node any other instance means by
  that id. Extensions are additive edges against a shared spine.
- **Proposals can be unambiguous.** "Add a `buildsTowards` edge from *this* node to
  *that* node" is a statement any instance can evaluate against its own copy.
- **Divergence is detectable.** If two mirrors of the same release disagree about a
  node's content under the same id, that is a real bug in one of them, and it can be
  found by comparison rather than argued about.

## What still has to be built

Deterministic identity is necessary, not sufficient. Honestly, what is missing:

**1. The id derivation recipe.** We have verified the ids *are* v5. We have not
recovered the namespace and name string used to produce them, so a third party cannot
yet mint an id for a node upstream has not published. That matters for local extensions
— a district's own lesson needs an id that will not collide and that another instance
could independently derive. Two paths: Learning Commons publishes the recipe, or the
federation spec defines a separate namespace for local extensions and never mints into
the upstream one. **The second works without their involvement and is the safer default.**

**2. A release identifier.** Federation needs instances to say which upstream release
they are a mirror of. Right now a mirror records its own build time and source file
hashes; there is no upstream version to name. The source hashes are a serviceable
stand-in until there is.

**3. Merge semantics for local extensions.** Additive edges into the shared spine are
easy. Two districts asserting *contradictory* alignments for the same pair of standards
is a policy question before it is a technical one, and it should be answered as one —
probably by keeping extensions namespaced per instance and never silently merging them
into a single truth.

**4. A proposal format.** A schema change should arrive upstream as a testable
artifact: the shape being requested, the evidence for it, and a fixture that
demonstrates the query it would enable. That is a much better contribution than an
issue describing a wish, and it is a natural thing for a mirror to produce.

## Sequencing

Each step is useful alone and none is blocked on Learning Commons agreeing to anything:

1. **Mirror.** Already works. Permitted by CC BY-4.0.
2. **Drift reports.** Already works. Offered upstream as a changelog they do not
   currently publish.
3. **Local extensions** in a namespaced id space, isolated from upstream tables so
   `sync` never clobbers them.
4. **Extension exchange** between instances that choose to trust each other.
5. **Proposal pipeline** into upstream, if and when they want one.

Steps 1 and 2 are the entire current scope. The rest is written down so the design does
not accidentally foreclose it — specifically, why local extensions must live in
separate tables from day one, even before anything exchanges them.

## The part worth saying out loud

Learning Commons chose CC BY-4.0 and chose deterministic identifiers. Those two
decisions together are what make an ecosystem possible rather than merely a product
with an API. Whatever comes of federation, that groundwork was theirs.
