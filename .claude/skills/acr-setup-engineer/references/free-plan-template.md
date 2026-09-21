# Claude Free plan template (seed for the Notion page)

This is the seed for the **`Claude Free plan`** page directly under the `ACR Setup Engineer` root:
what works and what doesn't when the skill runs on Claude's Free plan. It is **skill-owned and
auto-maintained**, exactly like `How to use` (`notion-structure.md` → *`How to use` and `Claude
Free plan` pages*). The skill's once-per-chat offline message points here
(`notion-rest-read.md` → *Offline mode*).

> When writing the Notion page, copy everything below the line. Replace `{version}` with the skill
> version (`SKILL.md` → *Skill version*). Every section is a normal heading — this page is short and
> Free users read all of it.

---

# Claude Free plan

> *Maintained by the skill ({version}). Don't write here: updates replace this page.*

On Claude's Free plan the skill can't connect to Notion's API. Only Pro and Max have a setting for
that, and it can't be turned on for Free. The skill checks once at the start of each chat and, when
it can't connect, says so in one line. Nothing is broken. This is what changes.

## What doesn't work

- **Your saved setups can't be read back.** Setups you ticked **`Learn from this`** don't shape new
  setups, and ratings don't either. Your setups are still saved to Notion, and you can open them
  there as usual.
- **A saved game default can't be reused.** When a build starts from the game's default setup,
  you'll be asked for screenshots of it again.

## What works

- Building, changing, reviewing, sharing and saving setups.
- Importing a save file, and saving your own setups from photos.
- **Every car, fully** — bundled ones and the ones you onboarded from screenshots. Their parameter
  lists never need the connection. A car set up by a much older version of the skill may need one
  re-onboard from screenshots. The skill tells you which.
- Anything you give it in the current chat, like screenshots or values you type.

## Things to know

- **Skip the token on the `Config` page.** It needs the connection Free doesn't have.
- **Long chats can hit Free's limits.** Some requests run several steps. If a chat stops, start a
  new one and ask again.

## Moving to Pro or Max

Open Settings → Capabilities → Network egress, choose **All domains**, set up the token on the
`Config` page, and start a new chat. Everything above then works, including learning from your
saved setups.
