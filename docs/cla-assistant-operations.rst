========================
CLA Assistant Operations
========================

This runbook records DataFog's production CLA Assistant configuration. Do not
place exported signature records or other contributor personal information in
this repository.

Production Configuration
========================

* Branded entry point: ``https://cla.datafog.ai``
* Hosted service: ``https://cla-assistant.io``
* GitHub organization: ``DataFog``
* Protected repository: ``DataFog/datafog-python``
* Agreement: `CLA.md <../CLA.md>`_, version 1.0
* Agreement Gist:
  ``https://gist.github.com/sidmohan0/c7f98b0c28a9d827c0a1a570102e0b89``
* Required GitHub status context: ``license/cla``

SAP's managed CLA Assistant deployment handles GitHub authentication, webhook
processing, and signature storage. DataFog does not operate a separate CLA
Assistant application or database.

The branded entry point is a redirect-only Vercel project named
``datafog-cla-redirect``. The ``cla.datafog.ai`` DNS record is a DNS-only CNAME
to ``e2c831ea94af969f.vercel-dns-016.com``. It must redirect every path to
``https://cla-assistant.io/DataFog/datafog-python`` without changing the apex
or ``www`` landing-page records.

Agreement And Signing Form
==========================

The repository ``CLA.md`` file is the canonical agreement. CLA Assistant reads
an unlisted GitHub Gist containing two files:

* ``DataFog-CLA.md`` must remain byte-for-byte identical to ``CLA.md``.
* ``metadata`` defines the contributor form fields.

The signing form requests only:

* Full legal name (required and prefilled from GitHub when available)
* Email address (required and prefilled from GitHub when available)
* Signing capacity: individual or on behalf of an organization (required)
* Organization name (optional; used when signing for an organization)
* Confirmation that the signer has authority to submit the contribution
  (required)

Avoid collecting postal addresses, phone numbers, or other information that is
not needed to establish the agreement. Because the Gist is unlisted rather
than private access-controlled storage, do not put secrets or signature data in
it.

Contributor Flow
================

#. A contributor opens a pull request against ``dev``.
#. CLA Assistant comments with the signing link and sets ``license/cla`` to
   pending.
#. The contributor signs in with the GitHub account associated with the pull
   request, reviews the agreement, completes the form, and selects ``I agree``.
#. CLA Assistant records the acceptance and changes ``license/cla`` to success.
#. If a pull request has multiple human authors, every author must sign.

Dependabot and other approved bots cannot sign. Add bot identities through the
CLA Assistant administration UI; never import a human contributor as signed
without evidence of acceptance.

Merge Protection
================

After one test pull request completes the signing flow:

#. Add ``license/cla`` to the required checks for the ``dev`` branch.
#. Add the same check to ``main`` if pull requests can target ``main``
   directly.
#. Confirm that unsigned, signed, multi-author, and approved-bot pull requests
   produce the expected result.
#. Do not bypass the check except during a documented service incident.

Updating The Agreement
======================

Treat any text change as a new agreement version:

#. Export and securely archive the current signature list from the CLA
   Assistant dashboard.
#. Obtain legal review of the proposed change.
#. Merge the reviewed ``CLA.md`` update.
#. Replace only the ``DataFog-CLA.md`` Gist file with the exact merged text;
   retain the ``metadata`` file unless the form is intentionally changing.
#. Verify that CLA Assistant displays the new version and requests a new
   signature when required.

Operations And Incident Response
================================

* Restrict CLA Assistant administration to DataFog maintainers who need it.
* Export signature records after an agreement-version change and before any
  service migration; store exports in DataFog's access-controlled records
  system, not GitHub.
* Monitor the hosted service, the ``license/cla`` check, the branded redirect,
  and TLS certificate health.
* If the hosted service is unavailable, keep the required check enabled and
  pause merges rather than silently accepting unsigned contributions.
* Review the managed service's terms and privacy policy when DataFog changes
  the personal information collected in the signing form.

Self-hosting is not the current production architecture. Re-evaluate it only
if DataFog needs controls the managed service cannot provide and after the
upstream runtime, dependencies, database, backups, security updates, and
on-call ownership have been reviewed.
