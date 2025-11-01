## Structure des workflows GitHub Actions

> Document en français. Version anglaise dans `docs/ci/workflows.en.md`.

Ce guide décrit les pipelines GitHub Actions à introduire dans `shopifake-back` pour automatiser le flux CI/CD présenté dans `overview.fr.md`.

### 1. Workflow `ci-dev-pr.yml`

- **Déclencheurs** : `pull_request` visant `staging` depuis `dev`.
- **Objectifs** :
  - Vérifier les mises à jour de sous-modules (lint, tests unitaires, intégration simulée).
  - Générer automatiquement le lock (`locks/<pr-number>.yml`).
  - Publier le lock en artefact et en commentaire PR.
- **Jobs clés** :
  1. `checkout` + `submodule-sync` (script `scripts/submodules/sync.sh`).
  2. `lint-and-test` : Maven pour services Java, futur tox/pytest pour services Python, avec exécution des tests unitaires et systèmes (build + démarrage de l’ensemble des services nécessaires via Compose/k8s mocks).
  3. `generate-lock` : script Python exportant SHA Git, tags d’images, digests OCI.
  4. `upload-artifacts` et `comment-lock`.

### 2. Workflow `ci-staging-post-merge.yml`

- **Déclencheurs** : `push` sur `staging` et `workflow_dispatch` (relance manuelle).
- **Objectifs** :
  - Récupérer le lock commité lors du merge de la PR.
  - Vérifier la santé du cluster Staging.
  - Déployer automatiquement en Staging avec le lock.
  - Exécuter la suite E2E contre l’environnement réel.
  - Créer la PR `staging` → `main` en cas de succès.
- **Jobs clés** :
  1. `prepare` : checkout + parsing du lock.
  2. `staging-healthcheck` : script `scripts/cluster/healthcheck.sh --env staging`.
  3. `deploy-staging` : apply manifests/Helm/ArgoCD avec les images du lock.
  4. `e2e-staging` : tests fonctionnels et systèmes couvrant les interactions entre services (stack montée avec les images du lock).
  5. `create-promotion-pr` : ouverture de la PR `staging` → `main` avec le lock inchangé.

### 3. Workflow `ci-prod-post-merge.yml`

- **Déclencheurs** : `push` sur `main` et `workflow_dispatch`.
- **Objectifs** :
  - Lire le lock promu depuis `staging`.
  - Vérifier la santé de Production.
  - Déployer en Production avec les images figées.
  - Lancer les smoke tests.
  - Taguer la release et archiver le lock.
- **Jobs clés** :
  1. `prepare` : checkout + lock.
  2. `prod-healthcheck` : `scripts/cluster/healthcheck.sh --env prod`.
  3. `deploy-prod` : déploiement identique à Staging.
  4. `smoke-tests` : vérification rapide post-déploiement.
  5. `release-tag` : tag Git + upload du lock en artefact longue durée.

### 4. Scripts et dépendances

- Scripts shell/Python rangés sous `scripts/` (ex : `scripts/lock/generate.py`).
- Secrets requis :
  - Token GitHub pour commenter/créer des PR.
  - Kubeconfigs Staging et Production.
  - Credentials registry (pull images privées).
- Permissions minimales :
  - `contents: write` pour committer le lock sur `staging`.
  - `pull-requests: write` pour commenter et ouvrir la promotion PR.

### 5. Artefacts générés

- `lock` : fichier YAML + checksum.
- `reports` : résultats des tests (JUnit, coverage, lint).
- `deployment-logs` : journaux de déploiement pour audit.

### 6. Points de contrôle manuels

- Les workflows Staging et Prod disposent d’un `workflow_dispatch` pour relance.
- La PR `staging` → `main` reste validée par quatre reviewers manuellement.

### 7. Prochaines étapes

1. Écrire les squelettes YAML des trois workflows.
2. Implémenter les scripts `generate_lock.py`, `healthcheck.sh`, `deploy.sh`.
3. Configurer les secrets/permissions GitHub Actions.
4. Documenter l’usage côté équipe (README orchestrateur, guides déclencheurs).

