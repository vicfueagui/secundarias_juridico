SHELL := /bin/bash

.PHONY: backup-db backup-media backup-code backup-env backup-full verify-backup clone-worktree prepare-clone restore-code restore-env

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

restore-code:
	./scripts/backups/restore_code.sh

restore-env:
	./scripts/backups/restore_env.sh
