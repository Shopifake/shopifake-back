## Objectif

Définir les artefacts, responsabilités et étapes du nouveau flux d’orchestration CI/CD piloté depuis `shopifake-back`.

## Vue d’ensemble

- `dev`, `staging`, `main` deviennent les branches de référence.
- Tous les microservices publient leurs images Docker taggées par SHA de commit.
- Les transitions `dev` → `staging` sont initiées manuellement via une PR ; le pipeline génère automatiquement le lock associé à cette PR.
- Après merge vers `staging`, les déploiements Staging et Prod consomment ce **lock** commun garantissant la parité des environnements.

## Artefacts partagés

| Artefact | Contenu | Responsable | Stockage |
| --- | --- | --- | --- |
| Lock de lot | Pour chaque microservice : SHA Git, tag d’image (SHA), digest OCI, date | workflow CI (PR dev→staging) | Artefact CI + commit sur merge staging |
| Scripts | `scripts/generate_lock.py`, utilitaires d’orchestration | repo central | versionnés |
| Rapports QA | Résultats lint/tests/E2E | GitHub Actions | artefacts CI + commentaires PR |

## Préparation locale (manuel)

- Les développeurs mettent à jour manuellement les sous-modules désirés, testent en local, puis poussent leurs modifications sur `dev`.
- Aucune automatisation centrale : cette étape reste un atelier local avant la création de la PR dev → staging.

## Promotion dev → staging (manuelle + lock auto)

1. Les développeurs créent manuellement la PR `dev` → `staging`, contenant uniquement les mises à jour des sous-modules et modifications associées.
2. À l’ouverture, la CI exécute lints/tests et génère automatiquement un lock (SHA Git + tags + digests) stocké comme artefact et/ou commentaire PR.
3. La PR est fusionnée manuellement lorsque tous les checks sont verts ; aucune auto-merge n’est configurée.
4. Lors du merge, le workflow ajoute le lock au dépôt `staging` (commit automatique) pour qu’il devienne la référence des déploiements.

## Post-merge vers staging

1. Workflow déclenché sur `staging` après merge.
2. Étapes :
   - Récupération du lock ajouté lors du merge (fichier versionné dans `staging`).
   - Validation santé du cluster Staging (API, quotas, dépendances critiques). Si KO, stop.
   - Déploiement via le lock (images figées) déclenché automatiquement après les checks, avec possibilité de relance manuelle (`workflow_dispatch`) si nécessaire.
   - Exécution de la même suite E2E/système que précédemment mais contre Staging réel (DB Staging, intégrations vivantes).
   - Si succès, création de la PR `staging` → `main` contenant le lock (inchangé).
   - Si échec, pas de PR ; on corrige et on relance le déploiement manuel.

## PR staging → main et Production

1. **PR `staging` → `main`**
   - Nécessite 4 validations manuelles.
   - Reviewers testent les environnements Staging déjà déployés via le lock.
2. **Workflow post-merge sur `main`**
   - Health check Prod bloquant.
   - Déploiement Prod depuis le même lock, déclenché automatiquement après merge, avec possibilité de relance manuelle (`workflow_dispatch`) si nécessaire.
   - Smoke tests post-déploiement.
   - Tag de release + archivage du lock (facilite rollback).

## Pré-requis côté microservices

- Maintenir la stratégie de build existante : CI propre à chaque repo, image Docker taggée par SHA.
- Exposer les métadonnées nécessaires (digest, version, API spec) en sortie de CI pour consommation par le lock central.
- S’assurer que les référentiels supportent les bumps de sous-modules (pas de commits locaux non poussés).

## Étapes suivantes

1. Définir le format exact du lock (`locks/schema.json`, modèle YAML).
2. Esquisser les scripts/bibliothèques partagées nécessaires à la génération et à la consommation du lock.
3. Décrire les workflows GitHub Actions : structure des jobs, permissions requises, secrets, déclenchements automatiques + relances manuelles possibles.
4. Mettre en place la documentation utilisateur (README orchestrateur, guide déclencheur).

