# Engineering Decision Log

| ID | Decision | Rationale |
| --- | --- | --- |
| 001 | Use Python 3.12, uv, and a repository-local virtual environment. | A minor-version pin and an exact dependency lock reduce environment drift while allowing Python patch updates. |
| 002 | Install pytest as the only direct development dependency in Phase 1. | The initialization checks need no ML, API, or infrastructure libraries. Add each library when its first caller arrives. |
| 003 | Keep one monorepo with a CPU-first local workflow. | Contracts and their consumers can evolve together during early development. Native Apple Silicon verification is a release check for later dependencies. |
| 004 | Use chronological data partitions and point-in-time behavioral features. | Random splits and globally computed behavioral aggregates can overstate real-time model performance. |
| 005 | Store predictions and analyst dispositions independently. | A score is evidence available at decision time. A disposition is an attributed action that can arrive later. |
| 006 | Keep Compose configuration for the first service integration. | A Compose file becomes executable when it has a real service and a verification path. The infrastructure directory reserves its place. |
| 007 | Validate the original ZIP directly with Python's standard library. | Streaming avoids extracting a second copy of the transactions and needs no dependency updates. Exact duplicate detection retains transaction IDs in memory for one validation run. |
| 008 | Preserve the publisher's train/test boundary and report both time representations. | The source test partition can stay held out. The observed difference between the timestamp fields must be understood before choosing event-time semantics. |
