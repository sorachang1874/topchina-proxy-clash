# TopChina Proxy Clash

Converts the public `TopChina/proxy-list` Markdown table into a Clash-compatible
subscription file. The generated nodes are used directly as Clash traffic exits;
this project does not depend on RackNerd, Argo, or the existing `argo-sub`
generator.

Subscription URL:

```text
https://raw.githubusercontent.com/sorachang1874/topchina-proxy-clash/main/dist/clash.yaml
```

The upstream list rotates proxy usernames frequently, so this repository updates
`dist/clash.yaml` every hour through GitHub Actions. The upstream password is
currently `1`.

## Local usage

```bash
python3 scripts/convert_topchina_proxy_list.py --output dist/clash.yaml
python3 -m unittest discover -s tests
```

Optional environment variables:

- `SOURCE_URL`: source Markdown URL. Defaults to `TopChina/proxy-list` README.
- `PROXY_PASSWORD`: proxy password. Defaults to `1`.
- `CLASH_TEST_URL`: URL used by the Clash `url-test` group.

## Output

The generated Clash config contains:

- HTTP proxies with username/password auth.
- A `TopChina Auto` url-test proxy group.
- A `TopChina Select` select group.
- A final `MATCH,TopChina Select` rule.
