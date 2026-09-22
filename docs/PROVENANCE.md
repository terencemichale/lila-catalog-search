# Provenance and limitations

Source project: LILA Fabrics Online Store, maintained by Terence Michale.

The portfolio edition retains the catalog-search and caption-parsing implementation. The dependency on the larger platform scaffold is replaced by a standalone FastAPI app. The shop landing page, legal-policy text, platform routes, real inventory, external URLs, and personal contact fixtures are not included. Test phone numbers use fictional North American 555 examples.

Cleanup was AI-assisted. Included third-party packages retain their own licenses; no new license grant is asserted over external materials.

Search is case-insensitive substring matching, not semantic retrieval. Cache invalidation uses modification time and file size. JSON catalog updates are a single-user workflow. The message adapter is a local demonstration, not an authenticated live webhook.
