# Contributing

Thanks for your interest in improving `vasya_ai`.

## Local Setup
```bash
git clone https://github.com/xelvhk/vasya_ai.git
cd vasya_ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Run basic checks:
```bash
python -m compileall .
```

## Development Flow
1. Create a branch from `main`.
2. Keep commits focused and small.
3. Update docs when behavior changes.
4. Open a PR with a short test plan.

## Pull Request Checklist
- [ ] Code compiles and app starts
- [ ] README/docs updated if needed
- [ ] No secrets in commits
- [ ] Changes are scoped to one problem
