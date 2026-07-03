# Security

Agent Skill Board is intended for local use on `127.0.0.1`.

Before publishing a skills folder or screenshots, review for:

- API keys, access tokens, cookies, app passwords, and OAuth credentials.
- Private hostnames, NAS addresses, VPN/Tailscale IPs, SSH usernames, and internal URLs.
- Personal document paths, vault names, email addresses, and customer/project names.
- Operational runbooks that reveal private infrastructure details.

The web UI only permits opening files and directories inside the configured skills directory. It does not expose delete, archive, sync, or remote publish actions.

If you find a security issue in this project, open a private report or contact the maintainer directly.
