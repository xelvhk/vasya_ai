# What's New / Что нового

Short, user-facing release notes for Vasya AI. Keep `CHANGELOG.md` technical and use this file for the friendlier "what changed for me?" version.

Короткие заметки для пользователя. `CHANGELOG.md` остается техническим, а здесь можно писать человеческим языком: что Вася теперь умеет и почему это приятно.

## v0.6.0 - Installation & First-Run

В этой версии Вася научился готовить утренний брифинг и меньше паниковать при первом запуске.

### Что нового
- Утренний брифинг теперь собирает погоду, задачи, события календаря и контекст Memory Center в один daily-flow.
- Полный брифинг сохраняется локальным Markdown-файлом, поэтому голосовой ответ остается коротким, а детали не теряются.
- Установка на macOS стала ближе к формату "скачал, запустил, проверил": основной путь теперь идет через `scripts/setup_mac.sh`.
- Для нового локального `.env` автоматически создается API-токен, а существующий `.env` Вася не трогает.
- `doctor` стал внимательнее: проверяет Python, virtualenv, зависимости, Ollama, TTS, storage, Memory wiki, API auth, optional integrations и autostart.
- CI теперь делает настоящую проверку качества: compile checks, unit tests и strict doctor smoke.

### Зачем это нужно
- Новый пользователь быстрее доходит от `git clone` до первого полезного ответа Васи.
- У проекта появилась понятная demo-история: установка, doctor, утренний брифинг.
- Local-first подход сохранился: setup не отправляет секреты наружу и не перезаписывает существующую конфигурацию.

### Настроение релиза
Вася все еще не Джарвис. Но он уже приносит утренний контекст, бережно складывает детали в Markdown и заметно спокойнее относится к первому запуску.

### English short version
- Morning Brief now gathers weather, tasks, calendar events, and Memory Center context into one daily flow.
- Full briefings are saved as local Markdown files, so the spoken summary stays short while the details remain available.
- macOS setup is now a one-command path through `scripts/setup_mac.sh`.
- New local `.env` files get a generated API token automatically, while existing `.env` files are left alone.
- `doctor` checks the first-run environment more carefully: Python, virtualenv, dependencies, Ollama, TTS, storage, Memory wiki, API auth, optional integrations, and autostart.
- CI now runs real quality gates: source compile checks, unit tests, and strict doctor smoke.

## v0.5.50 - Memory Search Quick-Open

В этой версии Вася перестал просто показывать найденное в памяти и начал сразу открывать нужные файлы и ссылки.

### Что нового
- Memory Center search получил quick-open действия для локальных файлов и source URLs.
- Search/digest/recent flow стал больше похож на рабочий инструмент, а не на витрину API.
- Документация релиза была собрана в аккуратный официальный `v0.5.50`.

### Настроение релиза
Память стала не просто "я где-то это видел", а "вот оно, открываю".

## v0.5.25 - Memory Center Foundation

В этой версии у Васи появилась более взрослая память: локальные источники, чанки, Markdown-артефакты и статус синхронизации.

### Что нового
- Добавлена основа Memory Center: local sources/chunks, wiki artifacts и sync-state tracking.
- Появился `/v1/memory/status`, чтобы понимать, что с памятью происходит.
- Вася начал двигаться от "помню пару фактов" к нормальному second-brain слою.

### Настроение релиза
До этого Вася делал заметки. После этого он начал раскладывать мысли по полкам.

## v0.5.21 - Security Hardening

В этой версии Вася стал осторожнее с API, токенами и логами.

### Что нового
- API auth стал строгим по умолчанию.
- Интеграционные токены начали уходить в keyring, когда он доступен.
- Логи получили redaction, чтобы секреты не гуляли там, где им не место.
- Dictation API получил safer host allowlist.

### Настроение релиза
Вася понял, что "работает у меня на ноутбуке" не отменяет замки на дверях.

## v0.5.10 - API Gateway

В этой версии у Васи появился API-шлюз для будущих web/mobile клиентов.

### Что нового
- Добавлен `apps/api` как FastAPI foundation.
- Core logic начал становиться доступным не только из desktop shell.
- Это подготовило дорогу к web-панели, мобильным клиентам и внешним thin clients.

### Настроение релиза
Вася впервые выглянул из desktop-окна и сказал: "а можно я буду еще и API?"

## v0.5.0 - Product Shell Polish

В этой версии desktop shell стал ощущаться больше как продукт, а не как инженерный прототип.

### Что нового
- Добавлены hover tooltip и status indicator.
- Avatar/widget surface стал понятнее для ежедневного использования.
- Desktop UX начал обрастать маленькими, но важными сигналами состояния.

### Настроение релиза
Вася еще не надел костюм, но уже перестал приходить на встречу в черновике.

## v0.4.0 - First Desktop Widget

В этой версии Вася получил первый плавающий avatar widget и assistant state layer.

### Что нового
- Появился первый desktop widget MVP.
- Click-to-talk стал ближе к настоящему desktop assistant опыту.
- Состояния ассистента начали отображаться визуально, а не только жить в логике.

### Настроение релиза
До этого Вася был голосом из терминала. Теперь у него появилось лицо на рабочем столе.

## v0.1.0 - Draft Foundation

В этой ранней линии родился базовый контур: голос, интенты, задачи, календарь, локальное хранилище и первые интеграции.

### Что нового
- Локальный voice pipeline: STT -> intent -> tool dispatch -> TTS.
- Базовые task/calendar workflows.
- SQLite/local-first storage.
- Первые Obsidian/Notion/GitHub hooks.
- Начало Memory Center foundation.

### Настроение релиза
Это был момент, когда Вася впервые сказал: "я, кажется, могу быть полезным".

## Micro-Release Timeline

Короткая живая лента небольших релизов. Для точных технических деталей см. `ROADMAP.md`, `CHANGELOG.md` и `docs/RELEASE_NOTES.md`.

- `v0.5.51`: doctor получил `--json`, `--strict` и `--quiet`, чтобы диагностика стала удобной и для людей, и для CI.
- `v0.5.49`: doctor baseline научился говорить `OK/WARN/FAIL` вместо загадочного "ну, попробуем".
- `v0.5.48`: Memory search popup стал компактнее, чтобы результаты можно было читать глазами, а не археологическими инструментами.
- `v0.5.47`: latest digest стал one-click действием с auto-build fallback.
- `v0.5.46`: tray digest UX стал спокойнее и перестал дублировать похожие действия.
- `v0.5.45`: latest digest получил быструю voice/text команду.
- `v0.5.44`: появился прямой endpoint `/v1/memory/digests/latest`.
- `v0.5.43`: digest history научился понимать `today` и `yesterday`.
- `v0.5.42`: desktop получил быстрые open-digest действия для today/yesterday.
- `v0.5.41`: tray получил day presets для digest history.
- `v0.5.40`: tray получил 7-day и 30-day digest presets.
- `v0.5.39`: digest history получил `range=7d|30d`.
- `v0.5.38`: digest history научился фильтроваться по date range.
- `v0.5.37`: desktop получил действие "открыть последний digest".
- `v0.5.36`: появилась история digest'ов через API, desktop и fast command.
- `v0.5.35`: daily digest стал доступен из desktop menu.
- `v0.5.34`: Memory Center научился делать deterministic daily digest Markdown artifacts.
- `v0.5.33`: recent Memory Center появился в desktop menu.
- `v0.5.32`: recent view начал отвечать на вопрос "что нового в памяти?".
- `v0.5.31`: появились быстрые voice/text команды для Memory Center status, sync и search.
- `v0.5.30`: desktop получил Memory Center search action.
- `v0.5.29`: Memory Center search появился как provenance-backed local retrieval.
- `v0.5.28`: Memory Center получил background scheduler.
- `v0.5.27`: desktop shell получил Memory Center controls.
- `v0.5.26`: GitHub, Notion и Obsidian начали синкаться в Memory Center.
- `v0.5.24`: Obsidian vault bootstrap стал управляемым, с папками, шаблонами и индексами.
- `v0.5.23`: security tests начали проверять auth, throttling и log redaction.
- `v0.5.22`: API/WS throttling добавил защиту от слишком бодрых клиентов.
- `v0.5.20`: continuous dictation mode получил start/stop, punctuation helpers и focus-safe guardrails.
- `v0.5.19`: диктовка в активное поле стала fast-path командой.
- `v0.5.18`: появился streaming pipeline, realtime WebSocket mode, modular STT/TTS/LLM registry и benchmark harness.
- `v0.5.17`: morning show начал кешироваться заранее, чтобы "доброе утро" не звучало сонно.
- `v0.5.16`: Вася научился обновлять Obsidian заметки и синкать GitHub project notes.
- `v0.5.15`: runtime prewarm стал прогревать STT/Ollama до того, как пользователь успел заскучать.
- `v0.5.14`: XTTS и hybrid speech mode добавили путь к более натуральному голосу.
- `v0.5.13`: voice metrics начали сравнивать routing/prompt profiles и TTFR/TTA.
- `v0.5.12`: OS action tools получили safety policy, а routing - role specs и prompt packs.
- `v0.5.11`: context/action layer добавил selected text, screenshot-aware prompts и slash-style быстрые действия.
- `v0.5.9`: A/B voice metrics, auto-interrupt thresholds и live health hints сделали голосовой контур наблюдаемее.
- `v0.5.8`: появились voice-open text window, первое morning show и быстрее fast-lane routing.
- `v0.5.7`: desktop text command window дал точный ввод без борьбы с распознаванием речи.
- `v0.5.6`: speed report и latency metrics впервые честно показали, где Вася думает, а где тормозит.
- `v0.5.5`: quick chat profile ускорил короткие разговорные ответы.
- `v0.5.4`: Notion adapter и GitHub -> Notion sync сделали Васю полезнее для project notes.
- `v0.5.3`: personal memory стала управляемой: запомнить, забыть, показать.
- `v0.5.2`: tool registry, routing policy и handoff rules начали превращать ассистента в систему.
- `v0.5.1`: mini tooltips добавили маленькие подсказки к состояниям.
- `v0.4.7`: first-run onboarding получил checklist и progress.
- `v0.4.6`: avatar personalization добавил скины, палитры и пользовательские картинки.
- `v0.4.5`: two-stage STT и quality profiles сделали распознавание речи спокойнее и точнее.
- `v0.4.4`: voice responsiveness и child-safe/game UX стали аккуратнее.
- `v0.4.3`: заметки, локальная память и Obsidian export сделали Васю ближе к second brain.
- `v0.4.2`: появился child game mode и отдельный game agent.
- `v0.4.1`: conversational UX, confirmations и faster chat path сделали общение менее деревянным.
- `v0.3.x`: базовый voice MVP собрал задачи, календарь, локальное хранилище и Google Calendar в первый полезный контур.

