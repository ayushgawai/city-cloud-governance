"""city-cloud-governance: offline governance / cost reference implementation.

The Terraform modules under ``modules/`` are the deployable artefact.
This package mirrors their policy and cost logic in pure stdlib Python so
``plan`` / ``score`` / ``forecast`` / ``bench`` can run anywhere — no AWS
credentials, no network — against a fixture account tree.
"""
__version__ = "0.1.0"
