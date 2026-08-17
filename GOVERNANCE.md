# Governance

Collective is stewarded by the **InterRealm Foundation** as non-profit open
infrastructure for educational AI.

This document exists because two questions will be asked early and deserve an answer
written down in advance rather than negotiated later:

- *If a district puts its curriculum in a Collective mirror, what happens to it?*
- *Is this a funnel for a commercial product?*

## The short answers

**A district's data stays the district's.** A mirror runs on hardware you control.
Collective has no telemetry, no phone-home, no hosted tier that your instance reports
to, and no mechanism by which content in your mirror reaches the Foundation or anyone
else. If you never open a network port, nothing leaves.

**No, and here is the boundary.** InterRealm Foundation members build commercial
products in adjacent space — most directly **Hopblox**, a learning platform for
families and kids. That is a real relationship and pretending otherwise would be worse
than stating it. The line:

| | Collective | Hopblox |
|---|---|---|
| Steward | InterRealm Foundation | commercial |
| License | Apache-2.0, CC BY-4.0 data | proprietary |
| Contains | public standards, public curriculum alignments | learner memory, per-child models |
| Runs | on your hardware | hosted |

Hopblox is a **consumer** of Collective, on exactly the same terms as any other
consumer. It gets no privileged API, no reserved namespace, no feature that is withheld
from the open project, and no access to any mirror it does not itself host.

The asymmetry that makes this stable: what is valuable to Hopblox is the **long-term
learner memory graph** — what a specific child knows, how they got there, what to teach
next. None of that is in Collective and none of it can be, because Collective
contains public standards data and nothing about any individual. The two are not
competing for the same asset, so there is no gravitational pull toward closing the open
one.

## Not open-core

There is no paid tier, no "enterprise edition," and no feature held back from the open
repository. If a capability belongs in Collective it ships in Collective.

The failure mode this rules out: a project that is open until the useful parts are
finished, then quietly stops merging them. If that ever appears to be happening, this
document is the thing to hold the Foundation to.

## Scope

**In scope**

- Mirroring, syncing, and drift detection against upstream sources
- Query, search, and traversal over the mirrored graph
- MCP and HTTP surfaces over the same query layer
- A web explorer for educators — search, compare, walk progressions
- Local extension: a school's own curriculum aligned against the shared spine
- Federation: identity, merge semantics, and schema-change proposals

**Out of scope**

- Anything about an individual learner. No learner records, no mastery models, no
  per-child state. This is a hard boundary, not a current-phase limitation — it is what
  makes the privacy answer above simple enough to be credible.
- Content authoring or curriculum generation
- Anything requiring a hosted service the Foundation operates on your behalf

## Relationship to Learning Commons

Learning Commons is the **upstream and the authority**. Collective mirrors their
published graph under the license they chose; it does not fork it, compete with it, or
assert an alternative canon. Where the mirror and upstream disagree, upstream is
correct and the mirror has a bug.

Ambitions for that relationship, in order of how much agreement each needs:

1. **Nothing** — mirroring is already permitted by CC BY-4.0. (Pulling exports through
   their API is separately governed by their terms.)
2. **Drift reports back upstream** — a changelog they do not currently publish, offered
   as a contribution.
3. **Schema-change proposals** — a path for schools to propose additions, with the
   mirror as the place proposals can be prototyped before upstream commits.
4. **Federation** — instances that can exchange local extensions against a shared,
   content-addressed identity spine.

Each rung is useful on its own. None is contingent on the next, and Collective stays
worth running even if the relationship never advances past rung one.

## Decisions

Alpha, so: maintainers decide, in public issues and pull requests. When there is more
than one independent institutional deployment, this section gets replaced by something
with actual structure — a technical steering committee with seats for deploying
institutions. Written here now so the commitment predates the leverage.

## Contact

Open an issue. For partnership or governance questions, contact the InterRealm
Foundation.
