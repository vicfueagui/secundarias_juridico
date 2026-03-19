SHELL := /bin/bash

.PHONY: backup-db backup-media backup-code backup-env backup-full verify-backup clone-worktree prepare-clone prepare-lab restore-code restore-env sync-dev-clone sync-dev sync-lab rebuild-dev rebuild-lab check-dev check-lab

backup-db:
	./scripts/backups/backup_db.sh

backup-media:
	./scripts/backups/backup_media.sh

backup-code:
	./scripts/backups/backup_code.sh

backup-env:
	./scripts/backups/backup_env.sh

backup-full:
	./scripts/backups/backup_full.sh

verify-backup:
	./scripts/backups/verify_backup.sh

clone-worktree:
	./scripts/backups/clone_worktree.sh

prepare-clone:
	./scripts/backups/prepare_parallel_clone.sh

prepare-lab:
	PATH="/usr/local/bin:$$PATH" ./scripts/backups/prepare_parallel_clone.sh --target-dir ../project_secu_juridi_lab --backup-dir ../project_secu_juridi_dev/backups/latest --db-name cejei_licencias_lab --db-port 5543 --nginx-port 8082 --nginx-port-legacy 8002

restore-code:
	./scripts/backups/restore_code.sh

restore-env:
	./scripts/backups/restore_env.sh

sync-dev-clone:
	./scripts/dev/sync_to_parallel_clone.sh

sync-dev:
	./scripts/dev/sync_to_parallel_clone.sh --target-dir ../project_secu_juridi_dev

sync-lab:
	./scripts/dev/sync_to_parallel_clone.sh --target-dir ../project_secu_juridi_lab

rebuild-dev:
	cd ../project_secu_juridi_dev && PATH="/usr/local/bin:$$PATH" docker compose up -d --build web worker nginx

rebuild-lab:
	cd ../project_secu_juridi_lab && PATH="/usr/local/bin:$$PATH" docker compose up -d --build web worker nginx

check-dev:
	cd ../project_secu_juridi_dev && PATH="/usr/local/bin:$$PATH" docker compose exec -T web python manage.py check

check-lab:
	cd ../project_secu_juridi_lab && PATH="/usr/local/bin:$$PATH" docker compose exec -T web python manage.py check
