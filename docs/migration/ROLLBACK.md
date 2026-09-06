# Rollback and private restoration

The pre-integration canonical main is `d1eefbeaf9aa01c55229f28aaf809d4800596c5e` (v0.9a). Existing tags and release attachments must not move or be replaced.

Revert the integration merge through a normal reviewed pull request if a regression is found. Do not reset main, force-push, delete tags, overwrite local work or restore an entire legacy tree over this repository. The game-producing sources are unchanged by this integration.

The owner has a durable private backup set identified as `narikiri2-consolidation-20260907`, outside both public working trees. Public reports intentionally omit its personal absolute path. The final local handoff identifies it.

For each repository it contains:

- `remote.git`: mirror with remote branches, tags and accessible PR head/merge refs;
- `local-all.bundle`: local branches/tags/remotes and other reachable refs;
- `remote-refs.txt`, `refs.txt`, binary working/staged diffs and reflogs;
- `working-files/` plus a SHA-256/size manifest, including ignored private evidence and local untracked work;
- paginated GitHub metadata, release assets and archive-member hashes;
- successful restore-trial refs comparison and `git fsck --full` output.

Separate attached worktrees are under `additional-worktrees/`. Generated Python caches, virtual environments and Node modules are excluded as regenerable; pinned manifests/lockfiles and authored/generated font inputs are retained. Junction targets are recorded, and the legacy target data was independently copied.

Restore into a **new private directory**:

```powershell
git clone --mirror "<backup>/narikiri2-save-compat/local-all.bundle" "<new-private-path>/canonical.git"
git -C "<new-private-path>/canonical.git" fsck --full
git -C "<new-private-path>/canonical.git" show-ref
```

Compare refs with the saved manifest. Use `remote.git` when restoring server-only refs; use the local bundle for local work. Restore selected working files from the matching manifest only after checking SHA-256. Inspect saved patches before applying them in a new checkout. Never publish the private backup, ROMs, old development patches, complete source corpus or evidence files. No mirror push is part of restoration.

GitHub issues/comments/reviews/releases are preserved as API JSON and assets; a Git clone alone does not restore them. Keep original author/time fields as historical metadata, not newly fabricated conversations. Archived legacy refs remain available read-only. Unarchiving, if ever needed, requires a separate explicit decision; it is not an automatic rollback step.
