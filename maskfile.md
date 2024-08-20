# Run Aider to write code

## chat

> Use Sonnet LLM to drive aider

```bash
source .env
aider --code-theme solarized-light --light-mode --model openrouter/anthropic/claude-3.5-sonnet
```

### install

> Install aider via pipx

```bash
pipx install aider-chat
```

## webui

> Run the aider web ui

```bash
source .env
aider --browser --model openrouter/anthropic/claude-3.5-sonnet
```

### install

> Install aider via pipx with browser support

```bash
pipx install --force aider-chat[browser]
```
