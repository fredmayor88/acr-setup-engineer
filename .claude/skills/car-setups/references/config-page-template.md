# Config page template (seed for the Notion page)

This is the friendly template used to create the **`Config`** page in Notion (directly under the
`Car setups` root) the first time the skill builds your structure. It explains how to give the
skill fast, exact read access to your setups and gives you a place to paste the token. It's
written for a non-technical user: plain language, numbered steps.

> When seeding the Notion page, copy everything below the line **verbatim**. **Never overwrite an
> existing `Config` page** — if one is already there, leave it (it may already hold the user's
> token). Leave the token line empty; the user pastes their own secret onto it later.

---

# 🔑 Config

This page gives the **car-setups skill** fast, exact read access to your tables. It's optional but
recommended — without it, reading your setups is slower and less reliable.

You only do this **once**, and it takes about 3 minutes.

## 1. Create a read-only integration
Go to **[notion.so/my-integrations](https://www.notion.so/my-integrations)** → **New integration**
→ **Internal**, in this workspace. Under **Capabilities**, leave **only "Read content"** checked
(uncheck *Update* and *Insert*). Copy the **Internal Integration Secret** — it starts with
`secret_` or `ntn_`.

## 2. Connect it to only your Car setups
Open your **Car setups** page → **•••** menu → **Connections** → add the integration you just made.
Access cascades to everything under `Car setups` (your Parameters/Setups) — **and nothing else** in
your workspace.

## 3. Paste your token below
Paste the secret on the line below. It's safe here: the token is **read-only** and can only see the
data you connected it to. **Keep it private** — don't share this page.

**Token:** _(paste your `secret_…` / `ntn_…` here)_

---

*Prefer not to store it?* You can skip this page and just paste the token in chat whenever the
skill asks — nothing is saved.
