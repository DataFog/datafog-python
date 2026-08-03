# Contributor License Agreement Policy

DataFog uses a Contributor License Agreement (CLA) to keep the origin and
licensing of external contributions clear across its open-source projects.

## What contributors grant

Contributors keep ownership of their work. By signing the
[DataFog Individual Contributor License Agreement](../CLA.md), an individual
grants DataFog, Inc. a broad, non-exclusive copyright and patent license. The
agreement allows DataFog to:

- continue distributing the contribution under the open-source license in use
  by the project when the contribution was submitted;
- use and sublicense the contribution in other open-source, commercial, or
  proprietary distributions; and
- maintain, enforce, and evolve the project without seeking a new signature for
  each contribution.

The CLA does not transfer copyright ownership to DataFog.

## Coverage and signing

An individual must accept the current CLA before submitting a contribution
that is intended to be covered by it. The CLA's effective date is the
acceptance date; submitting first and signing later does not silently create
retroactive coverage. A new signature may be required if DataFog publishes a
new agreement version.

An individual should accept the CLA only if they own the contribution or have
authority to grant the rights in it. If an employer or another entity owns or
may own the work, use the entity-owned or contract-covered workflow below.

Maintainers must not merge an external contribution unless the individual CLA
was accepted before submission, another written agreement covers the specific
contribution, or a separate historical ratification/IP assignment/license has
been signed and documented. A workflow status is evidence of process, not a
substitute for checking who owns the work.

## Contributor and maintainer workflow

### Individual-owned contribution

1. The contributor reviews and accepts the current CLA through DataFog's
   designated signing workflow before opening the pull request or otherwise
   submitting the contribution.
2. The contributor identifies third-party material and applicable restrictions
   in the pull request.
3. The maintainer confirms that the acceptance record predates the submission,
   verifies any third-party notices, and records the agreement version and
   acceptance date in the private CLA records.
4. The maintainer merges only after the coverage check passes.

### Entity-owned contribution

1. The contributor tells the maintainer before submission or merge if an
   employer or other entity owns or may own the contribution.
2. The maintainer pauses the merge and contacts
   [`legal@datafog.ai`](mailto:legal@datafog.ai) for the entity contribution
   process.
3. The entity, through an authorized representative, signs the applicable
   entity CLA or other written authorization before the contribution is merged.
4. The maintainer records the entity, signatory authority, covered project or
   contribution, agreement version, and dates privately; an individual CLA is
   not treated as covering entity-owned work unless the written agreement says
   so.

### Contract-covered contribution

1. The contributor identifies any employment, contractor, consulting, or other
   intellectual-property agreement that may cover the contribution.
2. The maintainer obtains confirmation from DataFog's authorized legal or
   administrative contact that the agreement covers the relevant rights and
   project. Do not request or store more confidential contract text than is
   necessary to verify coverage.
3. The maintainer records the agreement reference, rights holder, covered
   scope, and confirmation date in private records and marks the pull request
   as covered under that agreement.

For an active advisor or contractor relationship that is being updated, use a
short signed interim IP addendum before continuing new or deferred work. The
addendum should identify the prior, current, and future service scope, the
effective date, any pre-existing or third-party material, and the rights
holder. Fold it into the amended or restated service agreement later. Do not
require the individual CLA for work covered by the service agreement, but do
not treat an unsigned agreement discussion as coverage.

### Contribution submitted before CLA acceptance

The public CLA does not retroactively cover a prior submission. Before merge,
DataFog must either obtain a separate signed historical ratification/IP
assignment/license from the relevant rights holder, or replace or remove the
uncovered material. The [historical ratification template]
(cla-historical-ratification.md) is an interim starting point only and must not
be treated as executed until completed and signed.

## Agreement and signature records

The agreement is versioned. DataFog retains or exports records sufficient to
identify the signer, agreement version, acceptance time, authenticated account,
and the covered project or contribution where needed. Store these records,
entity authorizations, contract-coverage confirmations, and historical
ratifications in access-controlled private company storage. Do not publish a
contributor signature list, public coverage roster, private contract text, or
historical ratification in the repository.

Requests concerning a signature record or the CLA should be sent to
[`legal@datafog.ai`](mailto:legal@datafog.ai).

## Existing contributions

Existing contributions remain governed by the licenses and agreements in effect
when they were submitted. If DataFog needs broader rights to an existing
external contribution, it must obtain those rights through a separate signed
historical ratification/IP assignment/license from the relevant rights holder,
or replace or isolate the contribution.
