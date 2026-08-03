# CLA Administration Runbook

This runbook describes the rollout and ongoing administration of DataFog's
Contributor License Agreement (CLA). The legal text and interim contribution
records should receive later legal review when available, especially before
relying on them for a material ownership or relicensing decision.

## Signing workflow

Use the designated CLA or electronic-signature workflow approved by DataFog's
counsel. Keep the provider choice and implementation details separate from the
legal meaning of the agreement. The reviewed [`CLA.md`](../CLA.md) in this
repository is the source text for the published agreement. Treat each
substantive text change as a new agreement version and determine whether
contributors must sign again.

## Pilot rollout

1. Obtain legal approval for `CLA.md`, including the entity name, Delaware law,
   patent grant, and Outbound License Option Five.
2. Publish the approved `CLA.md` through the designated signing workflow and
   link it to `DataFog/datafog-python`.
3. Configure exemptions only for verified DataFog personnel and trusted bot
   accounts. At minimum, review Dependabot, Renovate, release automation, and
   any account that commits generated changes.
4. Open a pull request from a non-member test account and verify that the
   workflow requests acceptance, ties the record to the authenticated account,
   exposes a reviewable pass/fail result, and rechecks newly added authors.
   Confirm that the acceptance timestamp is earlier than the test submission.
5. In branch protection for `dev`, require the workflow's coverage check when
   available. Apply the rule to administrators if the policy is intended to be
   non-bypassable.
6. Verify bot and internal-member pull requests pass using documented
   exemptions.
7. Merge the policy change only when the signing flow, prospective-date check,
   and required coverage check have all been tested.

## Organization rollout

DataFog currently uses GitHub Free, so organization-wide rulesets are not
available. Repeat the following for every active public repository:

1. Confirm its license, default branch, and contribution guide.
2. Add links to the organization CLA and CLA policy.
3. Enable the designated signing workflow using the same agreement version.
4. Protect the default branch and require the workflow's coverage check before
   merge.
5. Test an external pull request and an exempt bot pull request.
6. Record the repository, protected branch, activation date, agreement version,
   exemptions, and test pull request in the rollout inventory.

If DataFog upgrades to GitHub Team or Enterprise, replace per-repository status
configuration with an organization ruleset targeting the default branches of
the covered public repositories.

## Historical contributions

The public CLA is prospective and does not cover a contribution submitted
before the contributor accepted it. Before relying on broader rights for
historical code:

1. inventory historical commits and pull requests by non-DataFog contributors;
2. distinguish original contributions from mechanical or third-party changes;
3. identify the actual rights holder and any employer or entity owner;
4. prepare a separate written historical ratification/IP assignment/license
   that lists the covered project, files, commits, pull requests, or other
   submissions; and
5. obtain signatures from DataFog and every required rights holder, or replace
   or isolate code where coverage cannot be obtained.

The repository's [historical ratification template](cla-historical-ratification.md)
is an interim starting point only. It is not an executed agreement and must not
be used as evidence of coverage until completed and signed. If an existing
advisor or contractor agreement covers the work, use a signed scope-confirming
addendum instead of duplicating it with a historical ratification.

## Records and continuity

- Export the signature and agreement-version records at least quarterly and
  after every agreement update.
- Store exports in access-controlled company storage, not in a public
  repository, and do not publish a public contributor-status list.
- Keep at least two DataFog administrators able to manage the integration and
  its signing workflow.
- Review exemptions quarterly and remove stale accounts.
- Re-run the external-contributor test after changes to the CLA integration,
  branch protection, repository ownership, or default branch.
- Document any manual entity CLA, contract-coverage confirmation, historical
  ratification, or special authorization in the same access-controlled legal
  record system.
