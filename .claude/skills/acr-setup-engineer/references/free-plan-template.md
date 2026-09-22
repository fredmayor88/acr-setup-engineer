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

## What's different

- **Your saved setups are read from a list, not from the table.** Every setup the skill saves
  from v{version} on is listed on the car's `Setups` page, under the heading `Setup index`. When
  you build, the skill reads the listed setups closest to your stage, **up to 6**, and uses the
  ones you ticked **`Learn from this`**, with their ratings. It tells you which ones it read. Say
  **"also learn from my other Lancia Stratos setups"** to read more.
- **Older setups aren't on the list.** Setups saved before v{version}, and setups you made by hand
  in Notion, don't count until you add them, one at a time: paste that setup's Notion link in the
  chat and say **"learn from this one too"**.
- **A saved game default is reused when it's on the list.** If the skill saved the default for
  this stage from v{version} on, it finds it. Otherwise it asks for screenshots of the default,
  and builds without them if you'd rather not.
- **You can force a setup in or out.** On the car's `Setups` page, add ` - learn: yes` to the end
  of a setup's line to always learn from it, or ` - learn: no` to never read it. Only edit the end
  of the line; the skill never writes that part.

## What works

- Building, changing, reviewing, sharing and saving setups.
- Importing a save file, and saving your own setups from photos.
- **Every car, fully** — bundled ones and the ones you onboarded from screenshots. Their parameter
  lists never need the connection. A car set up by a much older version of the skill may need one
  re-onboard from screenshots. The skill tells you which.
- Anything you give it in the current chat, like screenshots or values you type.

## Things to know

- **Skip the token on the `Config` page.** It needs the connection Free doesn't have.
- **Long chats can hit Free's limits.** Some requests run several steps, and each saved setup the
  skill reads costs a step. If a chat stops, start a new one and ask again.

## Moving to Pro or Max

Open Settings → Capabilities → Network egress, choose **All domains**, set up the token on the
`Config` page, and start a new chat. The skill then reads your whole `Setups` table, including
setups made before v{version} and by hand. The `learn: yes` / `learn: no` marks keep working.
