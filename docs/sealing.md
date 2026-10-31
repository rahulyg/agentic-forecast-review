# Sealing the held-out case seeds

Held-out cases are generated from seeds you have never seen. To make that
checkable, the seeds are encrypted with [`age`](https://age-encryption.org)
before any held-out case is generated, and only an aggregate manifest is public.
They are unsealed in weekend 6, after both freezes:

1. the scripted baseline is tagged `baseline-frozen` (weekend 4), and
2. the agent prompt is tagged (weekend 5).

## What the repository may contain

Only these two files, under `cases/heldout/`:

```
cases/heldout/seeds.jsonl.age
cases/heldout/manifest.json
```

No plaintext seed, family name, planted condition, case, expected result or
model output. The `.gitignore` rule blocks everything else in that directory;
still inspect the staged diff before committing.

## Procedure (weekend 4, after `baseline-frozen` exists)

1. On your own machine, outside the repository, write one JSON object per line
   to a plaintext file: each held-out family's seed and its planted condition.
2. Encrypt it to your own `age` public recipient. Keep the private identity off
   this repository, CI, PRs, shell history and `.env` files.

   ```
   age -r "$AGE_RECIPIENT" -o cases/heldout/seeds.jsonl.age /absolute/path/outside/repo/seeds.jsonl
   shasum -a 256 cases/heldout/seeds.jsonl.age
   ```

   Use standard binary `age` output, not ASCII armour.
3. Write `cases/heldout/manifest.json` with aggregate values only:

   ```json
   {
     "seal_process_revision": "seal-v1",
     "cipher_artifact": {"path": "cases/heldout/seeds.jsonl.age", "format": "age"},
     "cipher_sha256": "<lowercase sha256 of the ciphertext>",
     "total_families": 10,
     "baseline_commit": "<full commit hash that the baseline-frozen tag points to>",
     "sealed_at": "<UTC ISO-8601 timestamp>"
   }
   ```

4. Commit only those two files and run the verifier:

   ```
   uv run python -m agentic_forecast_review.sealing
   ```

## What the verifier proves

It checks the ciphertext digest, the `age` header, that the manifest has
exactly the expected keys, and that `baseline_commit` is a full hash. It does
not decrypt, so it cannot check the plaintext's quality, count or secrecy
before sealing. Git history shows the order: the `baseline-frozen` tag must be
older than the commit that adds the seal.
