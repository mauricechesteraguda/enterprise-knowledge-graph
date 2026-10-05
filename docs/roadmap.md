# Roadmap

## Next

- Complete the remaining ETL and adapter implementations behind the existing ports.
- Run the Compose ETL and integration profile in a clean environment and publish measured
  timings, graph counts, and coverage in `docs/results.md`.
- Add a production GraphStore adapter with secret injection and operational runbooks.

## Later

- Add source-specific identity review tooling and an operator audit view.
- Expand protocol adapters while preserving the bounded catalog and offline test path.

## Explicit non-goals

Terraform, Kubernetes manifests, cloud provisioning, and unrestricted SPARQL are outside
this portfolio baseline.
