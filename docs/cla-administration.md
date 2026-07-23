# CLA Administration Runbook

This runbook describes the rollout and ongoing administration of DataFog's
Contributor License Agreement (CLA). The legal text should be approved by
DataFog's counsel before the hosted integration is activated.

## Service

Use the SAP-hosted [CLA Assistant](https://cla-assistant.io/) integration. Do
not use the archived `contributor-assistant/github-action` workflow.

CLA Assistant uses a GitHub Gist as its agreement source. The reviewed
[`CLA.md`](../CLA.md) in this repository is the source text for the initial
Gist. Treat the Gist revision and repository version as one release: any
substantive change creates a new agreement version and may require contributors
to sign again.

## Pilot rollout

1. Obtain legal approval for `CLA.md`, including the entity name, Delaware law,
   patent grant, and Outbound License Option Five.
2. Create a public Gist owned by a durable DataFog administrative account using
   the approved `CLA.md` contents.
3. Sign in to CLA Assistant with that account and link the Gist to
   `DataFog/datafog-python`.
4. Configure exemptions only for verified DataFog personnel and trusted bot
   accounts. At minimum, review Dependabot, Renovate, release automation, and
   any account that commits generated changes.
5. Open a pull request from a non-member test account and verify that:
   - CLA Assistant requests a signature;
   - signing is tied to the authenticated GitHub account;
   - the `license/cla` status changes from failing to passing; and
   - a new commit by another author causes the pull request to be rechecked.
6. In the branch protection rule for `dev`, require the `license/cla` status
   check. Apply the rule to administrators if the policy is intended to be
   non-bypassable.
7. Verify bot and internal-member pull requests pass using documented
   exemptions.
8. Merge the policy change only when the signing flow and required check have
   both been tested.

## Organization rollout

DataFog currently uses GitHub Free, so organization-wide rulesets are not
available. Repeat the following for every active public repository:

1. Confirm its license, default branch, and contribution guide.
2. Add links to the organization CLA and CLA policy.
3. Enable CLA Assistant using the same agreement version.
4. Protect the default branch and require `license/cla` before merge.
5. Test an external pull request and an exempt bot pull request.
6. Record the repository, protected branch, activation date, agreement version,
   exemptions, and test pull request in the rollout inventory.

If DataFog upgrades to GitHub Team or Enterprise, replace per-repository status
configuration with an organization ruleset targeting the default branches of
the covered public repositories.

## Historical contributions

Before relying on the CLA for commercial or proprietary relicensing of existing
code:

1. inventory historical commits and pull requests by non-DataFog contributors;
2. distinguish original contributions from mechanical or third-party changes;
3. obtain the current CLA from the relevant rights holder; and
4. replace or isolate code where broader rights cannot be obtained.

Do not assume that a newly signed workflow retroactively covers a contributor
who has not accepted the agreement.

## Records and continuity

- Export the signer list and agreement-version records at least quarterly and
  after every agreement update.
- Store exports in access-controlled company storage, not in a public
  repository.
- Keep at least two DataFog administrators able to manage the integration and
  its Gist.
- Review exemptions quarterly and remove stale accounts.
- Re-run the external-contributor test after changes to the CLA integration,
  branch protection, repository ownership, or default branch.
- Document any manual entity CLA or special authorization in the same
  access-controlled legal record system.
