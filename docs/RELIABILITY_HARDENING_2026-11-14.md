# Vasya AI reliability hardening — 14 November 2026

## Risk and change

| Risk | Change | Local verification |
| --- | --- | --- |
| Security test changed `sys.modules` and broke later tests | Use installed FastAPI in the test without global module replacement | Previously 18 passed and 8 failed in the focused group; after the fix, 26 passed |
| Upload requests could start excessive media work | Per-peer request quotas, per-route active-work limits, bounded rate buckets, `429` with retry hint | Parallel video-upload test and focused limiter tests pass |
| Local proxy headers could change rate-limit identity | Reject `X-Forwarded-For`, use socket peer, document `--no-proxy-headers` startup | HTTP and WebSocket spoof-header tests pass |
| Dependency and credential regressions may escape tests | Add `pip-audit` and Gitleaks CI jobs; read-only workflow token | Workflow parsed locally; first GitHub run still pending |
| Model speed decisions lacked repeatable baseline | Add synthetic short-command, long-chat and grounded-note benchmark | Benchmark unit tests pass; live Ollama baseline recorded on 15 November |

## Before and after

- Focused security/API test group: **18 pass, 8 fail → 26 pass, 0 fail** after removing the test module leak.
- Full local suite after hardening: **498 pass, 35 subtests pass**. This does
  not establish remote CI status.
- Synthetic Mac baseline on 15 November, `llama3:latest`, five warm runs:
  long chat first text p50/p95 **169/184 ms**, full answer **6971/7413 ms**;
  grounded note first text **149/175 ms**, full answer **2770/2865 ms**.
  All ten model runs passed the simple output checks. The loaded model occupied
  about **5.2 GB** according to Ollama. One cold long-chat run took **15.5 s**.
  Raw aggregate JSON is in `build/benchmarks/local-paths-2026-11-15.json`.
- The existing voice report contains only eight historical interactions:
  average total **46 s**, capture **7.7 s**, STT **8.2 s**, intent **13.2 s**,
  TTS **15.3 s**. These are too few and too old to justify a production
  configuration change. The speed report now shows p95 by stage for the next
  representative session. No speedup is claimed yet.

## Release gate

Review the first GitHub dependency and secret scan, resolve any reported
findings, and confirm green CI. Then resume the EventKit read-only connector
in `docs/EXECUTION_PLAN.md`. macOS packaging and clean-machine checks follow
the existing queue; the unsigned ZIP remains a tester artifact.
