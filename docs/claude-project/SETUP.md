# Set up the two pinned Claude chats (about 5 minutes, on claude.ai)

1. Go to claude.ai → **Projects** → **Create project**. Name it **Stock Query**.
2. **Project instructions:** paste the whole of `docs/claude-project/stock-query.md`.
3. **Project knowledge:** **+** → **GitHub** → choose `prodadarjaiswal-lab/Aj` → tick these files:
   - `docs/technical-desk.md`
   - `docs/auction-desk.md`
   - `docs/n500.json`
   - `docs/hedging-research.md`
   - `docs/fair-value-workbench.html`
   - the newest file in `data/options/`
4. Star (pin) the project so it sits at the top of your sidebar.
5. Repeat for a second project named **Stock Journal**:
   - instructions from `docs/claude-project/journal.md`;
   - knowledge files `docs/technical-desk.md` and `docs/n500.json`.
   - The journal itself is kept encrypted (the repository is public). Send `journal` to the bot and paste the reply into this project.
6. GitHub files in a project do not refresh by themselves. Open the project knowledge and press **Sync** when you start a session, to pull the latest nightly files.

Claude Projects cannot post to Telegram. The bot stays the place for quick answers; the projects are for longer questions and the journal.
