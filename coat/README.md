# Coat integration

Three things are installed, each a symlink back into this kit:

| Installed as | Source | Why |
|---|---|---|
| `~/.coat/modules/k8s.sh` | `coat/k8s.sh` | `klab` dispatcher, `k8s_*` helpers, `k*` aliases |
| `$PACZEK_FILLINGS/k8s` | `paczki/k8s` | `paczek k8s` from any folder |
| `$SPELLS/kubernetes` | `coat/spells/k8s` | one-line spells in the magic book |

Plus one line at the end of `~/.coatrc`, after `source $PATH_TO_COAT/coat.sh`:

```bash
[ -f "$PATH_TO_COAT/modules/k8s.sh" ] && source "$PATH_TO_COAT/modules/k8s.sh"
```

The module is sourced from `.coatrc`, not added to `COAT_MODULE_ORDER` in
`coat.sh`, so a `git pull` of Coat never conflicts with this kit.

## Install

```bash
coat/install-coat.sh --dry-run   # see what will happen
coat/install-coat.sh             # symlinks, then asks before editing .coatrc
```

It refuses to overwrite a real file or a foreign symlink, and it backs up
`.coatrc` before appending.

## Use

```bash
klab help
klab up a6
klab status
klab scale --delta 1
klab verify a6
klab down a6
```

In the shell: `klab` (dispatcher), `k8s_pods`, `k8s_all`, `k8s_events`,
`k8s_logs`, `k8s_shell`, `k8s_desc`, `k8s_ctx`, `k8s_watch`, `k8s_curl`, plus
the aliases `kgp kgs kgd kga kgn kge kdp kaf kdel kctx`.

`ALT + s` casts a spell from `coat/spells/k8s`; `paczek k8s` lists the templates;
`loot` still sees only the project types Coat knows.

## Optional: make `loot` recognise this kit

`loot` chooses a paczki prefix from the folder it is in (`coat_loot_type` in
`modules/spells.sh`). To have it pick `k8s` here, add one branch:

```bash
elif [[ -f k8s-lab.conf || -d manifests/a6 ]]; then
  echo k8s
```

That is a change in the Coat repo, so it is documented and not applied by the
installer. `paczek k8s` works without it.

## Uninstall

```bash
rm ~/.coat/modules/k8s.sh
rm "$PACZEK_FILLINGS/k8s" ~/.dotfiles/spells/kubernetes
# remove the source line from ~/.coatrc by hand
```
