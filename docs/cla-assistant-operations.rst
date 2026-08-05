========================
CLA Assistant Operations
========================

This runbook records the intended production configuration for DataFog's
self-hosted CLA Assistant. Do not place credentials, private keys, database
URIs, or exported signature records in this repository.

Production Identity
===================

* Public URL: ``https://cla.datafog.ai``
* GitHub organization: ``DataFog``
* Initial protected repository: ``DataFog/datafog-python``
* Agreement: `CLA.md <../CLA.md>`_, version 1.0
* Administrator allowlist: ``sidmohan0``

The service runs separately from the static ``datafog.ai`` landing page. The
``cla.datafog.ai`` DNS record points at the production CLA service without
changing the apex or ``www`` landing-page records.

GitHub Configuration
====================

The production instance uses both a GitHub OAuth App for interactive login and
a GitHub App for repository installation and webhooks.

OAuth App:

* Homepage URL: ``https://cla.datafog.ai``
* Authorization callback URL:
  ``https://cla.datafog.ai/auth/github/callback``

GitHub App:

* Homepage URL: ``https://cla.datafog.ai``
* Callback URL: ``https://cla.datafog.ai/auth/github/app-callback``
* Webhook URL: ``https://cla.datafog.ai/github/webhooks``
* Install only on the repositories that require the CLA check.
* Grant only the repository permissions required by the upstream CLA Assistant
  release. Re-check the upstream documentation before expanding permissions.

The app secrets and private key belong in the hosting provider's secret store.
Rotate a credential immediately if it appears in logs, shell history, a pull
request, or a repository file.

Agreement Linkage
=================

The CLA Assistant record must point to an immutable, reviewable copy of
``CLA.md``. The public repository copy is the canonical text. If the
application requires a GitHub Gist, keep the Gist byte-for-byte identical to
``CLA.md`` and record the source commit in the Gist description.

The signing form should request only:

* Full legal name (required)
* Email address (required, prefilled from GitHub when available)
* Signing capacity: individual or on behalf of an organization (required)
* Organization name (only when signing for an organization)
* Confirmation that the signer has authority to submit the contribution
  (required)

Avoid collecting postal addresses, phone numbers, or other information that is
not needed to establish the agreement.

Merge Protection
================

After one test pull request completes the signing flow:

#. Add the CLA Assistant status to the ``dev`` branch's required checks.
#. Add the same check to ``main`` if pull requests can target ``main``
   directly.
#. Confirm that unsigned, signed, multi-author, and approved bot pull requests
   produce the expected result.
#. Do not merge by bypassing the check except during a documented service
   incident.

Dependabot and other approved bots cannot sign. Add bot identities through the
CLA Assistant administration UI; never import a human contributor as signed
without evidence of acceptance.

Updating The Agreement
======================

Treat any text change as a new agreement version:

#. Obtain legal review of the proposed change.
#. Merge the reviewed ``CLA.md`` update.
#. Update the CLA Assistant source to the exact merged text.
#. Verify that the application requests a new signature when required.
#. Export and securely archive the prior version's signature list before the
   new version becomes active.

Backup And Incident Response
============================

* Back up the database on a schedule appropriate for legal records and test a
  restore at least quarterly.
* Export the signature list after every agreement-version change and before a
  hosting migration.
* Monitor the public health endpoint, GitHub webhook deliveries, database
  availability, and TLS certificate expiration.
* If the service is unavailable, keep the required check enabled and pause
  merges rather than silently accepting unsigned contributions.
