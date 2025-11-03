## Lock Generator (`scripts/lock/generate_lock.py`)

### Quick usage

```
python -m scripts.lock.generate_lock \
  --image-metadata .github/images.json \
  --output locks/lock-preview.yml
```

- Add `--services orders inventory` to restrict the scope.
- Use `--default-tag-prefix main-` only if you want a global prefix (not needed when `tag_prefix` is defined in `images.json`).
- `--force` overwrites an existing lock file.

### `.github/images.json`

Each entry defines at least the image repository and optionally:

- `tag_prefix`: prepend this value to the 7-char git SHA (e.g. `main-`).
- `tag`: fixed tag to use as-is.
- `digest`: OCI digest if the image should be pinned exactly.

Example:

```json
{
  "shopifake-orders": {
    "repository": "ghcr.io/shopifake/shopifake-orders",
    "tag_prefix": "main-"
  }
}
```

With a commit `234e5bda…`, the resulting lock entry will reference the tag `main-234e5bd`.

### Lock structure

- `metadata`: timestamp, generator id, branch, monorepo commit SHA.
- `services`: map of service name → `{submodule_path, git_sha, image}`. The `image` block includes `repository`, `tag`, and optionally `digest`.

Validate with the schema stored in `locks/schema.json`:

```
python -m jsonschema -i locks/lock-preview.yml locks/schema.json
```

### Notes

- If neither `tag` nor `tag_prefix` is provided, the tag defaults to the first 7 characters of the SHA.
- Infrastructure submodules (`infra/*`) are handled the same as application services.
- Future Python services can be added to `.github/images.json` once their pipelines publish images.

