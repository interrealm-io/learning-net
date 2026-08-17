---
name: gke-deploy
description: Build, push, and roll collective to GKE (learningnet.interrealm.org) through the ~/core monorepo and Argo CD. Use when asked to deploy, ship, release, or roll the site to production.
---

# Deploy collective to GKE

This repo (github.com/interwax/collective) is the source of truth. A
vendored copy lives at `~/core` `learningnet/` (realmtrix-ai/core monorepo);
deploying means: sync the vendored copy → build/push the image locally (there
is deliberately no CI build — the ~740MB `data/kg.sqlite` layer can't live in
git) → bump the image tag in the kustomization on core `main` → push → Argo CD
auto-syncs the cluster.

**Never `kubectl apply` by hand** — Argo has selfHeal and will revert it.

## Preconditions — check each, don't assume

1. This repo is clean and its HEAD is pushed to `origin/main`. The image tag
   is this repo's full HEAD sha: `SHA=$(git rev-parse HEAD)`.
2. The committed web bundle is current: if anything under `web/src/` changed
   since the last `npm run build`, rebuild (`cd web && npm run build`) and
   commit — the image serves `src/collective/static/` as-is, no build in
   Docker.
3. `data/kg.sqlite` exists here (~740MB). If missing:
   `collective init --db data/kg.sqlite`.
4. Docker daemon running; gcloud account is `inbox@realmtrix.com`; Artifact
   Registry auth configured for `us-central1-docker.pkg.dev`.

## Steps

Work in a throwaway worktree of core `main` — the ~/core checkout usually has
unrelated work in flight on another branch; never touch it.

```sh
LN=~/clones/collective
SHA=$(git -C "$LN" rev-parse HEAD)
IMG=us-central1-docker.pkg.dev/realmtrix-infra-prod/realmtrix/learningnet:$SHA

git -C ~/core worktree prune
git -C ~/core fetch origin
WT=<scratchpad>/core-deploy
git -C ~/core worktree add "$WT" origin/main
```

1. **Sync the vendored copy** (code + metadata; core's Dockerfile,
   .dockerignore, .gitignore stay as they are):

   ```sh
   rsync -a --delete "$LN/src/" "$WT/learningnet/src/"
   cp "$LN"/pyproject.toml "$LN"/README.md "$LN"/LICENSE "$LN"/DATA-LICENSE.md "$WT/learningnet/"
   mkdir -p "$WT/learningnet/data"
   cp -c "$LN/data/kg.sqlite" "$WT/learningnet/data/kg.sqlite"   # APFS clone: instant, no extra disk
   ```

2. **Build and push** (amd64 — the cluster is x86; local machine is arm):

   ```sh
   docker build --platform linux/amd64 -t "$IMG" "$WT/learningnet"
   docker push "$IMG"
   ```

   `kg.sqlite` is COPY'd as the first layer on purpose: code-only rebuilds
   reuse the cached 700MB layer and pushes stay small. Don't reorder the
   Dockerfile.

3. **Roll the tag**: edit `newTag:` in
   `$WT/infra/k8s/applications/learningnet/kustomization.yaml` to `$SHA`.

4. **Commit and push to core main** (match the existing roll style, e.g.
   `learningnet: roll to <sha8> — <one-line summary of what shipped>`):

   ```sh
   git -C "$WT" switch -c learningnet-roll
   git -C "$WT" add learningnet infra/k8s/applications/learningnet
   git -C "$WT" commit -m "learningnet: roll to ${SHA:0:8} — <summary>"
   git -C "$WT" push origin HEAD:main
   ```

   If main rejects the direct push (branch protection), open a PR with `gh`
   instead and merge it.

5. **Verify**: Argo (App-of-Apps over `infra/k8s/bootstrap/`) auto-syncs from
   main within ~3 min. Then confirm the site serves the new bundle — the
   asset hashes in the live HTML must match this repo's committed
   `src/collective/static/index.html`:

   ```sh
   curl -s https://learningnet.interrealm.org/ | grep -o 'index-[^"]*\.\(js\|css\)'
   ```

   If kubectl is configured: `kubectl -n learningnet rollout status deploy`.

6. **Clean up**: `git -C ~/core worktree remove "$WT" --force` and delete the
   `learningnet-roll` branch.

## Gotchas

- **Rename fallout (until the monorepo catches up).** This repo's Python
  package was renamed `learningnet` → `collective`, but the vendored copy in
  ~/core still lives under `learningnet/` and its Dockerfile runs
  `CMD ["learning-net", "web", ...]`. The first deploy after the rename must
  also update `~/core/learningnet/Dockerfile` (CMD and any comments →
  `collective`) and any `LEARNING_NET_DB` env in the k8s manifests →
  `COLLECTIVE_DB`, or the container will fail to start. The monorepo
  *directory* names (`learningnet/`, image name, namespace) can stay.
- **Terraform is not part of a deploy.** Only touch `infra/terraform/coregke`
  for cert/DNS/domain changes — and if you do: `terraform.tfvars` is
  gitignored and sets `project = realmtrix-infra-prod`; a worktree without it
  silently plans against `realmtrix-test` and produces a plan that REPLACES
  every production cert. Copy tfvars from the main ~/core checkout first and
  read the plan summary (adds only). Auth without ADC:
  `GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token) terraform ...`
- **Root Argo app has no automated sync.** Irrelevant for image rolls; only
  matters when adding a NEW bootstrap Application — then selectively sync it:
  `kubectl patch application root -n argocd --type merge -p '{"operation":{"sync":{"resources":[{"group":"argoproj.io","kind":"Application","name":"<app>","namespace":"argocd"}]}}}'`
- **Hostnames**: learningnet.interrealm.org (primary) + learningnet.interrealm.io.
  Gateway IP 136.110.237.59, Cloudflare DNS-only. Cert/domain lore (Universal
  SSL shadowing `_acme-challenge`, failed-auth cert recovery) lives in the
  project memory `learningnet-gke-deploy` — read it before any cert work.
